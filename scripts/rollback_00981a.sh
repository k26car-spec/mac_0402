#!/usr/bin/env bash
# 把網頁與舊更新程式還原到部署前版本。只做一個一般 commit，不 push、不刪歷史。
# 用法：在最新的 main 上執行  bash scripts/rollback_00981a.sh <部署前的 tag>
set -euo pipefail
ref="${1:?請提供部署前的 tag，例如 pre-deploy-20261130}"
git rev-parse --verify -q "$ref^{commit}" >/dev/null || { echo "找不到版本：$ref"; exit 1; }
git diff --quiet && git diff --cached --quiet || { echo "有未提交的修改，請先處理再回復"; exit 1; }

# 保留新版 update_data.yml（一般 commit）。舊版會 force push，還原它會抹掉歷史。
git checkout "$ref" -- docs/index.html update_etf.py
git commit -m "回復：網頁與 update_etf.py 還原到 ${ref}（00981A 新版停用）"
echo "已建立回復 commit，尚未推送。下一步見 docs/etf/DEPLOY.md「回復」。"
