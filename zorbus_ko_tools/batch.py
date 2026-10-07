import json, sys, os, glob
KEEP=json.load(open('/home/claude/zorbus-tools/tl/exe/keep.json',encoding='utf-8'))
def skipset():
    import os
    f='/home/claude/zorbus-tools/tl/exe/skip.json'
    return set(map(str, json.load(open(f)))) if os.path.exists(f) else set()
def done():
    d=dict.fromkeys(skipset(), None)
    for f in glob.glob('/home/claude/zorbus-tools/tl/exe/ko_*.json'):
        d.update(json.load(open(f,encoding='utf-8')))
    return d
if __name__=='__main__':
    budget=int(sys.argv[1]) if len(sys.argv)>1 else 6000
    D=done(); out=[]; tot=0
    for r in KEEP:
        if str(r['id']) in D: continue
        out.append(r); tot+=len(r['en'])
        if tot>=budget: break
    rem=sum(len(r['en']) for r in KEEP if str(r['id']) not in D)
    print(f"### 남은 {len([r for r in KEEP if str(r['id']) not in D])}개 / {rem:,} bytes  — 이번 배치 {len(out)}개")
    for r in out: print(f"{r['id']}\t{r['en']}")
