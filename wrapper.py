import os
import json
import re
from collections import OrderedDict, defaultdict

# ==========================================
# 1. 全域快取與工具函數
# ==========================================
_tag_mapping_cache = None
_stem_category_cache = None
_tag_dir_cache = None
_tag_metadata_cache = None   # tag -> {"category": str, "source_file": str}

def safe_category(cat):
    if isinstance(cat, list):
        return ", ".join(str(c) for c in cat)
    return str(cat) if cat is not None else ""

def load_tag_mapping(directory):
    global _tag_mapping_cache, _stem_category_cache, _tag_dir_cache, _tag_metadata_cache
    if _tag_dir_cache == directory and _tag_mapping_cache is not None:
        return _tag_mapping_cache, _stem_category_cache, _tag_metadata_cache

    mapping = {}
    tag_metadata = {}
    if not os.path.isdir(directory):
        _tag_mapping_cache = mapping
        _stem_category_cache = {}
        _tag_metadata_cache = tag_metadata
        _tag_dir_cache = directory
        return mapping, {}, tag_metadata

    for fname in os.listdir(directory):
        if not fname.endswith(".json"):
            continue
        fpath = os.path.join(directory, fname)
        try:
            with open(fpath, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            print(f"[Wrapper] 讀取 {fpath} 失敗: {e}")
            continue

        if isinstance(data, dict):
            for tag, category in data.items():
                if not isinstance(tag, str):
                    continue
                cat_str = safe_category(category)
                if tag not in mapping and cat_str:
                    mapping[tag] = cat_str
                    tag_metadata[tag] = {
                        "category": cat_str,
                        "source_file": fname,
                    }
        elif isinstance(data, list):
            category = os.path.splitext(fname)[0]
            for tag in data:
                if isinstance(tag, str) and tag not in mapping:
                    mapping[tag] = category
                    tag_metadata[tag] = {
                        "category": category,
                        "source_file": fname,
                    }

    # 手動覆蓋機制 (overrides.json)
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
                        tag_metadata[tag] = {
                            "category": cat_str,
                            "source_file": "overrides.json",
                        }
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
    _tag_metadata_cache = tag_metadata
    _tag_dir_cache = directory
    return mapping, stem_to_category, tag_metadata


def make_stems(word):
    """詞形變化（完整版）"""
    original = word
    stems = [word]
    has_suffix = False

    if word.endswith("es"):
        stems.append(word[:-2])
        stems.append(word[:-1])
        has_suffix = True
    elif word.endswith("s") and not word.endswith("ss"):
        stems.append(word[:-1])
        has_suffix = True

    if word.endswith("ed"):
        stems.append(word[:-2])
        stems.append(word[:-1])
        has_suffix = True

    if word.endswith("ing"):
        stems.append(word[:-3])
        has_suffix = True

    if word.endswith("ly"):
        stems.append(word[:-2])
        has_suffix = True

    if word.endswith("ies"):
        stems.append(word[:-3] + "y")
        has_suffix = True

    if word.endswith("ves") and len(word) > 4 and word not in ("saves", "waves", "caves", "loves", "moves"):
        stems.append(word[:-3] + "f")
        stems.append(word[:-3] + "fe")
        has_suffix = True

    if word.endswith("ices") and len(word) > 5:
        stems.append(word[:-4] + "ex")
        stems.append(word[:-4] + "ix")
        has_suffix = True

    if word.endswith("er") and len(word) > 3:
        stems.append(word[:-2])
        has_suffix = True
    if word.endswith("est") and len(word) > 4:
        stems.append(word[:-3])
        has_suffix = True

    if word.endswith("lly") and len(word) > 4:
        stems.append(word[:-2])
        has_suffix = True

    if has_suffix:
        extra = []
        forbidden_pairs = {'ll', 'ff', 'ee', 'oo', 'ss'}
        for s in stems:
            if len(s) >= 3 and s[-1] == s[-2]:
                pair = s[-2:]
                if pair in forbidden_pairs:
                    continue
                if len(s) - 1 >= 3:
                    extra.append(s[:-1])
        stems.extend(extra)

    seen = set()
    out = []
    for s in stems:
        if len(original) >= 3 and len(s) < 3:
            continue
        if s not in seen:
            seen.add(s)
            out.append(s)
    return out


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

    RETURN_TYPES = ("STRING", "STRING", "STRING")
    RETURN_NAMES = ("classification_json", "help_text", "confirmed_type_and_mapping")
    FUNCTION = "classify_tags"

    @staticmethod
    def _normalize_category(cat: str) -> str:
        if not cat:
            return cat
        cat = cat.replace("(", "（").replace(")", "）")
        if cat == "畫面中的位置" or cat == "畫面中的位置（中心，left，前景等）":
            return "畫面中的位置（中心，左側，前景等）"
        return cat

    def _read_help_from_readme(self, node_dir):
        readme_path = os.path.join(node_dir, "README.md")
        default_help = "未找到說明文件。請確保節點目錄下存在 README.md 且包含 [HELP_START] 標記。"
        if not os.path.isfile(readme_path):
            return default_help
        try:
            with open(readme_path, "r", encoding="utf-8") as f:
                content = f.read()
            match = re.search(r'\[HELP_START\](.*?)\[HELP_END\]', content, re.DOTALL)
            if match:
                return match.group(1).strip()
            return "README.md 存在，但未找到 [HELP_START] 與 [HELP_END] 標記區塊。"
        except Exception as e:
            return f"讀取說明文件時發生錯誤: {str(e)}"

    def _get_tag_trace(self, tag, mapping, stem_category, tag_metadata, fuzzy, clean_inflection):
        """返回 (category, trace_string)，trace 包含来源文件名"""
        original_tag = tag
        tag = tag.lower().strip()
        trace_parts = []

        # 第一层：绝对原样匹配
        if tag in mapping:
            cat = mapping[tag]
            src = tag_metadata.get(tag, {}).get("source_file", "unknown")
            trace_parts.append(f"原始匹配: '{tag}' (來源: {src})")
            return cat, " -> ".join(trace_parts) + f" -> {cat}"

        tag_underscored = tag.replace(" ", "_")
        if tag_underscored != tag and tag_underscored in mapping:
            cat = mapping[tag_underscored]
            src = tag_metadata.get(tag_underscored, {}).get("source_file", "unknown")
            trace_parts.append(f"下劃線匹配: '{tag_underscored}' (來源: {src})")
            return cat, " -> ".join(trace_parts) + f" -> {cat}"

        # 第二层：智慧清洗后原样匹配
        cleaned = None
        if clean_inflection:
            cleaned = tag.strip()
            weight_match = re.match(r'^\(([^:]+)(?::\d+(?:\.\d+)?)?\)$', cleaned)
            if weight_match:
                cleaned = weight_match.group(1).strip()
                trace_parts.append(f"權重清洗: '{cleaned}'")
            else:
                cleaned = cleaned.replace("/", "").replace("\\", "")
                cleaned = re.sub(r'\([^)]*\)', '', cleaned)
                cleaned = cleaned.strip("_ ")
                if cleaned != tag:
                    trace_parts.append(f"一般清洗: '{cleaned}'")
            if cleaned and cleaned != tag:
                if cleaned in mapping:
                    cat = mapping[cleaned]
                    src = tag_metadata.get(cleaned, {}).get("source_file", "unknown")
                    trace_parts.append(f"清洗後匹配: '{cleaned}' (來源: {src})")
                    return cat, " -> ".join(trace_parts) + f" -> {cat}"
                cleaned_underscored = cleaned.replace(" ", "_")
                if cleaned_underscored in mapping:
                    cat = mapping[cleaned_underscored]
                    src = tag_metadata.get(cleaned_underscored, {}).get("source_file", "unknown")
                    trace_parts.append(f"清洗後下劃線匹配: '{cleaned_underscored}' (來源: {src})")
                    return cat, " -> ".join(trace_parts) + f" -> {cat}"

        # 第三层：安全词态还原匹配
        if clean_inflection and cleaned:
            for stem in make_stems(cleaned):
                if stem in mapping:
                    cat = mapping[stem]
                    src = tag_metadata.get(stem, {}).get("source_file", "unknown")
                    trace_parts.append(f"詞態還原: '{stem}' (來源: {src})")
                    return cat, " -> ".join(trace_parts) + f" -> {cat}"
            for stem in make_stems(tag):
                if stem in mapping:
                    cat = mapping[stem]
                    src = tag_metadata.get(stem, {}).get("source_file", "unknown")
                    trace_parts.append(f"詞態還原(原始): '{stem}' (來源: {src})")
                    return cat, " -> ".join(trace_parts) + f" -> {cat}"

        # 第四层：模糊拆词根匹配
        if fuzzy:
            target = cleaned if (clean_inflection and cleaned) else tag
            parts = [p for p in re.split(r'[ _\-]+', target) if p]
            if parts:
                trace_parts.append(f"拆詞: {parts}")
                for token in reversed(parts):
                    for stem_form in make_stems(token):
                        if stem_form in mapping:
                            cat = mapping[stem_form]
                            src = tag_metadata.get(stem_form, {}).get("source_file", "unknown")
                            trace_parts.append(f"反向匹配 token '{token}' -> '{stem_form}' (來源: {src})")
                            return cat, " -> ".join(trace_parts) + f" -> {cat}"
                for token in parts:
                    for stem_form in make_stems(token):
                        if stem_form in mapping:
                            cat = mapping[stem_form]
                            src = tag_metadata.get(stem_form, {}).get("source_file", "unknown")
                            trace_parts.append(f"正向匹配 token '{token}' -> '{stem_form}' (來源: {src})")
                            return cat, " -> ".join(trace_parts) + f" -> {cat}"
                # 词根表匹配（无源文件）
                for token in reversed(parts):
                    for stem_form in make_stems(token):
                        if stem_form in stem_category:
                            cat = stem_category[stem_form]
                            trace_parts.append(f"詞根表反向匹配 '{stem_form}' (來源: 詞根推斷)")
                            return cat, " -> ".join(trace_parts) + f" -> {cat}"
                for token in parts:
                    for stem_form in make_stems(token):
                        if stem_form in stem_category:
                            cat = stem_category[stem_form]
                            trace_parts.append(f"詞根表正向匹配 '{stem_form}' (來源: 詞根推斷)")
                            return cat, " -> ".join(trace_parts) + f" -> {cat}"
                trace_parts.append("未匹配任何字典/詞根")
            else:
                trace_parts.append("無可拆分詞元")

        return None, " -> ".join(trace_parts) + " -> None"

    def classify_tags(self, text, no_output_if_not_corresponding, fuzzy_definition, clean_and_inflection):
        node_dir = os.path.dirname(os.path.abspath(__file__))
        help_text = self._read_help_from_readme(node_dir)

        tags_dir = os.path.join(node_dir, "danbooru_tags")
        mapping, stem_category, tag_metadata = load_tag_mapping(tags_dir)

        raw_tags = [t.strip() for t in text.split(",") if t.strip()]

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
            "畫面中的位置（中心，左側，前景等）"
        ]

        grouped = defaultdict(list)
        mapping_info_lines = []

        for raw in raw_tags:
            cat, trace = self._get_tag_trace(raw, mapping, stem_category, tag_metadata, fuzzy_definition, clean_and_inflection)
            mapping_info_lines.append(f"{raw}: {trace}")
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

        json_output = json.dumps(output_dict, ensure_ascii=False)
        mapping_output = "\n".join(mapping_info_lines)
        return (json_output, help_text, mapping_output)


NODE_CLASS_MAPPINGS = {
    "WrapperNode": WrapperNode
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "WrapperNode": "Danbooru Tag Classifier Pro"
}
