
# 家族辦公室評估平台 v5（整合 AI秒算遺產稅）

## 內容
- 模組一：股利決策與稅負（兩階段＋AMT＋未分配稅＋個人二擇一）
- 模組二：傳承與移轉規劃（遺產／贈與／保險／信託示意）
- 模組三：**AI秒算遺產稅**（整合你提供的 `estate_tax_app.py`，完整保留其互動與圖表）

## 部署
```bash
pip install -r requirements.txt
streamlit run app.py
```
或上傳 GitHub → Streamlit Cloud 一鍵部署。


## 付費解鎖（Paywall）
- 在 Streamlit Cloud 的 **Secrets** 設定 `PAID_CODES`，可為：
  - 單一字串：`PAID_CODES="MY-CODE-001"`
  - 或 JSON 陣列：`PAID_CODES=["VIP-8888","GRACE-2025"]`
- 未設定時，預設 DEMO 啟用碼為 **DEMO-1234**（請在正式環境移除）

解鎖後，將開啟：
- 模組二的 **壽險模擬** 與 **分年贈與** 控制
- 模組三（AI秒算遺產稅）的 **保險／贈與模擬** 區塊
