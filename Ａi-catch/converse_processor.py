import pandas as pd

# 1. 讀取原始資料與屬性庫
# 請確保檔名與您的實際檔名一致
converse_df = pd.read_csv('Converse-2.xlsx - All SKU raw data.csv')
attr_category = pd.read_csv('货品资料属性库20260324.xlsx - 类别.csv')
attr_gender = pd.read_csv('货品资料属性库20260324.xlsx - 性别.csv')

# 2. 處理貨品資料 (Goods Master)
# 邏輯：組合 Style 與 Color
converse_df['Goods No'] = converse_df['Style'] + '-' + converse_df['Color'].astype(str)

# 邏輯：處理貨品名稱 (優先取 Local Product Name)
converse_df['Goods Name'] = converse_df['Local Product Name'].fillna(converse_df['Style Name'])

# 3. 建立貨品主檔 (去重)
goods_master = converse_df.drop_duplicates(subset=['Goods No']).copy()

# 設定固定屬性
goods_master['Brand'] = 'CONVERSE'
goods_master['Year'] = '2026'
goods_master['Season'] = 'SU' # 夏季

# 4. 欄位映射與格式化 (依照範本A)
final_goods_master = pd.DataFrame({
    '货品编号': goods_master['Goods No'],
    '货品名称': goods_master['Goods Name'],
    '品牌': goods_master['Brand'],
    '年份': goods_master['Year'],
    '季节': goods_master['Season'],
    '零售价': goods_master['Retail Price'],
    '性别': goods_master['Gender'] # 這裡可依屬性庫再做 replace
})

# 5. 處理尺码資料 (SKU Details)
sku_details = pd.DataFrame({
    '货品编号': converse_df['Goods No'],
    '条码': converse_df['UPC/EAN'],
    '尺码': converse_df['Size'],
    '颜色': converse_df['Color'],
    '零售价': converse_df['Retail Price']
})

# 6. 匯出為 Excel 多個分頁
with pd.ExcelWriter('货品新增导入表_SU26_Final.xlsx', engine='openpyxl') as writer:
    final_goods_master.to_excel(writer, sheet_name='货品资料', index=False)
    sku_details.to_excel(writer, sheet_name='尺码资料', index=False)

print("轉換完成！檔案已生成：货品新增导入表_SU26_Final.xlsx")
