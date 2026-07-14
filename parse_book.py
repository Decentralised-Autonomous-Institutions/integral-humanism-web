#!/usr/bin/env python3
"""Parse pdftotext -layout output of Integral Humanism into chapters JSON.
Blocks: ['h', text] headings · ['p', text] paragraphs · ['li', text] list items.
"""
import json, re, os

SRC = '/private/tmp/claude-501/-Users-mrunalpendem/10f5a2be-9b1f-4764-ab4b-df77f06300c2/scratchpad/ih.txt'
OUT = os.path.join(os.path.dirname(__file__), 'book.json')

lines = open(SRC).read().split('\n')

CH_RE = re.compile(r'^\s*C\s*H\s*A\s*P\s*T\s*E\s*R\s*-?\s*(\d)\s*$')
DATE_RE = re.compile(r'^\s*2\d(?:nd|rd|th|st)\s+April\s+1965\s*$')
LI_RE = re.compile(r'^\s{0,5}(\d+)\.\s+(.*)$')
JAI_RE = re.compile(r'BHARAT MATA KI JAI')
TERMINAL = re.compile(r'[.!?"’”]$')
BAN_END = {'be', 'of', 'to', 'in', 'a', 'is', 'are', 'our', 'for', 'the', 'and'}

def clean(t):
    return re.sub(r'\s+', ' ', t).strip()

def titlecaseish(t):
    ws = [w for w in re.findall(r"[A-Za-z']+", t) if len(w) > 3]
    if not ws:
        return False
    return sum(1 for w in ws if w[0].isupper()) / len(ws) >= .6

chapters, intro_blocks = [], []
cur = None
open_para = None
open_kind = 'p'

def blocks():
    return cur['blocks'] if cur is not None else intro_blocks

def close_para():
    global open_para
    if open_para is not None:
        txt = clean(open_para)
        if txt:
            blocks().append([open_kind, txt])
        open_para = None

def heading_ok(s):
    return (len(s) <= 55 and not re.search(r'[.,;:?!]$', s) and s[0].isupper()
            and s.split()[-1].lower() not in BAN_END)

for raw in lines:
    line = raw.rstrip('\n')
    if not line.strip():
        continue
    if CH_RE.match(line):
        close_para()
        cur = {'n': int(CH_RE.match(line).group(1)), 'blocks': []}
        chapters.append(cur)
        continue
    if DATE_RE.match(line):
        close_para(); continue
    if JAI_RE.search(line):
        close_para()
        blocks().append(['h', 'Bharat Mata Ki Jai !'])
        continue
    m = LI_RE.match(line)
    if m and len(line) - len(line.lstrip(' ')) <= 5:
        close_para()
        open_para = m.group(2)
        open_kind = 'li'
        continue
    indent = len(line) - len(line.lstrip(' '))
    stripped = line.strip()
    if indent >= 6:
        # indented: new paragraph, or an indented heading
        prev_terminal = open_para is None or TERMINAL.search(open_para.strip())
        if prev_terminal and heading_ok(stripped) and titlecaseish(stripped):
            close_para()
            blocks().append(['h', stripped])
        else:
            close_para()
            open_para = stripped
            open_kind = 'p'
    else:
        # col-0: heading only if previous para is closed by terminal punctuation
        prev_terminal = open_para is None or TERMINAL.search(open_para.strip())
        if prev_terminal and heading_ok(stripped) and titlecaseish(stripped):
            close_para()
            blocks().append(['h', stripped])
        else:
            if open_para is None:
                open_para = stripped; open_kind = 'p'
            else:
                open_para += ' ' + stripped
close_para()

# dedupe repeated running-head artifacts within a chapter; small typo fixes
FIX = {'Chiti, Cullture, Dharma': 'Chiti, Culture, Dharma',
       'Individual Versus society': 'Individual Versus Society',
       'Society And Individual not conflicting': 'Society and Individual Not Conflicting',
       'Our country: Our problems': 'Our Country, Our Problems'}
PROMOTE = {'Our country: Our problems': 'Our Country, Our Problems',
           'Mutual Co-operation': 'Mutual Co-operation'}
for c in chapters:
    seen, out = set(), []
    for kind, txt in c['blocks']:
        if kind == 'p' and txt in PROMOTE:
            kind, txt = 'h', PROMOTE[txt]
        if kind == 'h':
            txt = FIX.get(txt, txt)
            if txt in seen:
                continue
            seen.add(txt)
        out.append([kind, txt])
    c['blocks'] = out

data = {'intro': intro_blocks, 'chapters': chapters}
json.dump(data, open(OUT, 'w'), ensure_ascii=False)
for c in chapters:
    heads = [b[1] for b in c['blocks'] if b[0] == 'h']
    words = sum(len(b[1].split()) for b in c['blocks'] if b[0] != 'h')
    lis = sum(1 for b in c['blocks'] if b[0] == 'li')
    print(f"Ch{c['n']}: {len(c['blocks'])} blocks · {words}w · {lis} list items")
    print('   heads:', ' | '.join(heads))
