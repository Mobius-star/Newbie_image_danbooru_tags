import os
from collections import defaultdict

def convert_tags(input_file):
    # 用來記錄每個類別的數據
    categories = defaultdict(list)
    # 用來記錄已出現過的標籤，避免重複
    tag_tracker = defaultdict(int)

    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line or '*' not in line:
                    continue
                
                tags_part, category = line.split('*')
                category = category.strip()
                tags = [t.strip() for t in tags_part.split(',') if t.strip()]
                
                for tag in tags:
                    # 處理重複名稱
                    tag_tracker[tag] += 1
                    final_tag = tag
                    if tag_tracker[tag] > 1:
                        final_tag = f"{tag}_{tag_tracker[tag] - 1}"
                    
                    categories[category].append(f'"{final_tag}": "{category}",')

        # 輸出到各自的檔案，改為使用編號 1, 2, 3...
        # 這裡使用 enumerate 來獲取從 1 開始的編號
        for index, (category, lines) in enumerate(categories.items(), start=1):
            output_filename = f"add_tags_output_{index}.txt"
            with open(output_filename, 'w', encoding='utf-8') as f_out:
                f_out.write('\n'.join(lines))
            print(f"已生成檔案: {output_filename} (類別: {category})")

    except FileNotFoundError:
        print(f"錯誤：找不到檔案 {input_file}")

if __name__ == "__main__":
    convert_tags('add_tags.txt')