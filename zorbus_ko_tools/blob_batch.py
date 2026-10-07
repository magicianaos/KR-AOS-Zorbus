import json, glob, os, re, sys, csv
SRC='/home/claude/zorbus-tools/tl/blob/src.json'
if not os.path.exists(SRC):
    rows=list(csv.DictReader(open('/mnt/user-data/outputs/zbs_translate.csv',encoding='utf-8-sig')))
    lines=[r for r in rows if r['kind']=='line']
    out=[]
    for i,r in enumerate(lines):
        en=r['en']
        skip = (not en.strip()) or re.fullmatch(r'[a-z][a-z0-9_]*', en) or re.fullmatch(r'[-+0-9.,;: ]+', en) or len(en)<2
        out.append({'i':i,'en':en,'skip':bool(skip)})
    json.dump(out, open(SRC,'w',encoding='utf-8'), ensure_ascii=False)
SRCD=json.load(open(SRC,encoding='utf-8'))
def done():
    d={}
    for f in glob.glob('/home/claude/zorbus-tools/tl/blob/ko_*.json'):
        d.update(json.load(open(f,encoding='utf-8')))
    return d
if __name__=='__main__':
    budget=int(sys.argv[1]) if len(sys.argv)>1 else 12000
    D=done(); out=[]; tot=0
    todo=[r for r in SRCD if not r['skip'] and str(r['i']) not in D]
    rem=sum(len(r['en']) for r in todo)
    for r in todo:
        out.append(r); tot+=len(r['en'])
        if tot>=budget: break
    print(f"### 남은 {len(todo)}줄 / {rem:,} bytes — 이번 배치 {len(out)}줄")
    for r in out: print(f"{r['i']}\t{r['en']}")
