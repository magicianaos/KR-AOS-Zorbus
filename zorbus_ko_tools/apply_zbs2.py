#!/usr/bin/env python3
import sys, os, csv, json, re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),'tl'))
from zbs_codec import decode_file
import zbs_codec2 as C2
import zbs_tool
from it import IT
from be import BE
from ta import TA

# be 배열 두번째 필드(+0x48) 고유명 처리
BE2 = {"Joonas":"요나스","Skullcrusher":"해골분쇄자","Tharizdun":"타리즈둔","Demogorgon":"데모고르곤",
 "Dendar the Night Serpent":"밤의 뱀 덴다르","Svartr Aska":"스바르트르 아스카","Halaster":"할라스터",
 "Kezef the Chaos Hound":"혼돈사냥개 케제프","clay golem":"점토 골렘","flesh golem":"살점 골렘",
 "iron golem":"강철 골렘","stone golem":"돌 골렘"}

def build_map(rows):
    tr={}; be_main={}
    it_rows=[r for r in rows if r['key'].startswith('it:')]
    be_rows=[r for r in rows if r['key'].endswith(':0x29') and r['key'].startswith('be:')]
    assert len(it_rows)==len(IT), f'it {len(it_rows)} vs {len(IT)}'
    BE2L = list(BE) + [None]*(len(be_rows)-len(BE))
    for r,ko in zip(it_rows, IT): tr[r['key']]=ko
    for r,ko in zip(be_rows, BE2L):
        if not ko: continue
        tr[r['key']]=ko; be_main[int(r['key'].split(':')[1])]=(r['en'], ko)
    for r in rows:
        if r['key'].split(':')[0] in ('ta','mt') and r['en'] in TA: tr[r['key']]=TA[r['en']]
    # be 두번째 필드
    for r in rows:
        pref,idx,off = r['key'].split(':'); idx=int(idx)
        if pref=='be' and off=='0x48':
            en=r['en']
            if '%' in en: continue                       # 이름 생성 매크로 — 원문 유지
            if idx in be_main and en==be_main[idx][0]: tr[r['key']]=be_main[idx][1]
            elif en in BE2: tr[r['key']]=BE2[en]
    return tr

if __name__=='__main__':
    src='orig/Zorbus_EN_original.zbs'
    raw0=open(src,'rb').read()
    head2, _tp, _dl, cks24 = C2.unpack(raw0)
    plain=decode_file(src)
    rows_d, tail = zbs_tool.extract(plain)
    rows=[r for r in rows_d if r['kind']=='rec']
    tr=build_map([{'key':r['key'],'en':r['en']} for r in rows])
    print(f'레코드 필드 {len(rows)} 중 번역 적용 {len(tr)}개')
    untr=[r for r in rows if r['key'] not in tr and '%' not in r['en']]
    print('미번역', len(untr), [r['en'] for r in untr[:10]])
    # 블롭(본문 텍스트) 번역 병합
    import glob
    blob={}
    for f in sorted(glob.glob(os.path.join(os.path.dirname(os.path.abspath(__file__)),'tl/blob/ko_*.json'))):
        blob.update(json.load(open(f,encoding='utf-8')))
    for k,v in blob.items(): tr[f'blob:{k}']=v
    print(f'블롭 번역 {len(blob)}줄 병합')
    out=zbs_tool.rebuild(plain, rows_d, tr)
    enc=C2.pack(head2, out[2:-28], cks24)
    open('/mnt/user-data/outputs/Zorbus.zbs','wb').write(enc)
    print(f'생성 완료 {len(enc):,} bytes  (원본 {os.path.getsize(src):,})')
    # 검증: 다시 복호해서 읽어보기
    chk=zbs_tool.decode_file if False else None
    _h,_p,_d,_c = C2.unpack(enc)
    p2 = b'\x00\x00'+_p+b'\x00'*28
    print('  복호크기 기록', _d, '실제', len(_p), 'OK' if _d==len(_p) else '불일치')
    r2,_=zbs_tool.extract(p2)
    samples=[x for x in r2 if x['kind']=='rec'][:3]+[x for x in r2 if x['key'].startswith('be:47')]
    for s in samples: print('  ', s['key'], s['en'])
