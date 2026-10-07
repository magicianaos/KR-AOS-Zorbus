#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Zorbus.exe 실행코드 훅 (r9)

1) 자간 벌리기 함수(VA 0x22A024) CP949 대응
2) SysUtils.Format(VA 0x19894) 뒤에 조사 자동 선택 훅
   번역문에 "이(가)" "을(를)" "은(는)" "와(과)" 를 그대로 써 두면
   실행 시점에 앞 글자 받침을 보고 하나로 줄여 준다.

두 훅과 65536바이트 받침표를 새 실행 섹션 .kohook 에 넣는다.
"""
import struct, sys
import exe_patch as P

SPC_LOOP_VA   = 0x22A05D      # 자간 루프 시작
SPC_END_VA    = 0x22A071      # 자간 루프 다음
SPACE_CONST   = 0x22A09C
LSTRINSERT_VA = 0x141FC
FMT_TAIL_VA   = 0x198A3       # Format 래퍼의 `pop ebp; ret 4; nop` (5바이트)
WPN_VA        = 0x18E648      # 전투 로그: ' with '+무기 를 만드는 자리 (16바이트)
WPN_END_VA    = 0x18E658
LSTRCAT3_VA   = 0x13FB8
LSTRCLR_VA    = 0x13CEC

# 조사 표시 -> (받침없음, 받침있음)  각 CP949 2바이트
MARKERS = [('이','가','가','이'), ('을','를','를','을'),
           ('은','는','는','은'), ('와','과','와','과')]
# 튜플: (표시 앞글자, 표시 뒷글자, 받침없을때, 받침있을때)

def w16(s):
    b=s.encode('cp949'); return b[0] | (b[1]<<8)      # mov [edi],dx 용 (dl=lead)

def marker_bytes(a,b):
    return ('%s(%s)'%(a,b)).encode('cp949')           # 6바이트

def build_table():
    """0 = 받침 없음, 1 = 받침 있음(ㄹ 제외), 2 = ㄹ 받침"""
    t=bytearray(65536)
    for d in '013678': t[ord(d)] = 1                  # 영/일/삼/육/칠/팔
    t[ord('2')]=0; t[ord('4')]=0; t[ord('5')]=0; t[ord('9')]=0
    for lead in range(0x81,0xFF):
        for trail in range(0x41,0xFF):
            try: ch=bytes([lead,trail]).decode('cp949')
            except Exception: continue
            if len(ch)!=1: continue
            cp=ord(ch)
            if 0xAC00<=cp<=0xD7A3:
                j=(cp-0xAC00)%28
                t[(lead<<8)|trail] = 0 if j==0 else (2 if j==8 else 1)
    return bytes(t)

class Asm:
    def __init__(self): self.b=bytearray(); self.lbl={}; self.fix=[]
    def db(self,*x): self.b+=bytes(x)
    def raw(self,h): self.b+=bytes.fromhex(h)
    def label(self,n): self.lbl[n]=len(self.b)
    def jmp8(self,op,n):        # op: 1바이트 옵코드
        self.b+=bytes([op,0]); self.fix.append((len(self.b)-1,n,len(self.b),1))
    def jmp32(self,op_hex,n):
        self.raw(op_hex); self.b+=b'\0'*4; self.fix.append((len(self.b)-4,n,len(self.b),4))
    def resolve(self):
        for pos,n,nxt,sz in self.fix:
            rel=self.lbl[n]-nxt
            if sz==1:
                assert -128<=rel<=127, (n,rel)
                self.b[pos]=rel&0xFF
            else: self.b[pos:pos+4]=struct.pack('<i',rel)
        return bytes(self.b)

def gen(base, table_va, insert_va, sep_va=0):
    """base: 코드 시작 VA"""
    a=Asm()
    # ---------- 0) 자간 루프 ----------
    a.label('spc')
    a.raw('8B16')                    # mov edx,[esi]
    a.raw('B901000000')              # mov ecx,1
    a.label('spc_p')
    a.raw('3BCB'); a.jmp8(0x7D,'spc_done')      # cmp ecx,ebx / jge
    a.raw('8A440AFF')                # mov al,[edx+ecx-1]
    a.raw('3C81'); a.jmp8(0x72,'spc_one')       # cmp al,0x81 / jb
    a.raw('83C102'); a.jmp8(0xEB,'spc_p')
    a.label('spc_one'); a.raw('41'); a.jmp8(0xEB,'spc_p')
    a.label('spc_done')
    a.raw('3BCB'); a.jmp8(0x75,'spc_skip')
    a.raw('8BD6'); a.raw('8BCB')
    a.raw('B8'); a.b+=struct.pack('<I',SPACE_CONST)
    a.raw('E8'); a.b+=b'\0'*4; ins_pos=len(a.b)-4
    a.label('spc_skip')
    a.raw('4B'); a.raw('83FB01'); a.jmp8(0x75,'spc')
    a.raw('E9'); a.b+=b'\0'*4; spc_ret_pos=len(a.b)-4

    # ---------- 1b) 전투 로그: 무기를 대상이 아니라 공격자 쪽에 붙인다 ----------
    a.label('wpn')
    a.raw('8D45BC')                  # lea eax,[ebp-0x44]
    a.raw('8B4DBC')                  # mov ecx,[ebp-0x44]        (무기 이름)
    a.raw('BA'); a.b+=struct.pack('<I', sep_va)      # mov edx, 구분자
    a.raw('E8'); a.b+=b'\0'*4; cat1=len(a.b)-4      # call LStrCat3  -> [ebp-0x44]=구분자+무기
    a.raw('8D45E4')                  # lea eax,[ebp-0x1c]        (공격자)
    a.raw('8B4DBC')                  # mov ecx,[ebp-0x44]
    a.raw('8B55E4')                  # mov edx,[ebp-0x1c]
    a.raw('E8'); a.b+=b'\0'*4; cat2=len(a.b)-4      # call LStrCat3  -> 공격자 += 구분자+무기
    a.raw('8D45BC')                  # lea eax,[ebp-0x44]
    a.raw('E8'); a.b+=b'\0'*4; clr=len(a.b)-4       # call LStrClr   -> 무기 문자열 비우기
    a.raw('E9'); a.b+=b'\0'*4; wret=len(a.b)-4      # jmp 0x18E658

    # ---------- 1) Format 꼬리 훅 ----------
    a.label('fmt')
    a.raw('8B4508')                  # mov eax,[ebp+8]
    a.raw('8B00')                    # mov eax,[eax]
    a.jmp32('E8','josa')             # call josa
    a.raw('5D')                      # pop ebp
    a.raw('C20400')                  # ret 4

    # ---------- 2) 조사 치환 ----------
    a.label('josa')
    a.raw('85C0'); a.raw('7501'); a.raw('C3')    # test eax,eax / jnz +1 / ret
    a.raw('53'); a.raw('56'); a.raw('57')       # push ebx,esi,edi
    a.raw('50')                                  # push eax (start)
    a.raw('8BF0'); a.raw('8BF8')                # mov esi,eax / mov edi,eax
    a.raw('8B48FC'); a.raw('03C8')              # mov ecx,[eax-4] / add ecx,eax
    a.raw('33DB')                                # xor ebx,ebx
    a.label('j_loop')
    a.raw('3BF1'); a.jmp32('0F83','j_done')     # cmp esi,ecx / jae
    a.raw('8A06')                                # mov al,[esi]
    a.raw('3C81'); a.jmp32('0F82','j_ascii')    # cmp al,0x81 / jb
    a.raw('8D5606'); a.raw('3BD1'); a.jmp32('0F87','j_copy2')  # lea edx,[esi+6] / cmp edx,ecx / ja
    a.raw('8B06')                                # mov eax,[esi]
    # --- 로(으로) : 8바이트 마커, 출력 2 또는 4바이트
    RO=('로(으로)').encode('cp949'); assert len(RO)==8
    a.raw('3D'); a.b+=RO[:4]                     # cmp eax,imm32
    a.jmp32('0F85','j_m0')
    a.raw('8D5608'); a.raw('3BD1'); a.jmp32('0F87','j_m0')   # lea edx,[esi+8]/cmp/ja
    a.raw('817E04'); a.b+=RO[4:8]                # cmp dword[esi+4],imm32
    a.jmp32('0F85','j_m0')
    a.raw('0FB7C3')                              # movzx eax,bx
    a.raw('BA'); a.b+=struct.pack('<I',table_va) # mov edx,TABLE
    a.raw('8A0402')                              # mov al,[edx+eax]
    a.raw('3C01'); a.jmp8(0x75,'j_ro_short')     # cmp al,1 / jne
    a.raw('C707'); a.b+=('으로').encode('cp949') # mov dword[edi],'으로'
    a.raw('83C704')                              # add edi,4
    a.jmp8(0xEB,'j_ro_end')
    a.label('j_ro_short')
    a.raw('66C707'); a.b+=('로').encode('cp949') # mov word[edi],'로'
    a.raw('83C702')                              # add edi,2
    a.label('j_ro_end')
    a.raw('B7B7'); a.raw('B3CE')                 # mov bh,0xB7 / mov bl,0xCE
    a.raw('83C608')                              # add esi,8
    a.jmp32('E9','j_loop')
    a.label('j_m0')
    for i,(m1,m2,no,yes) in enumerate(MARKERS):
        mb=marker_bytes(m1,m2); assert len(mb)==6
        nxt = f'j_m{i+1}' if i+1<len(MARKERS) else 'j_copy2'
        a.raw('3D'); a.b+=mb[:4]                 # cmp eax,imm32
        a.jmp32('0F85',nxt)
        a.raw('66817E04'); a.b+=mb[4:6]          # cmp word[esi+4],imm16
        a.jmp32('0F85',nxt)
        a.raw('BA'); a.b+=struct.pack('<HH', w16(no), w16(yes))   # mov edx,pair
        a.jmp32('E9','j_subst')
        if i+1<len(MARKERS): a.label(f'j_m{i+1}')
    a.label('j_subst')
    a.raw('0FB7C3')                              # movzx eax,bx
    a.raw('52')                                  # push edx
    a.raw('BA'); a.b+=struct.pack('<I',table_va) # mov edx,TABLE
    a.raw('8A0402')                              # mov al,[edx+eax]
    a.raw('5A')                                  # pop edx
    a.raw('84C0'); a.jmp8(0x74,'j_noj')          # test al,al / jz
    a.raw('C1EA10')                              # shr edx,16
    a.label('j_noj')
    a.raw('668917')                              # mov [edi],dx
    a.raw('88D7'); a.raw('88F3')                 # mov bh,dl / mov bl,dh
    a.raw('83C702'); a.raw('83C606')             # add edi,2 / add esi,6
    a.jmp32('E9','j_loop')
    a.label('j_copy2')
    a.raw('8A06'); a.raw('8A6601')               # mov al,[esi] / mov ah,[esi+1]
    a.raw('8807'); a.raw('886701')               # mov [edi],al / mov [edi+1],ah
    a.raw('88C7'); a.raw('88E3')                 # mov bh,al / mov bl,ah
    a.raw('83C602'); a.raw('83C702')
    a.jmp32('E9','j_loop')
    a.label('j_ascii')
    a.raw('8807'); a.raw('30FF'); a.raw('88C3')  # mov [edi],al / xor bh,bh / mov bl,al
    a.raw('46'); a.raw('47')
    a.jmp32('E9','j_loop')
    a.label('j_done')
    a.raw('5A')                                  # pop edx  (start)
    a.raw('8BC7'); a.raw('2BC2')                 # mov eax,edi / sub eax,edx
    a.raw('8942FC')                              # mov [edx-4],eax
    a.raw('C60700')                              # mov byte[edi],0
    a.raw('5F'); a.raw('5E'); a.raw('5B')        # pop edi,esi,ebx
    a.label('j_ret0')
    a.raw('C3')
    code=bytearray(a.resolve())
    # 절대/상대 주소 마무리
    struct.pack_into('<i', code, ins_pos, insert_va - (base+ins_pos+4))
    struct.pack_into('<i', code, spc_ret_pos, SPC_END_VA - (base+spc_ret_pos+4))
    struct.pack_into('<i', code, cat1, LSTRCAT3_VA - (base+cat1+4))
    struct.pack_into('<i', code, cat2, LSTRCAT3_VA - (base+cat2+4))
    struct.pack_into('<i', code, clr,  LSTRCLR_VA  - (base+clr+4))
    struct.pack_into('<i', code, wret, WPN_END_VA  - (base+wret+4))
    return bytes(code), a.lbl

def add_exec_section(d, info, name, data):
    salign, falign = info['salign'], info['falign']
    last=max(info['secs'], key=lambda s:s['va'])
    sec_va  = P.align(last['va']+last['vsz'], salign)
    sec_raw = P.align(len(d), falign)
    d = bytearray(d) + b'\x00'*(sec_raw-len(d))
    raw = bytes(data) + b'\x00'*(P.align(len(data), falign)-len(data))
    d += raw
    ent = info['sectab'] + info['nsec']*40
    hdr = (name.encode('latin1').ljust(8,b'\x00')
           + struct.pack('<IIII', len(data), sec_va, len(raw), sec_raw)
           + b'\x00'*12 + struct.pack('<I', 0x60000020))    # CODE|EXECUTE|READ
    d[ent:ent+40]=hdr
    d[info['pe']+6:info['pe']+8]=struct.pack('<H', info['nsec']+1)
    d[info['sizeimg']:info['sizeimg']+4]=struct.pack('<I', P.align(sec_va+len(data), salign))
    return d, P.parse_pe(bytes(d)), sec_va

def patch(path):
    d=bytearray(open(path,'rb').read())
    info=P.parse_pe(d)
    # --- 원본 바이트 확인
    spc_off=P.va2off(info, SPC_LOOP_VA)
    orig=bytes(d[spc_off:spc_off+20])
    assert orig.startswith(bytes.fromhex('8BD68BCB')+b'\xB8'+struct.pack('<I',SPACE_CONST)), orig.hex()
    insert_va = SPC_LOOP_VA + 14 + struct.unpack('<i', orig[10:14])[0]
    assert insert_va==LSTRINSERT_VA, hex(insert_va)
    fmt_off=P.va2off(info, FMT_TAIL_VA)
    assert bytes(d[fmt_off:fmt_off+5])==bytes.fromhex('5DC2040090'), bytes(d[fmt_off:fmt_off+5]).hex()
    wpn_off=P.va2off(info, WPN_VA)
    w=bytes(d[wpn_off:wpn_off+16])
    assert w.startswith(bytes.fromhex('8D45BC8B4DBCBA')), w.hex()
    sep_va=struct.unpack('<I', w[7:11])[0]          # 구분자 상수 VA (재배치됐을 수 있음)
    assert w[11]==0xE8 and (WPN_VA+16+struct.unpack('<i',w[12:16])[0])==LSTRCAT3_VA, w.hex()

    table=build_table()
    code0,_=gen(0, 0, insert_va, sep_va)
    code_len=(len(code0)+15)//16*16
    # 자리 확정 후 재생성
    d2, info2, sec_va = add_exec_section(d, info, '.kohook', b'\x00'*(code_len+len(table)))
    base=info2['base']+sec_va
    table_va=base+code_len
    code,lbl=gen(base, table_va, insert_va, sep_va)
    sec=[s for s in info2['secs'] if s['name']=='.kohook'][0]
    d2[sec['raw']:sec['raw']+len(code)]=code
    d2[sec['raw']+code_len:sec['raw']+code_len+len(table)]=table
    # 훅 연결
    spc_va=base+lbl['spc']; fmt_va=base+lbl['fmt']
    d2[spc_off:spc_off+20]=b'\xE9'+struct.pack('<i', spc_va-(SPC_LOOP_VA+5))+b'\x90'*15
    d2[fmt_off:fmt_off+5]=b'\xE9'+struct.pack('<i', fmt_va-(FMT_TAIL_VA+5))
    wpn_va=base+lbl['wpn']
    d2[wpn_off:wpn_off+16]=b'\xE9'+struct.pack('<i', wpn_va-(WPN_VA+5))+b'\x90'*11
    open(path,'wb').write(bytes(d2))
    print(f'훅 적용: .kohook @ {hex(base)}  코드 {len(code)}B  받침표 {len(table)}B'
          f'  (자간 {hex(spc_va)} / 조사 {hex(fmt_va)} / 무기 {hex(wpn_va)}, 구분자 {hex(sep_va)})')

if __name__=='__main__':
    patch(sys.argv[1] if len(sys.argv)>1 else '/mnt/user-data/outputs/Zorbus.exe')
