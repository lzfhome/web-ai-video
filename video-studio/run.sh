#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

if [ ! -f config.secrets.json ]; then
  echo "============================================================"
  echo "✗ 未检测到 config.secrets.json（密钥文件，不入 git 仓库）"
  echo "  没有密钥无法运行，已停止启动。"
  echo ""
  echo "请手动创建该文件，把下面内容复制进去并填入你的真实密钥："
  echo ""
  echo '  {'
  echo '    "api_key": "ark-你的火山方舟APIKey",'
  echo '    "base_url": "https://ark.cn-beijing.volces.com/api/v3",'
  echo '    "public_base_url": "",'
  echo '    "access_key_id": "你的AK",'
  echo '    "secret_access_key": "你的SK",'
  echo '    "usage_apikey_id": "你的用量APIKeyID"'
  echo '  }'
  echo ""
  echo "  API Key 获取：https://console.volcengine.com/ark/region:cn-beijing/apikey"
  echo "  创建好后重新运行 run.sh 即可。"
  echo "============================================================"
  exit 1
fi

exec uvicorn app:app --host 0.0.0.0 --port 8000