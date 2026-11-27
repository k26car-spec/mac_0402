# 00981A 部署與回復步驟

**每一步都需要使用者授權後才能執行。** 目前尚未部署、未推送、`static.yml` 未停用。
任何一步結果與「通過條件」不符：停止後續步驟並回報，不得 force push。

```bash
R=k26car-spec/mac_0402
SRC=clean/00981a-official-data
```

## 部署來源（只能用這一個）

- 分支 `clean/00981a-official-data`：從 `pre-00981a-fix` 起算**只有一個 commit**。
- 舊的本機分支 `fix/00981a-official-data` 的歷史含投信員工編號，**不得 push、merge 或 cherry-pick**。
- 部署前在本機倉庫執行，兩行都必須符合：

```bash
git rev-list --count pre-00981a-fix..$SRC                      # 1
for c in $(git rev-list $SRC); do git grep -lE '"EditEmployee"[[:space:]]*:' $c; done | wc -l   # 0
```

## 目前發布狀態（2026-11-28 查核）

- Pages：legacy build，來源 `main` 分支 `/docs`。
- `pages-build-deployment`：每次 main 更新（含 Actions 的提交）發布 `/docs`。
- `static.yml`：人工或 claude.ai routine push main 時觸發，發布**整個 repo 根目錄**，與上面互相競爭。
  近期 `/docs` 版都晚幾秒完成而勝出，順序沒有保證；根目錄版勝出時網站會變回舊 `index.html` 與舊資料。
- 停用影響：線上網址只依賴 `/docs`（根目錄獨有的檔案現在就是 404），大盤分析讀 `docs/market-analysis.json`，不受影響。

## 新 workflow 的三種模式

| 觸發 | 條件 | 行為 |
|---|---|---|
| 手動（預設） | `deploy` 未勾選 | dry-run：唯讀權限，只抓取、驗算、輸出 |
| 手動 `deploy=true` | 只能在 main；其他分支由 `guard` 標紅拒絕 | 正式提交資料 |
| 自動排程 | `ETF_OFFICIAL_ENABLED=true` 且 main（預設未設定＝關閉） | 正式提交資料 |

## 第一階段：部署準備

```bash
gh api repos/$R/pages --jq '[.build_type,.source.branch,.source.path]'   # legacy main /docs
gh run list -R $R --status in_progress                                  # 必須是空的
gh run list -R $R --status queued                                       # 必須是空的
gh variable list -R $R                                                  # 不得有 ETF_OFFICIAL_ENABLED=true
gh api repos/$R/actions/workflows --jq '.workflows[]|[.name,.state]'    # 記錄現況
git fetch origin
TAG=pre-deploy-$(date +%Y%m%d-%H%M)
git tag $TAG origin/main && git push origin $TAG                        # 回復版本
git ls-remote origin refs/tags/$TAG                                     # 確認存在
```

避開舊排程時段：平日台北 17:00 前後，以及 GitHub 延遲後常落在的隔天 01:00–05:00。

## 第二階段：新版部署

```bash
gh workflow disable static.yml -R $R                       # 還原：gh workflow enable static.yml -R $R
git switch -c deploy-00981a origin/main                    # main 每天被舊排程重建，所以用 cherry-pick
git cherry-pick pre-00981a-fix..$SRC                       # 衝突就 git cherry-pick --abort 並停止
python3 -m unittest discover -s tests                      # 全部通過
python3 etf_official.py --verify docs/etf                  # 一致性核對通過
git log -p origin/main..HEAD | grep -cE '^\+.*"EditEmployee"[[:space:]]*:'   # 0
git push origin HEAD:main                                  # 一般 push；被拒絕就停止，重做本階段
gh run list -R $R --workflow pages-build-deployment -L 1   # success
```

線上確認（Pages 快取可能延遲數分鐘）：`https://k26car-spec.github.io/mac_0402/?etf=00981A`
的 11/26、11/27、兩日累計與本機驗收相同；00403A 分頁與大盤分析正常。
此時資料若落後最新交易日，頁面顯示「待更新」屬預期。

## 第三階段：自動更新驗證

```bash
gh workflow run etf_official.yml -R $R                     # dry-run
gh run watch -R $R --exit-status
```
通過條件：只有 `dry-run` job 執行且成功（測試通過、官方端點可連線）；main 沒有新 commit。
這是原子互換與官方端點第一次在 GitHub 主機上實跑。

```bash
gh workflow run etf_official.yml -R $R -f deploy=true      # 正式提交一次
gh run watch -R $R --exit-status
```
通過條件：`publish` 成功；main 多一個只改 `docs/etf/` 的 commit；
`git pull` 後 `--verify docs/etf` 通過；網頁顯示「更新正常」。

```bash
gh variable set ETF_OFFICIAL_ENABLED --body true -R $R     # 上面都通過才開啟
gh workflow run update_data.yml -R $R                      # 舊流程跑一次
```
通過條件：舊流程 commit 只改 `data.json`、`docs/data.json`、`baseline.json`；`docs/etf/` 與歷史保留。

可選：`gh variable set ETF_PUBLISH_TIME --body 17:00 -R $R` 調整應公布時間。

## 第四階段：紀錄

正式網址、部署 commit、各次 run 連結、`status.json` 的最後成功更新時間、驗收結果、`$TAG`。

## 回復

1. 停止新排程（資料保持現狀）：`gh variable set ETF_OFFICIAL_ENABLED --body false -R $R`
2. 網頁也要回舊版：
   ```bash
   git fetch origin --tags && git switch -c rollback origin/main
   bash scripts/rollback_00981a.sh $TAG      # 只建立一個回復 commit，不 push
   git push origin HEAD:main
   gh workflow run update_data.yml -R $R     # 讓舊流程重新產生 00981A 資料
   ```
3. 需要時 `gh workflow enable static.yml -R $R`（不建議）。

注意：回到舊版等於回到**已知錯誤的 00981A 數字**。回復後保留新版 `update_data.yml`，不恢復 force push。
