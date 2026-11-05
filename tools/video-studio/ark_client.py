import httpx

from config import CONFIG

BASE_URL = CONFIG["base_url"]
API_KEY = CONFIG["api_key"]


def _headers():
    return {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
    }


async def create_task(payload: dict) -> dict:
    async with httpx.AsyncClient(timeout=120) as client:
        resp = await client.post(
            f"{BASE_URL}/contents/generations/tasks",
            headers=_headers(),
            json=payload,
        )
        if resp.status_code >= 400:
            raise httpx.HTTPStatusError(
                f"HTTP {resp.status_code}: {resp.text[:800]}",
                request=resp.request,
                response=resp,
            )
        return resp.json()


async def query_task(task_id: str) -> dict:
    async with httpx.AsyncClient(timeout=120) as client:
        resp = await client.get(
            f"{BASE_URL}/contents/generations/tasks/{task_id}",
            headers=_headers(),
        )
        if resp.status_code >= 400:
            raise httpx.HTTPStatusError(
                f"HTTP {resp.status_code}: {resp.text[:800]}",
                request=resp.request,
                response=resp,
            )
        return resp.json()


async def chat_messages(model: str, messages: list[dict], temperature: float = 0.4) -> str:
    payload = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
    }
    async with httpx.AsyncClient(timeout=120) as client:
        resp = await client.post(
            f"{BASE_URL}/chat/completions",
            headers=_headers(),
            json=payload,
        )
        if resp.status_code >= 400:
            raise httpx.HTTPStatusError(
                f"HTTP {resp.status_code}: {resp.text[:800]}",
                request=resp.request,
                response=resp,
            )
    data = resp.json()
    try:
        return data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError):
        raise RuntimeError(f"对话模型返回异常: {str(data)[:400]}")


async def chat(model: str, user_prompt: str, temperature: float = 0.4) -> str:
    return await chat_messages(
        model,
        [{"role": "user", "content": user_prompt}],
        temperature,
    )


async def download(url: str, dest: str) -> None:
    async with httpx.AsyncClient(timeout=None) as client:
        async with client.stream("GET", url, follow_redirects=True) as resp:
            resp.raise_for_status()
            with open(dest, "wb") as f:
                async for chunk in resp.aiter_bytes():
                    f.write(chunk)


async def list_models() -> list[str]:
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(f"{BASE_URL}/models", headers=_headers())
        if resp.status_code >= 400:
            raise httpx.HTTPStatusError(
                f"HTTP {resp.status_code}: {resp.text[:800]}",
                request=resp.request,
                response=resp,
            )
    data = resp.json()
    return [m.get("id") for m in data.get("data", []) if m.get("id")]


async def gen_image(model: str, prompt: str, size: str = "1280x720", watermark: bool = False,
                    image: list[str] | None = None, sequential: bool = False) -> list[dict]:
    """调用 Seedream 生图，返回 data 列表（每项含 b64_json / output_format）。
    image: 参考图（图生图/多图融合）；sequential=True 走组图生成（一条提示词出一组）。"""
    payload = {
        "model": model,
        "prompt": prompt,
        "size": size,
        "response_format": "b64_json",
        "watermark": watermark,
    }
    if image:
        payload["image"] = image
    if sequential:
        payload["sequential_image_generation"] = "auto"
    async with httpx.AsyncClient(timeout=300) as client:
        resp = await client.post(
            f"{BASE_URL}/images/generations",
            headers=_headers(),
            json=payload,
        )
        if resp.status_code >= 400:
            raise httpx.HTTPStatusError(
                f"HTTP {resp.status_code}: {resp.text[:800]}",
                request=resp.request,
                response=resp,
            )
    data = resp.json()
    items = data.get("data") or []
    if not items:
        raise RuntimeError(f"图片生成返回异常: {str(data)[:400]}")
    return items