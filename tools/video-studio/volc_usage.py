"""火山引擎 OpenAPI 调用（用量 + 余额）。

统一走 open.volcengineapi.com，HMAC-SHA256 签名 v4。
- 用量：GetInferenceUsage  (service=ark, region=cn-beijing)
- 余额：QueryBalanceAcct (service=billing)
"""
import datetime
import hashlib
import hmac
import json
import urllib.parse

import httpx

BILLING_LABELS = {
    "normal": "付费余额",
    "no_need_billing": "未付费体验",
    "free_for_model_unit": "模型单元用量",
    "free_for_free_quota": "安心体验(免费)",
    "free_for_limit_boundary": "安心体验(超限)",
    "free_for_viptier": "TPM保障包",
}


def _hmac(key: bytes, msg: str) -> bytes:
    return hmac.new(key, msg.encode("utf-8"), hashlib.sha256).digest()


def _hex_sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _canonical_query(query: dict) -> str:
    def enc(s: str) -> str:
        return urllib.parse.quote(s, safe="-_.~")

    return "&".join(f"{enc(k)}={enc(v)}" for k, v in sorted(query.items()))


def _sign(ak: str, sk: str, service: str, region: str, query: dict, body_bytes: bytes, xdate: str) -> dict:
    cqs = _canonical_query(query)
    payload_hash = _hex_sha256(body_bytes)

    headers = {
        "content-type": "application/json; charset=utf-8",
        "host": "open.volcengineapi.com",
        "x-content-sha256": payload_hash,
        "x-date": xdate,
    }
    canonical_headers = "".join(f"{k}:{v}\n" for k, v in sorted(headers.items()))
    signed_headers = ";".join(sorted(headers.keys()))

    canonical_request = "\n".join(["POST", "/", cqs, canonical_headers, signed_headers, payload_hash])

    date = xdate[:8]
    scope = f"{date}/{region}/{service}/request"
    string_to_sign = "\n".join(["HMAC-SHA256", xdate, scope, _hex_sha256(canonical_request.encode())])

    k_date = _hmac(sk.encode(), date)
    k_region = _hmac(k_date, region)
    k_service = _hmac(k_region, service)
    k_signing = _hmac(k_service, "request")
    signature = hmac.new(k_signing, string_to_sign.encode(), hashlib.sha256).hexdigest()

    authorization = (
        f"HMAC-SHA256 Credential={ak}/{scope}, "
        f"SignedHeaders={signed_headers}, Signature={signature}"
    )
    return {
        "Host": "open.volcengineapi.com",
        "X-Date": xdate,
        "X-Content-Sha256": payload_hash,
        "Content-Type": "application/json; charset=utf-8",
        "Authorization": authorization,
    }


async def _call(ak: str, sk: str, service: str, region: str, action: str, version: str, body: dict) -> dict:
    body_bytes = json.dumps(body, separators=(",", ":")).encode()
    query = {"Action": action, "Version": version}
    xdate = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    url = f"https://open.volcengineapi.com/?{_canonical_query(query)}"
    headers = _sign(ak, sk, service, region, query, body_bytes, xdate)

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(url, headers=headers, content=body_bytes)
        if resp.status_code >= 400:
            raise RuntimeError(f"HTTP {resp.status_code}: {resp.text[:800]}")

    data = resp.json()
    meta = data.get("ResponseMetadata", {})
    if meta.get("Error"):
        err = meta["Error"]
        raise RuntimeError(f"{err.get('Code')}: {err.get('Message')}")
    return data


async def get_usage(ak: str, sk: str, start: str, end: str, apikey_id: str = "") -> list[dict]:
    filters = [{"Key": "BillingStatus", "Values": []}]
    if apikey_id:
        filters.append({"Key": "ApikeyID", "Values": [apikey_id]})
    body = {
        "Filters": filters,
        "QueryInterval": "Day",
        "StartTime": start,
        "EndTime": end,
        "ShowWindowDetail": True,
    }
    data = await _call(ak, sk, "ark", "cn-beijing", "GetInferenceUsage", "2024-01-01", body)
    result = data.get("Result", {})
    fields = [f.get("Name", "") for f in result.get("Fields", [])]
    rows = []
    for item in result.get("Data", []) or []:
        row = dict(zip(fields, item))
        if row.get("BillingStatus") in BILLING_LABELS:
            row["BillingStatusLabel"] = BILLING_LABELS[row["BillingStatus"]]
        rows.append(row)
    return rows


async def get_balance(ak: str, sk: str) -> dict:
    """查询资金账户余额。QueryBalanceAcct 无需业务参数。"""
    data = await _call(ak, sk, "billing", "cn-north-1", "QueryBalanceAcct", "2022-01-01", {})
    return data.get("Result", {}) or {}