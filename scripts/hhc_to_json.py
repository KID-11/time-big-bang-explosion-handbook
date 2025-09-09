#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""超强兼容版 CHM 目录生成器"""
import os
import sys
import json
import re
import glob

def log(msg):
    """调试日志"""
    print(f"[LOG] {msg}")

def find_all_html_files(root_dir):
    """查找所有 HTML 文件"""
    html_files = []
    for ext in ['*.htm', '*.html']:
        pattern = os.path.join(root_dir, '**', ext)
        html_files.extend(glob.glob(pattern, recursive=True))
    
    # 相对路径转换
    return [os.path.relpath(f, root_dir).replace('\\', '/') for f in html_files]

def create_simple_toc(html_files, root_dir):
    """从 HTML 文件创建简单目录"""
    items = []
    
    # 按文件名排序
    html_files.sort()
    
    for html_file in html_files:
        try:
            # 尝试读取文件内容提取标题
            full_path = os.path.join(root_dir, html_file)
            title = extract_title_from_html(full_path) or os.path.basename(html_file)
            
            items.append({
                "title": title,
                "url": html_file,
                "children": []
            })
        except Exception as e:
            log(f"处理文件 {html_file} 时出错: {e}")
    
    return items

def extract_title_from_html(file_path):
    """从 HTML 文件中提取标题"""
    try:
        encodings = ['utf-8', 'gbk', 'gb2312', 'latin1']
        for enc in encodings:
            try:
                with open(file_path, 'r', encoding=enc) as f:
                    content = f.read(10000)  # 只读取开头部分
                    title_match = re.search(r'<title[^>]*>(.*?)</title>', content, re.IGNORECASE | re.DOTALL)
                    if title_match:
                        title = title_match.group(1).strip()
                        return title or None
            except UnicodeDecodeError:
                continue
    except Exception as e:
        log(f"读取标题失败: {e}")
    return None

def main():
    if len(sys.argv) < 2:
        print("用法: python hhc_to_json.py <publish目录>")
        sys.exit(1)
    
    publish_dir = sys.argv[1]
    log(f"处理目录: {publish_dir}")
    
    # 1. 查找所有 HTML 文件
    html_files = find_all_html_files(publish_dir)
    log(f"找到 {len(html_files)} 个 HTML 文件")
    
    if len(html_files) > 0:
        for i, html in enumerate(html_files[:5]):
            log(f"示例文件 {i+1}: {html}")
    else:
        log("警告: 未找到任何 HTML 文件!")
    
    # 2. 创建目录结构
    toc = []
    
    if html_files:
        # 优先查找常见首页
        index_candidates = ['index.htm', 'index.html', 'default.htm', 'default.html', 'home.htm', 'home.html']
        index_file = None
        
        for candidate in index_candidates:
            if candidate in html_files:
                index_file = candidate
                break
        
        if not index_file and html_files:
            index_file = html_files[0]
        
        # 创建根节点
        if index_file:
            log(f"使用 {index_file} 作为首页")
            root_title = extract_title_from_html(os.path.join(publish_dir, index_file)) or "目录"
            
            # 构建目录树
            toc = [{
                "title": root_title,
                "url": index_file,
                "children": create_simple_toc(html_files, publish_dir)
            }]
        else:
            toc = create_simple_toc(html_files, publish_dir)
    
    if not toc:
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
    
    # 输出第一个节点内容以供调试
    if toc:
        log(f"根节点: {json.dumps(toc[0], ensure_ascii=False)}")

if __name__ == "__main__":
    main()
