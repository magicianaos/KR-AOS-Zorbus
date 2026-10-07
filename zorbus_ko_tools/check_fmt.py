#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""번역문의 Delphi 서식 지정자 검증

원문과 번역문의 %d/%s 순서·개수가 어긋나면 게임이
"Format '%s' invalid or incompatible with argument" 로 죽는다.
순서를 바꾸려면 반드시 위치 지정자(%0:d %1:s)를 쓸 것.
"""
import json, glob, re, struct, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import exe_patch as P

SPEC = re.compile(r'%(?:(\d+):)?[-]?(?:\d+|\*)?(?:\.(?:\d+|\*))?([diuoxXeEfgGnmpsSbcv%])')

def specs(t):
    return [(m.group(1), m.group(2).lower()) for m in SPEC.finditer(t) if m.group(2) != '%']

def all_strings(path):
    d = open(path, 'rb').read()
    out = {}
    for m in re.finditer(rb'\xff\xff\xff\xff', d):
        p = m.end()
        if p + 4 > len(d): continue
        L = struct.unpack('<I', d[p:p+4])[0]
        if not (1 <= L <= 4000) or p+4+L >= len(d) or d[p+4+L] != 0: continue
        out[p+4] = d[p+4:p+4+L]
    return out

def check(src='orig/Zorbus_EN_original.exe'):
    strs = all_strings(src)
    KEEP = json.load(open('tl/exe/keep.json', encoding='utf-8'))
    byid = {r['id']: r for r in KEEP}
    bad = []
    for f in sorted(glob.glob('tl/exe/ko_*.json')):
        off_keyed = f.endswith(('ko_ext_off.json', 'ko_race.json', 'ko_raw.json'))
        for k, v in json.load(open(f, encoding='utf-8')).items():
            if not isinstance(v, str): continue
            off = int(k) if off_keyed else byid.get(int(k), {}).get('offset')
            if off is None: continue
            en = strs.get(off, b'').decode('latin1')
            se, sk = specs(en), specs(v)
            if any(x[0] for x in sk):                 # 위치 지정자 사용
                for idx, typ in sk:
                    if idx is None: continue
                    i = int(idx)
                    if i >= len(se) or se[i][1] != typ:
                        bad.append((f, k, en, v, f'인덱스 {i} 가 원문과 안 맞음')); break
                continue
            if len(sk) > len(se) or [x[1] for x in sk] != [x[1] for x in se][:len(sk)]:
                bad.append((f, k, en, v, '개수/순서 불일치'))
    return bad

if __name__ == '__main__':
    bad = check()
    for f, k, en, v, why in bad:
        print(f'[{why}] {f} {k}\n   EN: {en!r}\n   KO: {v!r}')
    print(f'서식 불일치 {len(bad)}건')
    sys.exit(1 if bad else 0)
