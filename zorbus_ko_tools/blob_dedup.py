"""이미 번역한 원문과 완전히 동일한 줄에 같은 번역을 자동 적용"""
import json, glob, os
SRC=json.load(open('/home/claude/zorbus-tools/tl/blob/src.json',encoding='utf-8'))
done={}
for f in glob.glob('/home/claude/zorbus-tools/tl/blob/ko_*.json'):
    done.update(json.load(open(f,encoding='utf-8')))
byid={str(r['i']):r['en'] for r in SRC}
en2ko={}
for k,v in done.items():
    en=byid.get(k)
    if en is not None: en2ko.setdefault(en, v)
auto={}
for r in SRC:
    k=str(r['i'])
    if r['skip'] or k in done: continue
    if r['en'] in en2ko: auto[k]=en2ko[r['en']]
AF='/home/claude/zorbus-tools/tl/blob/ko_auto.json'
prev = json.load(open(AF,encoding='utf-8')) if os.path.exists(AF) else {}
prev.update(auto)
json.dump(prev, open(AF,'w',encoding='utf-8'), ensure_ascii=False)
print(f'고유 원문 {len(en2ko)}개 -> 자동 적용 {len(auto)}줄')
