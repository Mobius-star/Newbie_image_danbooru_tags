import json

class DanbooruSmartMart:
    """
    Parser 節點：接收 JSON 字串並將標籤分發到各個分類輸出。
    """
    CATEGORIES = [
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
    ]

    @classmethod
    def INPUT_TYPES(s):
        inputs = {
            "required": {
                "json_string": ("STRING", {"multiline": True, "default": "{}"}),
            },
            "optional": {}
        }
        for category in s.CATEGORIES:
            inputs["optional"][category] = ("STRING", {"multiline": True, "default": ""})
        return inputs

    RETURN_TYPES = tuple(["STRING"] * len(CATEGORIES))
    RETURN_NAMES = tuple(CATEGORIES)
    FUNCTION = "process_tags"
    CATEGORY = "Newbie_image_danbooru_tags"

    def process_tags(self, json_string, **kwargs):
        try:
            data = json.loads(json_string)
        except json.JSONDecodeError:
            data = {}

        outputs = []
        for category in self.CATEGORIES:
            json_tags = data.get(category, "").strip()
            widget_tags = kwargs.get(category, "").strip()
            
            if json_tags and widget_tags:
                merged_tags = f"{json_tags}, {widget_tags}"
            else:
                merged_tags = json_tags if json_tags else widget_tags
            outputs.append(merged_tags)

        return tuple(outputs)