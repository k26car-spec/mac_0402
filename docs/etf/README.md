# 00981A 官方資料管線

修正日期：2026-11-28（台北）。狀態：本機驗收完成，**尚未部署**。00403A 尚未修正。
部署與回復步驟見 [DEPLOY.md](DEPLOY.md)。

## 錯誤根因

| 現象 | 原因 |
|---|---|
| 11/27「當天加碼」混入兩天 | 舊程式用「執行當下日期」建每日基準。11/26 的排程延到 11/27 02:56，把 11/25 持股存成「11/27 基準」；下午那次看到基準已存在就跳過 |
| 單位淨值 21.58、−1.42% | Fugle 收盤市價覆蓋了淨值欄位 |
| 規模 2,321 億、現金 6.60%、保證金 0.22% | 官網沒有程式要找的欄位名稱，靜默沿用寫死值；規模漲跌幅借用市價漲跌幅 |
| 台指期貨 2 張 | 1,533 口被除以 1,000 再四捨五入 |
| 51 檔股票只剩 38 檔，漏掉南茂刪除 | `weight > 0` 濾掉權重 0.00% 的股票 |
| 前二十大混入期貨 | 未依商品分類 |
| 報表日期錯 | 網頁用開啟當天日期 |
| 無異動時沿用舊增減 | 舊資料冒充當日資料 |
| 程式修改歷史會消失 | 每日 orphan commit + force push |

## 資料來源與日期定義

| 資料 | 來源 | 可回查歷史 |
|---|---|---|
| 持股、期貨、淨值、淨資產、單位數 | 統一投信 `POST /ETF/Transaction/GetPCF` | 可 |
| 現金、期貨保證金 | 統一投信基金頁 `DataAsset` | **不可，只有最新一天** |
| 收盤市價、實際交易日 | 證交所 `STOCK_DAY`、`FMTQIK` | 可 |
| 休市行事曆 | 證交所 `holidaySchedule` | 可（依年度） |

- 持股基準日 = 官方 `TranDate`。PCF 查詢日是「適用日」，兩者分開保存。
- 官方回應日期會混用 `/Date(毫秒)/` 與 `YYYY-MM-DDT00:00:00` 兩種格式。
- 現金／保證金只有在基金頁的日期、淨值、單位數、股票總額都與該日 PCF 相同時才採用；沒有就「待核實」。

## PCF 查詢結果與狀態分類

| 查詢結果 | 意義 |
|---|---|
| found | 有該基準日清單 |
| skipped | 官方回傳更晚的基準日，確定沒有這一天 |
| empty | 空白回應，沒有任何佐證，不能當成休市 |
| 連線失敗／非預期格式 | `source_error` |

| 狀態 | 條件 |
|---|---|
| `confirmed_closure` | 行事曆有列；或行事曆沒列、之後已恢復交易、且 PCF 為 skipped |
| `not_published` | 最新交易日 PCF 為 empty；過了公布時間顯示待更新，不算錯誤 |
| `source_error` | 連線、格式、資料驗證不過、行事曆抓不到 |
| `data_gap` | 有交易卻缺清單，或投信有清單而證交所缺資料 |

`status.json`：
- `data_current`：現有資料是否為最新應公布交易日；行事曆無法驗證時為 `null`。
- `expected_basis_date`：最新應公布交易日。`next_due_at`：下一交易日的應公布時間（跳過假日）。
- `last_success_at`：只有資料最新、無異常、無未確認日期才更新。`last_attempt_at`：每次執行都更新。

網頁分開判斷三件事：資料是否最新（含 `next_due_at` 是否已過）、排程是否執行（`last_attempt_at` 超過 36 小時）、
官方來源狀態。連續休市但資料仍最新時不顯示過期。

應公布時間預設 17:00：`--publish-time HH:MM` 或環境變數／repo Variable `ETF_PUBLISH_TIME`。

## 整批發布與資料版本

- 每次執行先在 `docs/etf/.00981A.staging/` 產生完整新版並核對，通過才用單一系統呼叫互換整個資料夾
  （macOS `renamex_np`、Linux `renameat2 RENAME_EXCHANGE`）。系統不支援時直接失敗，不退回改名兩次。
- 任一日期失敗：快照與報表完全不變，只更新 `status.json`、`errors.jsonl`；`last_success_at` 沿用上次成功值。
- `data_version`＝全部快照內容的雜湊；`status.json` 與 `report.json` 必須相同。網頁版本不同時重抓三次，
  仍不同就不顯示資料。
