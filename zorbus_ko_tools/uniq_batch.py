#!/usr/bin/env python3
"""남은 고유 원문만 뽑아낸다 (빈도 높은 것부터). 대표 id 하나만 번역하면
blob_dedup.py 가 동일 원문 전체에 자동 적용한다."""
import json, glob, sys, collections, os
D='/home/claude/zorbus/tl/blob/'
SRC=json.load(open(D+'src.json',encoding='utf-8'))
done={}
for f in glob.glob(D+'ko_*.json'): done.update(json.load(open(f,encoding='utf-8')))
todo=[r for r in SRC if not r['skip'] and str(r['i']) not in done]
freq=collections.Counter(r['en'] for r in todo)
rep={}
for r in todo: rep.setdefault(r['en'], r['i'])
order=sorted(rep.items(), key=lambda kv:(-freq[kv[0]], kv[1]))
start=int(sys.argv[1]) if len(sys.argv)>1 else 0
cnt=int(sys.argv[2]) if len(sys.argv)>2 else 300
print(f"### 고유 원문 {len(order)}개 남음 (실제 {len(todo)}줄) — {start}~{start+cnt}")
for en,i in order[start:start+cnt]:
    print(f"{i}\t×{freq[en]}\t{en}")
