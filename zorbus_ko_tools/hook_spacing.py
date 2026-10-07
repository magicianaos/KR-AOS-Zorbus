#!/usr/bin/env python3
"""자간 벌리기 함수(VA 0x22A024) CP949 대응 패치

원본 루프(0x22A05D~0x22A070, 20바이트)는 바이트 사이마다 공백을 끼워 넣어
CP949 한글 2바이트를 반토막 낸다. 루프를 새 실행 섹션(.kohook)으로 옮기고,
문자열을 앞에서부터 파싱해 '글자 경계'에서만 공백을 넣도록 바꾼다.
  - ASCII 는 모든 위치가 경계 → 원본과 동일 ("E M A I L")
  - CP949 한글은 2바이트 단위 경계 → "설 정"
"""
import struct, sys
import exe_patch as P

LOOP_OFF_VA   = 0x22A05D      # 루프 시작 VA
LOOP_END_VA   = 0x22A071      # 루프 다음 VA (복귀 지점)
SPACE_CONST   = 0x22A09C      # " " Delphi 상수 VA
LSTRINSERT_VA = 0x141FC       # System.@LStrInsert

def make_code(cave_va, insert_va, ret_va):
    C = cave_va
    b = bytearray()
    b += bytes.fromhex('8B16')            # +00 L1:  mov edx,[esi]
    b += bytes.fromhex('B901000000')      # +02      mov ecx,1
    b += bytes.fromhex('3BCB')            # +07 PRS: cmp ecx,ebx
    b += bytes.fromhex('7D10')            # +09      jge DONE(+0x1B)
    b += bytes.fromhex('8A440AFF')        # +0B      mov al,[edx+ecx-1]
    b += bytes.fromhex('3C81')            # +0F      cmp al,0x81
    b += bytes.fromhex('7205')            # +11      jb ONE(+0x18)
    b += bytes.fromhex('83C102')          # +13      add ecx,2
    b += bytes.fromhex('EBEF')            # +16      jmp PRS
    b += bytes.fromhex('41')              # +18 ONE: inc ecx
    b += bytes.fromhex('EBEC')            # +19      jmp PRS
    b += bytes.fromhex('3BCB')            # +1B DONE:cmp ecx,ebx
    b += bytes.fromhex('750E')            # +1D      jne SKIP(+0x2D)
    b += bytes.fromhex('8BD6')            # +1F      mov edx,esi
    b += bytes.fromhex('8BCB')            # +21      mov ecx,ebx
    b += b'\xB8' + struct.pack('<I', SPACE_CONST)          # +23 mov eax,SPACE
    b += b'\xE8' + struct.pack('<i', insert_va - (C+0x2D)) # +28 call LStrInsert
    b += bytes.fromhex('4B')              # +2D SKIP:dec ebx
    b += bytes.fromhex('83FB01')          # +2E      cmp ebx,1
    b += bytes.fromhex('75CD')            # +31      jne L1
    b += b'\xE9' + struct.pack('<i', ret_va - (C+0x38))    # +33 jmp 0x22A071
    assert len(b) == 0x38, len(b)
    return bytes(b)

def add_exec_section(d, info, name, data):
    salign, falign = info['salign'], info['falign']
    last = max(info['secs'], key=lambda s: s['va'])
    sec_va  = P.align(last['va'] + last['vsz'], salign)
    sec_raw = P.align(len(d), falign)
    d = bytearray(d) + b'\x00' * (sec_raw - len(d))
    raw = bytes(data) + b'\x00' * (P.align(len(data), falign) - len(data))
    d += raw
    ent = info['sectab'] + info['nsec'] * 40
    hdr = (name.encode('latin1').ljust(8, b'\x00')
           + struct.pack('<IIII', len(data), sec_va, len(raw), sec_raw)
           + b'\x00' * 12 + struct.pack('<I', 0x60000020))   # CODE|EXECUTE|READ
    d[ent:ent+40] = hdr
    d[info['pe']+6:info['pe']+8] = struct.pack('<H', info['nsec'] + 1)
    d[info['sizeimg']:info['sizeimg']+4] = struct.pack('<I', P.align(sec_va + len(data), salign))
    return d, P.parse_pe(bytes(d)), sec_va

def patch(path):
    d = bytearray(open(path, 'rb').read())
    info = P.parse_pe(d)
    loop_off = P.va2off(info, LOOP_OFF_VA)
    orig = bytes(d[loop_off:loop_off+20])
    expect = bytes.fromhex('8BD6') + bytes.fromhex('8BCB') + b'\xB8' + struct.pack('<I', SPACE_CONST)
    assert orig.startswith(expect), f'루프 시작 바이트 불일치: {orig.hex()}'
    ins_rel = struct.unpack('<i', orig[10:14])[0]
    insert_va = LOOP_OFF_VA + 14 + ins_rel
    assert insert_va == LSTRINSERT_VA, hex(insert_va)

    code = make_code(0, insert_va, LOOP_END_VA)          # 자리표시(길이만 확정)
    d, info2, sec_va = add_exec_section(d, info, '.kohook', code)
    cave_va = info2['base'] + sec_va
    code = make_code(cave_va, insert_va, LOOP_END_VA)    # 실제 주소로 재생성
    sec = [s for s in info2['secs'] if s['name'] == '.kohook'][0]
    d[sec['raw']:sec['raw']+len(code)] = code

    # 원래 루프 자리 -> 훅으로 점프
    jmp = b'\xE9' + struct.pack('<i', cave_va - (LOOP_OFF_VA + 5))
    d[loop_off:loop_off+20] = jmp + b'\x90' * (20 - len(jmp))
    open(path, 'wb').write(bytes(d))
    print(f'자간 함수 훅 적용: .kohook @ VA {hex(cave_va)} ({len(code)} bytes)')

if __name__ == '__main__':
    patch(sys.argv[1] if len(sys.argv) > 1 else '/mnt/user-data/outputs/Zorbus.exe')
