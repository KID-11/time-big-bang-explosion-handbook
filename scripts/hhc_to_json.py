#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
增强版CHM内容扫描器 - 无论有没有.hhc文件都能工作
"""
import os
import sys
import json
import re
from html.parser import HTMLParser

class HHCParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.stack = [[]]
        self.current = None
        self.in_object = False

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        tag = tag.lower()
        if tag == 'ul':
            self.stack.append([])
        elif tag == 'object' and attrs.get('type','').lower() == 'text/sitemap':
            self.current = {'title': None, 'url': None, 'children': []}
            self.in_object = True
        elif self.in_object and tag == 'param':
            name = (attrs.get('name') or attrs.get('NAME') or '').lower()
            value = (attrs.get('value') or attrs.get('VALUE') or '')
            if name == 'name':
                self.current['title'] = value
            elif name == 'local':
                self.current['url'] = value.lstrip('/')

    def handle_endtag(self, tag):
        tag = tag.lower()
        if tag == 'ul':
            if len(self.stack) > 1:  # 防止栈空
                children = self.stack.pop()
                if self.stack and self.stack[-1] and self.stack[-1][-1]:
                    self.stack[-1][-1]['children'] = children
        elif tag == 'object' and self.in_object:
            if self.current:
                if not self.current.get('children'):
                    self.current['children'] = []
                if self.stack and len(self.stack) > 0:
                    self.stack[-1].append(self.current)
            self.current = None
            self.in_object = False

    def get_result(self):
        return self.stack[0] if self.stack else []

def scan_all_html_files(root_dir):
    """扫描所有HTML文件并创建目录树"""
    html_files = []
    
    # 找出所有HTML文件
    for dirpath, _, filenames in os.walk(root_dir):
        for filename in filenames:
            if filename.lower().endswith(('.htm', '.html')):
                full_path = os.path.join(dirpath, filename)
                rel_path = os.path.relpath(full_path, root_dir)
                
                # 尝试从HTML文件提取标题
                title = extract_html_title(full_path) or os.path.splitext(filename)[0]
                
                html_files.append({
                    'title': title,
                    'url': rel_path.replace('\\', '/'),
                    'children': []
                })
    
    # 按URL排序（通常能保持一定的层次结构）
    html_files.sort(key=lambda x: x['url'])
    
    # 如果过多，只保留前100个
    if len(html_files) > 100:
        print(f"警告：发现{len(html_files)}个HTML文件，限制为前100个")
        html_files = html_files[:100]
    
    return html_files

def extract_html_title(html_path):
    """从HTML文件中提取标题"""
    try:
        with open(html_path, 'rb') as f:
            content = f.read(8192)  # 只读取开头部分
            
        # 尝试不同编码
        for encoding in ['utf-8', 'gbk', 'gb2312', 'cp936', 'big5', 'latin1']:
            try:
                text = content.decode(encoding)
                match = re.search(r'<title[^>]*>(.*?)</title>', text, re.IGNORECASE | re.DOTALL)
                if match:
                    title = match.group(1).strip()
                    return title
            except:
                continue
    except:
        pass
    return None

def find_hhc_file(root):
    """查找.hhc文件"""
    for dirpath, _, filenames in os.walk(root):
        for filename in filenames:
            if filename.lower().endswith('.hhc'):
                return os.path.join(dirpath, filename)
    return None

def parse_hhc_file(hhc_path):
    """解析.hhc文件为目录结构"""
    try:
        with open(hhc_path, 'rb') as f:
            content = f.read()
            
        # 尝试多种编码
        text = None
        for encoding in ['utf-8', 'gbk', 'gb2312', 'cp936', 'big5']:
            try:
                text = content.decode(encoding)
                break
            except:
                continue
                
        if text is None:
            text = content.decode('latin1', errors='ignore')
            
        parser = HHCParser()
        parser.feed(text)
        result = parser.get_result()
        
        # 修复相对路径
        def fix_paths(items):
            for item in items:
                if 'url' in item and item['url']:
                    item['url'] = item['url'].replace('\\', '/').lstrip('/')
                if 'children' in item and item['children']:
                    fix_paths(item['children'])
        
        fix_paths(result)
        return result
    except Exception as e:
        print(f"解析.hhc文件失败: {e}")
        return []

def find_index_file(root):
    """查找索引文件"""
    index_candidates = [
        'index.html', 'index.htm', 
        'default.html', 'default.htm',
        'home.html', 'home.htm',
        'start.html', 'start.htm',
        'main.html', 'main.htm',
        'welcome.html', 'welcome.htm'
    ]
    
    # 先在根目录查找
    for candidate in index_candidates:
        if os.path.exists(os.path.join(root, candidate)):
            return candidate
            
    # 递归查找任何目录下的索引文件
    for dirpath, _, filenames in os.walk(root):
        for candidate in index_candidates:
            if candidate in filenames:
                return os.path.relpath(os.path.join(dirpath, candidate), root).replace('\\', '/')
                
    # 找第一个html文件
    for dirpath, _, filenames in os.walk(root):
        for filename in filenames:
            if filename.lower().endswith(('.htm', '.html')):
                return os.path.relpath(os.path.join(dirpath, filename), root).replace('\\', '/')
                
    return None

def main():
    if len(sys.argv) < 2:
        print("用法: python3 hhc_to_json.py <发布目录>")
        sys.exit(1)
        
    pub_dir = sys.argv[1]
    
    # 查找.hhc文件
    hhc_path = find_hhc_file(pub_dir)
    toc_data = []
    
    if hhc_path:
        print(f"找到.hhc文件: {hhc_path}")
        toc_data = parse_hhc_file(hhc_path)
    
    # 如果.hhc解析失败或为空，扫描所有HTML文件
    if not toc_data:
        print("未找到有效的.hhc文件或解析失败，扫描所有HTML文件...")
        index_file = find_index_file(pub_dir)
        
        if index_file:
            print(f"找到索引文件: {index_file}")
            # 将索引文件作为根节点
            toc_data = [{
                'title': '首页',
                'url': index_file,
                'children': scan_all_html_files(pub_dir)
            }]
        else:
            # 直接使用所有HTML文件
            toc_data = scan_all_html_files(pub_dir)
    
    # 确保有至少一个条目
    if not toc_data:
        print("警告: 未找到任何内容，创建空目录")
        toc_data = [{
            'title': '无内容',
            'url': '',
            'children': []
        }]
    
    # 保存为toc.json
    output_path = os.path.join(pub_dir, 'toc.json')
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(toc_data, f, ensure_ascii=False, indent=2)
    
    print(f"已生成目录，共{len(toc_data)}个根节点，保存到: {output_path}")

if __name__ == "__main__":
    main()
