#!/usr/bin/env python3
"""Inject book.json into site_template.html -> index.html"""
import json, os
here = os.path.dirname(os.path.abspath(__file__))
book = open(os.path.join(here, 'book.json')).read()
tpl = open(os.path.join(here, 'site_template.html')).read()
out = tpl.replace('__BOOK_JSON__', book)
open(os.path.join(here, 'index.html'), 'w').write(out)
print('index.html written,', len(out)//1024, 'KB')
