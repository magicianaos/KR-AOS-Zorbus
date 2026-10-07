#!/usr/bin/env python3
"""Zorbus.exe 한글판 빌드 (v2)
  - tl/exe/ko_*.json  : id 기준 번역 (keep.json 으로 offset 변환)
  - tl/exe/ko_ext_off.json : offset 기준 번역 (1차 추출 누락분)
  - 마지막에 zbs 무결성 검사 우회 패치 적용
"""
import json, glob, sys, os, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import exe_patch

SRC = 'orig/Zorbus_EN_original.exe'
DST = '/mnt/user-data/outputs/Zorbus.exe'
BYPASS_OFF = 0x0A7C8C          # 0xB888C: 55 8B EC -> B0 01 C3 (mov al,1; ret)

KEEP = json.load(open('tl/exe/keep.json', encoding='utf-8'))
byid = {r['id']: r for r in KEEP}
tr = {}
n1 = 0
for f in sorted(glob.glob('tl/exe/ko_*.json')):
    if f.endswith(('ko_ext_off.json','ko_race.json')): continue
    for k, v in json.load(open(f, encoding='utf-8')).items():
        if int(k) in byid:
            tr[byid[int(k)]['offset']] = v; n1 += 1
ext = json.load(open('tl/exe/ko_ext_off.json', encoding='utf-8'))
for k, v in ext.items(): tr[int(k)] = v
# 종족·성별·크기·성향 이름표 (오프셋 기준, 되돌리기 쉽게 별도 파일)
race = json.load(open('tl/exe/ko_race.json', encoding='utf-8'))
for k, v in race.items(): tr[int(k)] = v
print(f'번역 적용: 기존 {n1}개 + 추가 {len(ext)}개 + 종족표 {len(race)}개 = 총 {len(tr)}개 오프셋')

# 서식 지정자 검증 (여기서 걸리면 게임이 Format 예외로 죽는다)
import check_fmt
_bad = check_fmt.check(SRC)
if _bad:
    for _f,_k,_en,_v,_w in _bad: print(f'  [{_w}] {_f} {_k}\n     EN: {_en!r}\n     KO: {_v!r}')
    raise SystemExit(f'서식 불일치 {len(_bad)}건 — 빌드 중단')
print('서식 지정자 검증 OK')

exe_patch.build(SRC, DST, tr)
d = bytearray(open(DST, 'rb').read())
assert d[BYPASS_OFF:BYPASS_OFF+3] == bytes.fromhex('558bec'), '우회 패치 위치 불일치'
d[BYPASS_OFF:BYPASS_OFF+3] = bytes.fromhex('b001c3')
open(DST, 'wb').write(bytes(d))
print('무결성 검사 우회 패치 적용, 최종 크기', len(d))

# 추출기가 걸러낸(비ASCII 바이트 포함) 문자열 직접 패치
raw = json.load(open('tl/exe/ko_raw.json', encoding='utf-8'))
if raw:
    b = bytearray(open(DST,'rb').read())
    for k, v in raw.items():
        off = int(k); L = struct.unpack('<I', b[off-4:off])[0]
        enc = v.encode('cp949')
        assert len(enc) <= L, f'{k} 길이 초과 {len(enc)}>{L}'
        b[off-4:off] = struct.pack('<I', len(enc))
        b[off:off+L+1] = enc + b'\x00'*(L+1-len(enc))
    open(DST,'wb').write(bytes(b))
    print(f'직접 패치 {len(raw)}개')

# 난독화된 문자열(뒤집기 + XOR 1) 직접 패치 — 원형 캐릭터 이름
enc = json.load(open('tl/exe/ko_enc.json', encoding='utf-8'))
if enc:
    b = bytearray(open(DST,'rb').read())
    for k, v in enc.items():
        off = int(k); L = struct.unpack('<I', b[off-4:off])[0]
        e = bytes(c ^ 1 for c in v.encode('cp949'))[::-1]
        assert len(e) <= L, f'{k} 길이 초과 {len(e)}>{L}'
        b[off-4:off] = struct.pack('<I', len(e))
        b[off:off+L+1] = e + b'\x00'*(L+1-len(e))
    open(DST,'wb').write(bytes(b))
    print(f'난독 문자열 패치 {len(enc)}개')

# 실행코드 훅: 자간 벌리기 CP949 대응 + 조사 자동 선택
import hook_patch
hook_patch.patch(DST)