- workflow 在提交前與 rebase 後各跑一次 `--verify`，不通過不推送。
- 原子性指行程中斷與同時讀取；斷電時的磁碟持久性未保證（以 Git 版本為準）。
- 網頁狀態：`pending` 顯示「待更新／官方尚未公布」；只有 `error` 顯示「更新異常」。

## 驗證規則（任一不過 → 整批不發布、寫入 errors.jsonl、工作流程標紅）

資料日期一致；必要欄位齊全；股票代號不重複、股數正整數；明細金額合計 = 官方股票總額；
權重與金額一致；單位數 × 淨值 ≈ 淨資產；期貨欄位格式；單位數差異與前日快照一致；
單日淨值變動 ≤ 12%；股票檔數變動 ≤ 10（確認屬實用 `--allow-count-change`）。

## Workflow

| Workflow | 寫入路徑 | 備註 |
|---|---|---|
| `etf_official.yml` | `docs/etf/` | 手動預設 dry-run；`deploy=true` 限 main；排程需 `ETF_OFFICIAL_ENABLED=true` |
| `update_data.yml`（舊） | `data.json`、`docs/data.json`、`baseline.json` | 改一般 commit、checkout 最新 main |
| claude.ai 大盤分析 routine | `market-analysis.json`、`docs/market-analysis.json` | 未修改 |

路徑不重疊；兩個流程各自 concurrency group；push 被拒絕時 rebase 重試最多 3 次，
同檔衝突則失敗、不覆蓋。`tests/test_workflows.py` 用本機暫存倉庫實跑提交步驟驗證。

## 操作

```bash
python3 -m unittest discover -s tests -v
python3 etf_official.py --days 5
cd docs && python3 -m http.server 8765 --bind 127.0.0.1
# 開 http://127.0.0.1:8765/index.html?etf=00981A&date=2026-11-27  （date=range 為兩日累計）
```

## 驗收結果（2026-11-28）

- 單元測試 92/92：macOS（Python 3.12、3.11）。
- Linux 容器（Ubuntu 26.04、Debian；overlayfs、ext4）在加入欄位白名單前通過 89/89，之後未重跑。
- 瀏覽器驗收 490/490：桌面與手機三種檢視的數字由原始快照獨立重算比對、日期切換、異常與版本不符、舊功能新舊版比對。
- workflow：YAML 解析、各步驟 `bash -n`、`if` 條件求值測試通過；未跑 actionlint，GitHub 端尚未實跑。
- 官方實際回應驗證（僅指定「現在時間」）：週末、中秋＋教師節、光復節補假、臨時休市 7/10 與 10/23、
  公布時間前後。補班日 2025-02-08（週六）僅驗證證交所資料（基金尚未成立）。
- `update_etf.py` 新舊版吃同一份網路回應：00403A、00992A、0050、baseline 完全相同。

## 尚未解決

1. 11/27 以前各日的現金與期貨保證金占比：待核實。
2. 「官網資料編輯時間」取自 PCF `EditDate`，不一定等於對外公告時間。
3. 臨時休市當天到市場恢復交易前，只能顯示「無法確認／待更新」。
4. GitHub 主機能否連到新使用的官方端點，要第一次實跑才能確認。
5. GitHub 排程可能延遲數小時；超過公布時間未跑完時網頁會顯示待更新。
6. `common_holdings`（共識持股）不再納入 00981A，多出大立光；該區塊目前沒有入口按鈕可開啟。
7. 00403A 仍是舊邏輯（日期、規模、比較基準等同類問題）。
8. `data.json` 內舊的 00981A 錯誤資料會在舊排程下一次執行後移除；新版網頁不讀它。
9. `static.yml` 與 `/docs` 發布競爭：待授權後依 DEPLOY.md 停用。
10. GitHub 主機上的原子互換尚未實跑（本機容器通過）；第一次 dry-run 會一併測試。
11. 回看範圍內任一日期持續失敗，整批不發布，最多卡到該日離開 5 個交易日範圍。
12. 本機舊分支 `fix/00981a-official-data` 的歷史仍含投信員工編號，只能留在本機。

## 快照欄位

快照保留全部資料列，但欄位限白名單（`etf_official.py` 的 `KEEP_PCF`、`KEEP_ASSET`、`KEEP_DETAIL`），
不含 `EditEmployee` 等人員欄位。`tests/fixtures/` 與已保存快照同樣處理，並有測試檢查。

## 回復版本

本次修改前：tag `pre-00981a-fix`（`a1a69a7`）。部署與回復指令見 DEPLOY.md。
