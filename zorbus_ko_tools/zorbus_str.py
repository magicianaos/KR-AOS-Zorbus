#!/usr/bin/env python3
"""Zorbus 한글화 도구 - Delphi AnsiString 상수 추출 / 재삽입"""
import re, struct, csv, sys, os

EXE = '/mnt/user-data/uploads/Zorbus/Zorbus.exe'

# ---------- PE 오프셋 <-> VA ----------
def pe_sections(d):
    pe = struct.unpack('<I', d[0x3c:0x40])[0]
    nsec = struct.unpack('<H', d[pe+6:pe+8])[0]
    optsz = struct.unpack('<H', d[pe+20:pe+22])[0]
    base = struct.unpack('<I', d[pe+24+28:pe+24+32])[0]
    off = pe+24+optsz
    secs=[]
    for i in range(nsec):
        e=d[off+i*40:off+(i+1)*40]
        name=e[:8].rstrip(b'\x00').decode('latin1')
        vsz,va,rsz,raw = struct.unpack('<IIII', e[8:24])
        secs.append((name, va, vsz, raw, rsz))
    return base, secs

def off2va(off, base, secs):
    for n,va,vsz,raw,rsz in secs:
        if raw <= off < raw+rsz: return base+va+(off-raw)
    return None

# ---------- 문자열 추출 ----------
NONTRANS = [
    re.compile(rb'^[a-z][a-z0-9_]*$'),            # it_xxx, cr_xxx 내부 ID
    re.compile(rb'^[A-Za-z0-9_.\\/:%-]+\.(txt|dll|exe|pdf|png|jpg|zbs|zts|zse|zti)$', re.I),
    re.compile(rb'^https?://'),
    re.compile(rb'^[A-Z][A-Za-z0-9_]*$'),          # 클래스명/식별자
    re.compile(rb'^[%sdxg0-9.\-+ :,]*$'),          # 포맷 문자열만
    re.compile(rb'^[a-z]+(,[a-z ]+)+$'),           # graphics,color 같은 태그
]
def is_translatable(s: bytes) -> bool:
    if len(s) < 2: return False
    if not any(0x61 <= b <= 0x7a for b in s): return False   # 소문자 없음 → 대개 식별자
    for p in NONTRANS:
        if p.match(s): return False
    return True

def extract(path=EXE):
    d = open(path,'rb').read()
    base, secs = pe_sections(d)
    rows=[]
    for m in re.finditer(rb'\xff\xff\xff\xff', d):
        p = m.end()
        if p+4 > len(d): continue
        ln = struct.unpack('<I', d[p:p+4])[0]
        if not (1 <= ln <= 4000) or p+4+ln >= len(d): continue
        if d[p+4+ln] != 0: continue
        s = d[p+4:p+4+ln]
        if not all(32 <= b < 127 or b in (9,10,13) for b in s): continue
        rows.append({'off':p+4, 'va':off2va(p+4, base, secs), 'len':ln,
                     'trans': is_translatable(s), 'text': s.decode('latin1')})
    return d, rows

if __name__ == '__main__':
    d, rows = extract()
    tr = [r for r in rows if r['trans']]
    print(f"전체 상수 {len(rows)}개 / 번역대상 {len(tr)}개")
    print(f"번역대상 총 바이트 {sum(r['len'] for r in tr):,}")
    # 길이 분포
    import collections
    b=collections.Counter()
    for r in tr:
        L=r['len']
        b['1-10' if L<=10 else '11-30' if L<=30 else '31-60' if L<=60 else '61-120' if L<=120 else '121+']+=1
    print('길이 분포', dict(b))
    os.makedirs('/mnt/user-data/outputs', exist_ok=True)
    with open('/mnt/user-data/outputs/zorbus_strings.csv','w',newline='',encoding='utf-8-sig') as f:
        w=csv.writer(f); w.writerow(['id','offset','va','max_bytes','original','korean','note'])
        for i,r in enumerate(tr):
            w.writerow([i, r['off'], hex(r['va'] or 0), r['len'], r['text'], '', ''])
    print("→ /mnt/user-data/outputs/zorbus_strings.csv")
