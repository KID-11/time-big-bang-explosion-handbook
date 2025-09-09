#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""超强兼容版 CHM 目录生成器 - 支持任何文件类型"""
import os
import sys
import json
import re
import glob

def log(msg):
    """调试日志"""
    print(f"[LOG] {msg}")

def find_all_content_files(root_dir):
    """查找所有可能的内容文件（不限于HTML）"""
    content_files = []
    
    # 特别检查 chm-content 子目录
    chm_content = os.path.join(root_dir, 'chm-content')
    if os.path.exists(chm_content):
        log(f"检查 chm-content 子目录")
        
        # 优先查找HTML
        for ext in ['*.htm', '*.html']:
            pattern = os.path.join(chm_content, '**', ext)
            found = glob.glob(pattern, recursive=True)
            log(f"在 chm-content 中找到 {len(found)} 个 {ext} 文件")
            for f in found:
                rel_path = os.path.relpath(f, root_dir).replace('\\', '/')
                content_files.append(rel_path)
        
        # 如果没找到HTML，查找任何文件
        if not content_files:
            log("未找到HTML文件，尝试查找其他文件类型")
            for pattern in ['*.txt', '*.rtf', '*.pdf', '*.xml', '*.*']:
                found = glob.glob(os.path.join(chm_content, '**', pattern), recursive=True)
                log(f"找到 {len(found)} 个 {pattern} 文件")
                for f in found:
                    rel_path = os.path.relpath(f, root_dir).replace('\\', '/')
                    content_files.append(rel_path)
    
    return content_files

def main():
    if len(sys.argv) < 2:
        print("用法: python hhc_to_json.py <publish目录>")
        sys.exit(1)
    
    publish_dir = sys.argv[1]
    log(f"处理目录: {publish_dir}")
    
    # 1. 查找所有内容文件
    content_files = find_all_content_files(publish_dir)
    log(f"找到 {len(content_files)} 个内容文件")
    
    if content_files:
        for i, f in enumerate(content_files[:10]):
            log(f"示例文件 {i+1}: {f}")
    else:
        log("警告: 未找到任何内容文件!")
    
    # 2. 创建目录结构
    toc = []
    
    if content_files:
        # 按文件类型分组
        by_ext = {}
        for f in content_files:
            ext = os.path.splitext(f)[1].lower()
            if ext not in by_ext:
                by_ext[ext] = []
            by_ext[ext].append(f)
        
        # 为每种文件类型创建一个目录节点
        for ext, files in by_ext.items():
            files.sort()
            children = []
            for f in files:
                name = os.path.basename(f)
                children.append({"title": name, "url": f, "children": []})
            
            toc.append({
                "title": f"{ext[1:].upper()} 文件" if ext else "文件",
                "url": files[0],
                "children": children
            })
    
    if not toc:
        # 创建一个直接链接到chm-content目录的节点
        if os.path.exists(os.path.join(publish_dir, 'chm-content')):
            toc = [{
                "title": "浏览CHM内容",
                "url": "chm-content/",
                "children": []
            }]
        else:
            log("生成空目录")
            toc = [{
                "title": "无可用内容",
                "url": "",
                "children": []
            }]
    
    # 3. 保存为 JSON
    output_path = os.path.join(publish_dir, 'toc.json')
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(toc, f, ensure_ascii=False, indent=2)
    
    log(f"成功生成 toc.json，包含 {len(toc)} 个根节点")
    
    # 输出toc内容以供调试
    log(f"TOC内容: {json.dumps(toc, ensure_ascii=False)}")

if __name__ == "__main__":
    main()
