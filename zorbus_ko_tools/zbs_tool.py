#!/usr/bin/env python3
"""Zorbus.zbs 문자열 추출 / 재삽입

구조
  1) 고정크기 레코드 배열   : it_/be_/ta_/mt_/co_ ... 각 레코드 안에 ShortString 필드
  2) 파일 끝 텍스트 블롭    : \r\n 구분 라인 목록 (설명문·대사). 줄 수 유지, 길이는 자유
"""
import re, json, csv, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from zbs_codec import decode_file, encode_file

BLOB_START = 0x238d0d2      # 텍스트 블롭 시작(평문 기준)

# 배열정의: prefix -> (base, stride, count, [ (필드오프셋, 용량) ... ])
ARRAYS = {
 'it': (0x0000067, 5140,  477, [(0x13e0, 52)]),
 'be': (0x02a9a9b, 25336, 509, [(0x29, 31), (0x48, 31)]),
 'ta': (0x0255597, 1908,  181, [(0x29, 41)]),   # 182 -> 181: 마지막 항목이 be 배열 시작을 침범
 'mt': (0x0279aef, 1908,  103, [(0x29, 41)]),   # 104 -> 103: 마지막 항목이 be 배열 시작을 침범
}

def read_field(p, off):
    L = p[off]
    return p[off+1:off+1+L].decode('latin1')

def extract(plain: bytes):
    rows = []
    for pref,(base,stride,cnt,fields) in ARRAYS.items():
        rbase = base-1
        for i in range(cnt):
            r0 = rbase + i*stride
            ident = read_field(plain, r0)
            for fo,cap in fields:
                o = r0+fo
                s = read_field(plain, o)
                if s: rows.append(dict(kind='rec', key=f'{pref}:{i}:{fo:#x}',
                                       off=o, cap=cap-1, ident=ident, en=s))
    blob = plain[BLOB_START:]
    # 끝 28바이트 트레일러 분리
    tail_i = blob.rfind(b'\r\n')+2
    lines = blob[:tail_i].split(b'\r\n')[:-1]
    for i,l in enumerate(lines):
        rows.append(dict(kind='line', key=f'blob:{i}', off=-1, cap=0,
                         ident='', en=l.decode('latin1')))
    return rows, blob[tail_i:]

def rebuild(plain: bytes, rows, trans: dict) -> bytes:
    b = bytearray(plain)
    # 1) 레코드 필드
    for r in rows:
        if r['kind']!='rec': continue
        ko = trans.get(r['key'])
        if not ko: continue
        enc = ko.encode('cp949', errors='replace')
        if len(enc) > r['cap']:
            raise ValueError(f"용량초과 {r['key']} {len(enc)}>{r['cap']} : {ko}")
        o=r['off']; cap=r['cap']
        b[o] = len(enc)
        b[o+1:o+1+cap] = enc + b'\x00'*(cap-len(enc))
    # 2) 텍스트 블롭 (줄 수 유지)
    lines=[]
    for r in rows:
        if r['kind']!='line': continue
        ko = trans.get(r['key'])
        lines.append((ko.encode('cp949', errors='replace') if ko else r['en'].encode('latin1')))
    _, tail = extract(plain)
    newblob = b'\r\n'.join(lines) + b'\r\n' + tail
    return bytes(b[:BLOB_START]) + newblob

if __name__ == '__main__':
    src='/mnt/user-data/uploads/Zorbus/Data/Zorbus.zbs'
    plain = decode_file(src)
    rows, tail = extract(plain)
    recs=[r for r in rows if r['kind']=='rec']; lines=[r for r in rows if r['kind']=='line']
    print(f'레코드 필드 {len(recs)}개 / 블롭 라인 {len(lines)}개')
    print(f'블롭 텍스트 {sum(len(r["en"]) for r in lines):,} bytes, 트레일러 {len(tail)} bytes')
    # 무수정 재구성 검증
    rebuilt = rebuild(plain, rows, {})
    print('무수정 재구성:', 'OK' if rebuilt==plain else f'불일치 {len(rebuilt)} vs {len(plain)}')
    enc = encode_file(rebuilt)
    print('재암호화 원본 일치:', 'OK' if enc==open(src,'rb').read() else '불일치')
    with open('/mnt/user-data/outputs/zbs_translate.csv','w',newline='',encoding='utf-8-sig') as f:
        w=csv.writer(f); w.writerow(['key','kind','ident','cap','en','ko'])
        for r in rows: w.writerow([r['key'],r['kind'],r['ident'],r['cap'],r['en'],''])
    print('→ /mnt/user-data/outputs/zbs_translate.csv')
