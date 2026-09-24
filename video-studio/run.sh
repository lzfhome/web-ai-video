#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

if [ ! -f config.json ]; then
  cp config.example.json config.json 2>/dev/null || true
fi

if ! python3 -c "import json,sys; sys.exit(0 if json.load(open('config.json')).get('api_key') else 1)" 2>/dev/null; then
  echo "提示：config.json 里还没填 api_key，请先编辑 config.json 填入你的 API Key。"
  echo "  获取地址：https://console.volcengine.com/ark/region:cn-beijing/apikey"
  echo "  仍会启动，但无法生成视频。"
fi

exec uvicorn app:app --host 0.0.0.0 --port 8000