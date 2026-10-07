import re, collections, json
p=open('/tmp/claude-0/zbs_final.bin','rb').read()
PREFIXES=[b'it_',b'be_',b'co_',b'sp_',b'va_',b'ta_',b'mt_',b'fu_',b'sy_',b'ar_',b'ba_',b'cl_',b'ra_']
result={}
for pref in PREFIXES:
    ids=[m.start() for m in re.finditer(rb'(?<![a-zA-Z0-9_])'+pref+rb'[a-z0-9_]{2,40}', p)]
    if len(ids)<20: 
        print(f'{pref.decode():5s} skip ({len(ids)})'); continue
    gaps=collections.Counter(ids[i+1]-ids[i] for i in range(len(ids)-1))
    stride,hits=gaps.most_common(1)[0]
    if hits<10: print(f'{pref.decode():5s} 불규칙 {gaps.most_common(3)}'); continue
    first=next(o for o in ids if o+stride in ids)
    while first-stride in ids: first-=stride
    cnt=0
    while first+cnt*stride < len(p) and re.match(rb'[a-z][a-z0-9_]{2,40}', p[first+cnt*stride:first+cnt*stride+42]): cnt+=1
    rbase=first-1; pos=collections.Counter(); mx=collections.defaultdict(int)
    N=min(cnt,300)
    for i in range(N):
        r=p[rbase+i*stride:rbase+(i+1)*stride]
        for j in range(len(r)-2):
            L=r[j]
            if 2<=L<=250 and j+1+L<len(r) and all(0x20<=b<0x7f for b in r[j+1:j+1+L]) and r[j+1+L]==0:
                pos[j]+=1; mx[j]=max(mx[j],L)
    fields=sorted(o for o,c in pos.items() if c>=N*0.8)
    caps={o:(fields[k+1]-o if k+1<len(fields) else stride-o) for k,o in enumerate(fields)}
    result[pref.decode()]={'first':first,'stride':stride,'count':cnt,
        'fields':[{'off':o,'maxlen':mx[o],'cap':min(caps[o],256)} for o in fields]}
    r=p[rbase:rbase+stride]
    print(f'{pref.decode():5s} 레코드 {cnt:5d}  stride {stride:6d}  base {first:#09x}')
    for o in fields:
        L=r[o]; print(f'     +{o:#07x} cap {min(caps[o],256):4d} max {mx[o]:3d}  {r[o+1:o+1+L].decode("latin1")[:50]}')
json.dump(result, open('/home/claude/zorbus-tools/zbs_map.json','w'), indent=1)
