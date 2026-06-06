這是為 Newbie_Nodes 專案設計的自定義節點。
需要依賴同目錄的danbooru_tags資料夾裡的json，其中，overrides.json的優先級最高，如果你想要自訂字典，你可以寫在這，他會覆蓋其他1~65.json。你需要遵循格式，能被使用的分類有這些:

   "帶有體重標註的體型標籤",
   "畫師標籤",
   "風格描述",
   "背景",
   "具體環境",
   "相機視角",
   "心情和氛圍",
   "光照條件",
   "畫面質量提示詞",
   "場景中的重要物體",
   "其他 Danbooru 標籤",
   "外觀描述",
   "服飾及配件",
   "臉部表情和情緒",
   "姿勢，動作，手勢，活動",
   "與他人/物件/環境的互動",
   "畫面中的位置（中心，左側，前景等）"

特別感謝 https://huggingface.co/datasets/newtextdoc1111/danbooru-tag-csv/tree/main 的 danbooru_tags.csv
與 https://tags.novelai.dev/ ，所有tags都來源自這裡。

[v1.0.1] - 2026-06-06 : fix(wrapper): 修正智慧清洗邏輯以支援單獨括號與權重格式
- 修正了原本正則表達式會將單獨括號字串全數抹除導致分類歸入「其他」的 Bug。
- 新增條件分流：若是標準權重或強調括號則進行智慧脫殼保留核心詞；若為提示詞尾巴的附帶括號則維持原抹除邏輯。

[HELP_START]

自動將 AI 繪圖提示詞（Prompts）依據 Danbooru 標籤屬性，智慧清洗並分類為 JSON 格式輸出。輸出期待輸出到 Newbie_image_danbooru_tags (Parser) 節點的 JSON 格式。該節點為 Newbie_Nodes 設計，希望以編寫 Tags 的方式編寫 XML，如果你沒有 Newbie_Nodes 節點包，這個自訂節點將毫無意義。

1. text:
   輸入要分類的提示詞文字，以英文逗號 (,) 分隔。

2. no_output_if_not_corresponding:
   - False (預設): 字典未收錄且無法辨識的詞，統一歸類至「其他 Danbooru 標籤」。
   - True: 隱藏未收錄或無法辨識的詞，不輸出。

3. clean_and_inflection:
   - True (預設): 智慧「卸妝」模式。自動拔除髒資料（斜線、不完整括號等），並自動還原單字變體（如複數 s/es/ies、動詞 ing/ed、副詞 ly、重複尾音等）。
   - False: 關閉。嚴格比對原始文字。

4. fuzzy_definition:
   - True (預設): 啟用智慧拆詞根。若遇到字典沒有的長複合詞，會以「字尾優先」雙向拆解底線(_)、空格( )與減號(-)來推斷分類。
   - False: 關閉。非精確匹配的標籤將不予處置。
[HELP_END]
