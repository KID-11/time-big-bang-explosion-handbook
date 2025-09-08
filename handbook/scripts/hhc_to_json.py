#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
从解压目录中查找 .hhc/.hhk，解析为 toc.json（层级结构）。
用法：python scripts/hhc_to_json.py publish
"""
import os, sys, json, re

from html.parser import HTMLParser

class HHCParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.stack = [[]]  # 栈顶是当前层级的 children 列表
        self.current = None
        self.in_object = False
        self.in_param = False
        self.param_name = None

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag.lower() == 'ul':
            self.stack.append([])
        elif tag.lower() == 'object' and attrs.get('type','').lower() == 'text/sitemap':
            self.current = {'title': None, 'url': None, 'children': []}
            self.in_object = True
        elif self.in_object and tag.lower() == 'param':
            # <param name="Name" value="xxx"> / <param name="Local" value="path.htm">
            name = attrs.get('name') or attrs.get('NAME')
            value = attrs.get('value') or attrs.get('VALUE')
            if name:
                if name.lower() == 'name':
                    self.current['title'] = value
                elif name.lower() == 'local':
                    self.current['url'] = value.lstrip('/')
        # 其他标签不关心

    def handle_endtag(self, tag):
        if tag.lower() == 'ul':
            children = self.stack.pop()
            # 把 children 放到上一层最后一个节点的 children 里（若存在）
            if len(self.stack[-1]) > 0:
                self.stack[-1][-1]['children'] = children
        elif tag.lower() == 'object' and self.in_object:
            if self.current:
                # 清理空 children
                if not self.current.get('children'):
                    self.current['children'] = []
                self.stack[-1].append(self.current)
            self.current = None
            self.in_object = False

    def get_result(self):
        return self.stack[0]

def find_hhc(root):
    # 优先 .hhc，再尝试 .hhk
    for name in os.listdir(root):
        if name.lower().endswith('.hhc'):
            return os.path.join(root, name)
    for name in os.listdir(root):
        if name.lower().endswith('.hhk'):
            return os.path.join(root, name)
    return None

def main():
    if len(sys.argv) < 2:
        print('Usage: python scripts/hhc_to_json.py <publish-dir>')
        sys.exit(1)
    pub = sys.argv[1]
    hhc = find_hhc(pub)
    if not hhc:
        # 没有目录文件，尝试以 index.htm(l) 构建一个最简单目录
        index_file = None
        for cand in ('index.html','index.htm','default.html','default.htm'):
            p = os.path.join(pub, cand)
            if os.path.exists(p):
                index_file = cand
                break
        data = [{'title': '首页', 'url': index_file or '', 'children': []}]
    else:
        with open(hhc, 'rb') as f:
            raw = f.read()
        # 尝试按常见编码解码（CHM 常见为 gbk/gb2312）
        txt = None
        for enc in ('utf-8', 'gbk', 'gb2312', 'cp936'):
            try:
                txt = raw.decode(enc)
                break
            except:
                continue
        if txt is None:
            txt = raw.decode('latin1', errors='ignore')
        parser = HHCParser()
        parser.feed(txt)
        data = parser.get_result()

    out = os.path.join(pub, 'toc.json')
    with open(out, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print('Wrote', out)

if __name__ == '__main__':
    main()
