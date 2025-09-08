import os
import sys
import json

def find_hhc_file(root):
    for dirpath, _, filenames in os.walk(root):
        for f in filenames:
            if f.lower().endswith(".hhc"):
                return os.path.join(dirpath, f)
    return None

def build_simple_toc(root):
    """如果没有 hhc，就用 index.html 或第一个 HTML 文件"""
    candidates = []
    for dirpath, _, filenames in os.walk(root):
        for f in filenames:
            if f.lower().endswith((".htm", ".html")):
                rel = os.path.relpath(os.path.join(dirpath, f), root)
                candidates.append(rel)
    candidates.sort()

    if not candidates:
        return {"title": "No Content", "items": []}

    # 优先 index.html
    entry = None
    for c in candidates:
        if os.path.basename(c).lower().startswith("index"):
            entry = c
            break
    if not entry:
        entry = candidates[0]

    return {
        "title": "Contents",
        "items": [
            {"title": os.path.splitext(os.path.basename(entry))[0], "path": entry}
        ]
    }

def main():
    if len(sys.argv) < 2:
        print("Usage: python hhc_to_json.py <publish_dir>")
        sys.exit(1)

    root = sys.argv[1]
    hhc_path = find_hhc_file(root)

    if hhc_path:
        # TODO: 这里可以扩展解析 .hhc 文件为 JSON
        toc = {"title": "CHM TOC", "items": [{"title": os.path.basename(hhc_path), "path": os.path.relpath(hhc_path, root)}]}
    else:
        print("⚠️ 未找到 .hhc 文件，使用简化目录")
        toc = build_simple_toc(root)

    with open(os.path.join(root, "toc.json"), "w", encoding="utf-8") as f:
        json.dump(toc, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    main()
