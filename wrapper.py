import os
import json
import re
from collections import OrderedDict, defaultdict

# ==========================================
# 1. 全域快取與工具函數層級 (最外層)
# ==========================================
_tag_mapping_cache = None
_stem_category_cache = None
_tag_dir_cache = None

def safe_category(cat):
    """確保分類值是字串（若為 list 則合併成字串）"""
    if isinstance(cat, list):
        return ", ".join(str(c) for c in cat)
    return str(cat) if cat is not None else ""

def load_tag_mapping(directory):
    global _tag_mapping_cache, _stem_category_cache, _tag_dir_cache
    if _tag_dir_cache == directory and _tag_mapping_cache is not None:
        return _tag_mapping_cache, _stem_category_cache

    mapping = {}
    if not os.path.isdir(directory):
        _tag_mapping_cache = mapping
        _stem_category_cache = {}
        _tag_dir_cache = directory
        return mapping, {}

    # 讀取所有 JSON
    for fname in os.listdir(directory):
        if not fname.endswith(".json"):
            continue
        fpath = os.path.join(directory, fname)
        try:
            with open(fpath, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            continue

        if isinstance(data, dict):
            for tag, category in data.items():
                if not isinstance(tag, str):
                    continue
                cat_str = safe_category(category)
                if tag not in mapping and cat_str:
                    mapping[tag] = cat_str
        elif isinstance(data, list):
            category = os.path.splitext(fname)[0]
            for tag in data:
                if isinstance(tag, str) and tag not in mapping:
                    mapping[tag] = category

    # 手動覆蓋機制
    override_path = os.path.join(directory, "overrides.json")
    if os.path.isfile(override_path):
        try:
            with open(override_path, "r", encoding="utf-8") as f:
                overrides = json.load(f)
            if isinstance(overrides, dict):
                for tag, category in overrides.items():
                    cat_str = safe_category(category)
                    if isinstance(tag, str) and cat_str:
                        mapping[tag] = cat_str
        except Exception as e:
            print(f"[Wrapper] 讀取 overrides.json 失敗: {e}")

    # 建立詞根推斷表
    stem_counter = defaultdict(lambda: defaultdict(int))
    for tag, category in mapping.items():
        if not category:
            continue
        tokens = tag.replace("_", " ").split()
        for token in tokens:
            token = token.lower()
            if len(token) >= 2:
                stem_counter[token][category] += 1

    stem_to_category = {}
    for stem, cat_counts in stem_counter.items():
        if stem in mapping:
            continue
        if not cat_counts:
            continue
        best_cat = max(cat_counts, key=cat_counts.get)
        stem_to_category[stem] = best_cat

    _tag_mapping_cache = mapping
    _stem_category_cache = stem_to_category
    _tag_dir_cache = directory
    return mapping, stem_to_category


def make_stems(word):
    """
    詞形變化（安全強化版）：
    - 嚴格控制重複尾音還原，避免誤傷 dress, glass, ass 等正常單字。
    """
    stems = [word]
    has_suffix = False  # 標記是否真的進行了後綴截斷

    # 1. 原有 s/es 分支
    if word.endswith("es"):
        stems.append(word[:-2])
        stems.append(word[:-1])
        has_suffix = True
    elif word.endswith("s") and not word.endswith("ss"):
        stems.append(word[:-1])
        has_suffix = True

    # 2. 原有 ed 分支
    if word.endswith("ed"):
        stems.append(word[:-2])
        stems.append(word[:-1])
        has_suffix = True

    # 3. 原有 ing 分支
    if word.endswith("ing"):
        stems.append(word[:-3])
        has_suffix = True

    # 4. 新增 -ly 結尾
    if word.endswith("ly"):
        stems.append(word[:-2])
        has_suffix = True

    # 5. 新增 -ies 結尾轉為 y
    if word.endswith("ies"):
        stems.append(word[:-3] + "y")
        has_suffix = True

    # 6. 安全的重複尾音還原
    if has_suffix:
        extra = []
        for s in stems:
            if len(s) >= 3 and s[-1] == s[-2]:
                if s[-1] != 's':  # 排除 ss 結尾
                    extra.append(s[:-1])
        stems.extend(extra)

    # 去重並保留順序
    seen = set()
    out = []
    for s in stems:
        if s not in seen:
            seen.add(s)
            out.append(s)
    return out


# ==========================================
# 2. 類別定義與其方法層級 (WrapperNode 內部)
# ==========================================
class WrapperNode:
    CATEGORY = "Newbie_image_danbooru_tags"

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "text": ("STRING", {"multiline": True, "default": ""}),
                "no_output_if_not_corresponding": ("BOOLEAN", {"default": False}),
                "fuzzy_definition": ("BOOLEAN", {"default": True}),
                "clean_and_inflection": ("BOOLEAN", {"default": True}),
            }
        }

    RETURN_TYPES = ("STRING", "STRING")
    RETURN_NAMES = ("classification_json", "help_text")
    FUNCTION = "classify_tags"

    @staticmethod
    def _normalize_category(cat: str) -> str:
        """將分類字串中的半角括號統一轉為全角括號，並統一將常見的舊命名形式修正，與 category_order 保持一致"""
        if not cat:
            return cat
        # 1. 先處理全半角括號
        cat = cat.replace("(", "（").replace(")", "）")
        # 2. 強大防禦：如果使用者的詞典檔案裡寫的是舊命名，在這裡自動對齊，避免使用者需要手動翻修幾萬行的 JSON！
        if cat == "畫面中的位置" or cat == "畫面中的位置（中心，left，前景等）":
            return "畫面中的位置（中心，左側，前景等）"
        return cat

    def _read_help_from_readme(self, node_dir):
        """從同目錄的 README.md 中讀取 [HELP_START] 與 [HELP_END] 之間的內容"""
        readme_path = os.path.join(node_dir, "README.md")
        default_help = "未找到說明文件。請確保節點目錄下存在 README.md 且包含 [HELP_START] 標記。"
        
        if not os.path.isfile(readme_path):
            return default_help

        try:
            with open(readme_path, "r", encoding="utf-8") as f:
                content = f.read()
            
            # 使用正規表達式撈取標記中間的文字
            match = re.search(r'\[HELP_START\](.*?)\[HELP_END\]', content, re.DOTALL)
            if match:
                return match.group(1).strip()
            return "README.md 存在，但未找到 [HELP_START] 與 [HELP_END] 標記區塊。"
        except Exception as e:
            return f"讀取說明文件時發生錯誤: {str(e)}"

    def classify_tags(self, text, no_output_if_not_corresponding, fuzzy_definition, clean_and_inflection):
        node_dir = os.path.dirname(os.path.abspath(__file__))
        
        # 讀取說明文件內容
        help_text = self._read_help_from_readme(node_dir)

        tags_dir = os.path.join(node_dir, "danbooru_tags")
        mapping, stem_category = load_tag_mapping(tags_dir)

        raw_tags = [t.strip() for t in text.split(",") if t.strip()]

        # 這裡的字串必須與 Parser 節點輸出完全一致
        category_order = [
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
            "畫面中的位置（中心，左側，前景等）"  # <--- 【已修正】完美對齊 Parser 節點！
        ]

        grouped = defaultdict(list)

        for raw in raw_tags:
            tag_lower = raw.lower()
            cat = self._find_category(tag_lower, mapping, stem_category, fuzzy_definition, clean_and_inflection)
            if cat is not None:
                normalized_cat = self._normalize_category(cat)
                grouped[normalized_cat].append(raw)
            else:
                if not no_output_if_not_corresponding:
                    grouped["其他 Danbooru 標籤"].append(raw)

        output_dict = OrderedDict()
        for cat in category_order:
            tags = grouped.get(cat, [])
            if tags:
                output_dict[cat] = ", ".join(tags)

        return (json.dumps(output_dict, ensure_ascii=False), help_text)

    def _find_category(self, tag, mapping, stem_category, fuzzy, clean_inflection):
        """漏斗過濾流程方法"""
        tag = tag.lower().strip()

        for stem in make_stems(tag):
            if stem in mapping:
                return mapping[stem]

        tag_underscored = tag.replace(" ", "_")
        if tag_underscored != tag:
            for stem in make_stems(tag_underscored):
                if stem in mapping:
                    return mapping[stem]

        if clean_inflection:
            cleaned = tag.replace("/", "").replace("\\", "")
            cleaned = re.sub(r'\([^)]*\)', '', cleaned)
            cleaned = cleaned.strip("_ ")
            
            if cleaned:
                for stem in make_stems(cleaned):
                    if stem in mapping:
                        return mapping[stem]

        if fuzzy:
            parts = [p for p in re.split(r'[ _\-]+', tag) if p]
            if not parts:
                return None

            for token in reversed(parts):
                for stem_form in make_stems(token):
                    if stem_form in mapping:
                        return mapping[stem_form]
                        
            for token in parts:
                for stem_form in make_stems(token):
                    if stem_form in mapping:
                        return mapping[stem_form]

            for token in reversed(parts):
                for stem_form in make_stems(token):
                    if stem_form in stem_category:
                        return stem_category[stem_form]
                        
            for token in parts:
                for stem_form in make_stems(token):
                    if stem_form in stem_category:
                        return stem_category[stem_form]

        return None


# ==========================================
# 3. ComfyUI 節點映射登記 (最外層)
# ==========================================
NODE_CLASS_MAPPINGS = {
    "WrapperNode": WrapperNode
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "WrapperNode": "Danbooru Tag Classifier Pro"
}