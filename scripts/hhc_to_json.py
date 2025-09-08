#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
解析 publish/ 下的 .hhc/.hhk（优先），生成 publish/toc.json。
若没有 .hhc/.hhk，则按文件夹/HTML 文件结构生成目录树（数组形式）。
输出格式：list of { title, url, children }
用法：python3 scripts/hhc_to_json.py publish
"""
import os, sys, json, re, html
from html.parser import HTMLParser

# 尝试的编码顺序
ENCODINGS = ['utf-8', 'utf-16', 'cp1252', 'cp936', 'gbk', 'gb2312', 'big5', 'latin1']

HTML_EXTS = ('.htm', '.html', '.xhtml')

def read_text_try(path):
    raw = open(path, 'rb').read()
    for enc in ENCODINGS:
        try:
            return raw.decode(enc)
        except Exception:
            continue
    # 最后保险回退
    return raw.decode('latin1', errors='replace')

class RobustTOCParser(HTMLParser):
    """
    尝试解析两类结构：
      1) .hhc 的 object/param (text/sitemap)
      2) 普通 <a href="...">Title</a> 列表（li/ul 嵌套）
    结果是一个树：list of nodes (dicts)
    """
    def __init__(self):
        super().__init__()
        self.stack = [[]]   # 每遇到 ul/ol 就 push, pop -> 子项归属
        self.current_object = None
        self.current_anchor = None
        self.capture_anchor_text = False

    def handle_starttag(self, tag, attrs):
        tag = tag.lower()
        attrs = dict((k.lower(), v) for k, v in attrs)
        if tag in ('ul', 'ol'):
            self.stack.append([])
        elif tag == 'object' and attrs.get('type', '').lower() == 'text/sitemap':
            self.current_object = {'title': None, 'url': None, 'children': []}
        elif tag == 'param' and self.current_object is not None:
            name = attrs.get('name', '').lower()
            val = attrs.get('value', '') or attrs.get('VALUE', '')
            val = html.unescape(val)
            if name == 'name':
                self.current_object['title'] = val
            elif name in ('local', 'url'):
                self.current_object['url'] = val
        elif tag == 'a':
            href = attrs.get('href', '')
            href = html.unescape(href)
            self.current_anchor = {'title': None, 'url': href, 'children': []}
            self.capture_anchor_text = True

    def handle_endtag(self, tag):
        tag = tag.lower()
        if tag in ('ul', 'ol'):
            children = self.stack.pop()
            if self.stack and self.stack[-1]:
                # 把 children 赋给上层最后一个节点
                parent = self.stack[-1][-1]
                parent['children'] = children
        elif tag == 'object':
            if self.current_object is not None:
                if not self.current_object.get('title'):
                    self.current_object['title'] = self.current_object.get('url') or 'Untitled'
                self.stack[-1].append(self.current_object)
            self.current_object = None
        elif tag == 'a':
            if self.current_anchor is not None:
                if not self.current_anchor.get('title'):
                    # 用文件名代替 title（尽量友好）
                    t = self.current_anchor.get('url') or ''
                    t = os.path.basename(t) or t or 'Untitled'
                    self.current_anchor['title'] = t
                self.stack[-1].append(self.current_anchor)
            self.current_anchor = None
            self.capture_anchor_text = False

    def handle_data(self, data):
        if self.capture_anchor_text and self.current_anchor is not None:
            # 累计锚文本
            text = (self.current_anchor.get('title') or '') + data
            self.current_anchor['title'] = text.strip()

    def get_result(self):
        return self.stack[0]

def find_first_by_ext(root, exts):
    for base, _, files in os.walk(root):
        for f in files:
            low = f.lower()
            if any(low.endswith(ext) for ext in exts):
                return os.path.relpath(os.path.join(base, f), root)
    return None

def normalize_href(href):
    if not href:
        return None
    href = href.strip()
    # 去掉 mk:@MSITStore:, ms-its:, file:// 等前缀
    # 若包含 ::/ 或 :: 后面通常是真实文件路径，取后面部分
    m = re.search(r'::/+(.*)$', href)
    if not m:
        m = re.search(r'::(.*)$', href)
    if m:
        href = m.group(1)
    # 去掉 leading slashes and drive letters, 但保留 http(s) 等外部链接
    if re.match(r'^https?://', href, flags=re.I):
        return href
    # 去掉 fragment (? 和 #) 但保留用于后续匹配；实际文件存在性检查会切掉 fragment
    href = href.lstrip('/\\')
    href = href.replace('\\', '/')
    return href

def resolve_to_existing(root, href):
    """
    尽力把 href 映射到 publish 下存在的文件（相对路径）。
    如果找不到，返回 normalize 后的 href（尽量可用）。
    """
    if not href:
        return None
    href = href.split('#')[0].split('?')[0]
    href_norm = href
    # 若为外部链接（http:// 等），直接返回
    if re.match(r'^[a-z]+://', href_norm, flags=re.I):
        return href_norm
    # 尝试直接存在
    candidate = os.path.normpath(os.path.join(root, href_norm))
    if os.path.exists(candidate):
        return os.path.relpath(candidate, root).replace('\\', '/')
    # 否则尝试 basename 匹配（大小写不敏感）
    bname = os.path.basename(href_norm).lower()
    for base, _, files in os.walk(root):
        for f in files:
            if f.lower() == bname:
                return os.path.relpath(os.path.join(base, f), root).replace('\\', '/')
    # 再尝试去掉可能的 query/hash 之后的片段（已处理），最后退回原始 href_norm
    return href_norm.replace('\\', '/')

def fix_nodes(nodes, root):
    # 递归修正 title/url，并解析相对路径
    for n in nodes:
        if not n.get('title'):
            n['title'] = n.get('url') or 'Untitled'
        if n.get('url'):
            raw = n['url']
            norm = normalize_href(raw)
            resolved = resolve_to_existing(root, norm)
            n['url'] = resolved
        # 递归
        if n.get('children'):
            fix_nodes(n['children'], root)

def build_tree_from_files(root):
    # 把所有 html 文件按目录构造成树
    files = []
    for base, _, filenames in os.walk(root):
        for f in filenames:
            if f.lower().endswith(HTML_EXTS):
                files.append(os.path.relpath(os.path.join(base, f), root).replace('\\', '/'))
    files.sort()
    nodes = []
    for rel in files:
        parts = rel.split('/')
        cur = nodes
        for i, part in enumerate(parts):
            if i == len(parts) - 1:
                # 文件节点
                title = os.path.splitext(part)[0]
                cur.append({'title': title, 'url': rel, 'children': []})
            else:
                # 目录节点：在 cur 中查找
                found = None
                for it in cur:
                    if it.get('title') == part and it.get('children') is not None:
                        found = it
                        break
                if not found:
                    found = {'title': part, 'url': None, 'children': []}
                    cur.append(found)
                cur = found['children']
    return nodes

def parse_hhc_file(hhc_path, root):
    txt = read_text_try(hhc_path)
    parser = RobustTOCParser()
    parser.feed(txt)
    data = parser.get_result()
    # 若解析为空，尝试用简单的正则抓 <param name="Name" value="..."> 情况（作为兜底）
    if not data:
        params = re.findall(r'<param[^>]+name=["\']?name["\']?[^>]*value=["\']([^"\']+)["\']', txt, flags=re.I)
        locals_ = re.findall(r'<param[^>]+name=["\']?local["\']?[^>]*value=["\']([^"\']+)["\']', txt, flags=re.I)
        if params and locals_:
            # 简单配对
            pairs = zip(params, locals_)
            for title, url in pairs:
                data.append({'title': html.unescape(title), 'url': html.unescape(url), 'children': []})
    # 规范化
    fix_nodes(data, root)
    return data

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 scripts/hhc_to_json.py <publish-dir>")
        sys.exit(1)
    root = sys.argv[1]
    if not os.path.isdir(root):
        print("Error: publish dir not found:", root)
        sys.exit(2)

    # 尝试找到 .hhc / .hhk
    hhc_rel = find_first_by_ext(root, ('.hhc', '.hhk'))
    if hhc_rel:
        hhc_path = os.path.join(root, hhc_rel)
        print("Found HHC/HHK:", hhc_rel)
        try:
            toc = parse_hhc_file(hhc_path, root)
        except Exception as e:
            print("Warning: parse hhc failed:", str(e))
            toc = []
    else:
        toc = []

    # 如果解析出空（或没有 .hhc），使用文件树回退
    if not toc:
        print("⚠️ 未解析到 .hhc/.hhk 或解析结果为空，使用按文件夹生成的目录回退。")
        toc = build_tree_from_files(root)

    # 最后：确保是数组（viewer 需要数组）
    if not isinstance(toc, list):
        toc = list(toc) if toc else []

    out = os.path.join(root, 'toc.json')
    with open(out, 'w', encoding='utf-8') as f:
        json.dump(toc, f, ensure_ascii=False, indent=2)
    print("Wrote", out, "with", len(toc), "root items.")

if __name__ == '__main__':
    main()
