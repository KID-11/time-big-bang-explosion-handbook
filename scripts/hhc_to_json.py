#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
从解压目录中递归查找 .hhc/.hhk（CHM 目录），解析为 toc.json。
若没有 .hhc/.hhk，则递归寻找一个最可能的入口页（index/default/home…），作为单页目录。
用法：python scripts/hhc_to_json.py publish
"""
import os, sys, json

from html.parser import HTMLParser

POSSIBLE_ENTRY = (
    "index.html","index.htm",
    "default.html","default.htm",
    "home.html","home.htm",
    "start.html","start.htm"
)

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
            children = self.stack.pop()
            if self.stack[-1]:
                self.stack[-1][-1]['children'] = children
        elif tag == 'object' and self.in_object:
            if self.current:
                if not self.current.get('children'):
                    self.current['children'] = []
                self.stack[-1].append(self.current)
            self.current = None
            self.in_object = False

    def get_result(self):
        return self.stack[0]

def find_first(root, exts):
    """递归寻找符合扩展名的第一个文件，返回相对路径"""
    for base, _, files in os.walk(root):
        for f in files:
            low = f.lower()
            if any(low.endswith(ext) for ext in exts):
                return os.path.relpath(os.path.join(base, f), root)
    return None

def find_entry(root):
    # 优先在每个目录里找常见入口名
    for base, _, files in os.walk(root):
        lowset = {f.lower(): f for f in files}
        for cand in POSSIBLE_ENTRY:
            if cand in lowset:
                return os.path.relpath(os.path.join(base, lowset[cand]), root)
    # 实在没有就找任意一个 html
    return find_first(root, ('.html', '.htm'))

def parse_hhc(hhc_path, pub_root):
    with open(os.path.join(pub_root, hhc_path), 'rb') as f:
        raw = f.read()
    txt = None
    for enc in ('utf-8','gbk','gb2312','cp936','big5'):
        try:
            txt = raw.decode(enc)
            break
        except:
            pass
    if txt is None:
        txt = raw.decode('latin1', errors='ignore')
    parser = HHCParser()
    parser.feed(txt)
    data = parser.get_result()
    # 清理空 title，用 url 顶上
    def fix(nodes):
        for n in nodes:
            if not n.get('title'):
                n['title'] = n.get('url') or 'Untitled'
            # 标准化 URL（相对路径）
            if n.get('url'):
                n['url'] = n['url'].lstrip('/')
            if n.get('children'):
                fix(n['children'])
    fix(data)
    return data

def main():
    if len(sys.argv) < 2:
        print('Usage: python scripts/hhc_to_json.py <publish-dir>')
        sys.exit(1)
    pub = sys.argv[1]

    # 1) 递归找 .hhc / .hhk
    hhc_rel = find_first(pub, ('.hhc', '.hhk'))

    if hhc_rel:
        data = parse_hhc(hhc_rel, pub)
    else:
        # 2) 没有目录文件，构建最小 toc：递归找入口页
        entry = find_entry(pub)
        if entry:
            data = [{'title': '首页', 'url': entry.replace('\\','/'), 'children': []}]
        else:
            # 连 html 都没有，生成一个空的 toc（防前端报错）
            data = []

    out = os.path.join(pub, 'toc.json')
    with open(out, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print('Wrote', out, 'with', len(data), 'root items.')

if __name__ == '__main__':
    main()
