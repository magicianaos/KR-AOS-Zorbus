#!/usr/bin/env python3
"""Zorbus.exe 한글 패처 — 인플레이스 + 새 섹션 재배치

- Delphi AnsiString 상수: [FF FF FF FF][len:4][본문][00]
- 원본 길이 이하 -> 제자리 교체 (길이 필드 갱신)
- 초과 -> 새 섹션(.kotext)에 기록하고, 해당 문자열을 가리키는
  절대주소 참조(.reloc 목록으로 검증)를 새 주소로 패치
"""
import struct, re, sys, json

def parse_pe(d):
    pe=struct.unpack('<I', d[0x3c:0x40])[0]
    nsec=struct.unpack('<H', d[pe+6:pe+8])[0]
    optsz=struct.unpack('<H', d[pe+20:pe+22])[0]
    opt=pe+24
    base=struct.unpack('<I', d[opt+28:opt+32])[0]
    salign=struct.unpack('<I', d[opt+32:opt+36])[0]
    falign=struct.unpack('<I', d[opt+36:opt+40])[0]
    sizeimg=opt+56
    sectab=opt+optsz
    secs=[]
    for i in range(nsec):
        e=d[sectab+i*40:sectab+(i+1)*40]
        secs.append(dict(name=e[:8].rstrip(b'\0').decode('latin1'),
            vsz=struct.unpack('<I',e[8:12])[0], va=struct.unpack('<I',e[12:16])[0],
            rsz=struct.unpack('<I',e[16:20])[0], raw=struct.unpack('<I',e[20:24])[0],
            chars=struct.unpack('<I',e[36:40])[0], _off=sectab+i*40))
    return dict(pe=pe,nsec=nsec,opt=opt,base=base,salign=salign,falign=falign,
                sizeimg=sizeimg,sectab=sectab,secs=secs)

def off2va(info,o):
    for s in info['secs']:
        if s['raw']<=o<s['raw']+s['rsz']: return info['base']+s['va']+(o-s['raw'])
def va2off(info,v):
    r=v-info['base']
    for s in info['secs']:
        if s['va']<=r<s['va']+s['rsz']: return s['raw']+(r-s['va'])

def reloc_targets(d, info):
    """.reloc 이 가리키는 '절대주소가 저장된 위치'들의 파일 오프셋 집합"""
    rel=next((s for s in info['secs'] if s['name']=='.reloc'), None)
    if not rel: return set()
    out=set(); p=rel['raw']; end=rel['raw']+rel['rsz']
    while p+8<=end:
        page,blk=struct.unpack('<II', d[p:p+8])
        if blk<8 or p+blk>end: break
        for q in range(p+8, p+blk, 2):
            e=struct.unpack('<H', d[q:q+2])[0]
            if (e>>12)==3:
                o=va2off(info, info['base']+page+(e&0xFFF))
                if o is not None: out.add(o)
        p+=blk
    return out

def find_strings(d):
    out=[]
    for m in re.finditer(rb'\xff\xff\xff\xff', d):
        p=m.end()
        if p+4>len(d): continue
        L=struct.unpack('<I', d[p:p+4])[0]
        if not (1<=L<=4000) or p+4+L>=len(d) or d[p+4+L]!=0: continue
        s=d[p+4:p+4+L]
        if all(32<=b<127 or b in (9,10,13) for b in s):
            out.append((p+4, L, s))    # p+4 = 본문 시작 오프셋
    return out

def build(src, dst, trans:dict):
    d=bytearray(open(src,'rb').read())
    info=parse_pe(d)
    relocs=reloc_targets(bytes(d), info)
    print(f'.reloc 절대주소 참조 {len(relocs):,}개')
    strs={p:(L,s) for p,L,s in find_strings(bytes(d))}
    # VA -> 참조 위치 색인
    ptr_index={}
    for o in relocs:
        v=struct.unpack('<I', d[o:o+4])[0]
        ptr_index.setdefault(v, []).append(o)
    inplace=0; moved=0; newdata=bytearray(); pending=[]
    for off, ko in trans.items():
        off=int(off)
        if off not in strs: continue
        L,orig=strs[off]
        enc=ko.encode('cp949', errors='replace')
        if len(enc)<=L:
            d[off-4:off]=struct.pack('<I', len(enc))
            d[off:off+L+1]=enc+b'\x00'*(L+1-len(enc))
            inplace+=1
        else:
            va=off2va(info, off)
            sites=ptr_index.get(va, [])
            if not sites:
                # 참조를 못 찾으면 잘라서 제자리 삽입
                while len(enc)>L: enc=enc[:-1]
                enc=enc.decode('cp949','ignore').encode('cp949')
                d[off-4:off]=struct.pack('<I', len(enc))
                d[off:off+L+1]=enc+b'\x00'*(L+1-len(enc))
                inplace+=1; continue
            pending.append((off, enc, sites)); moved+=1
    # 새 섹션 구성
    if pending:
        sec_data=bytearray()
        placements=[]
        for off, enc, sites in pending:
            while len(sec_data)%4: sec_data.append(0)
            placements.append((len(sec_data), enc, sites))
            sec_data += b'\xff\xff\xff\xff' + struct.pack('<I', len(enc)) + enc + b'\x00'
        d, info, sec_va, sec_raw = add_section(d, info, '.kotext', bytes(sec_data))
        for rel_off, enc, sites in placements:
            strva = info['base'] + sec_va + rel_off + 8
            for s in sites: d[s:s+4]=struct.pack('<I', strva)
    open(dst,'wb').write(bytes(d))
    print(f'제자리 교체 {inplace} / 재배치 {moved}')
    return inplace, moved

def align(x,a): return (x+a-1)//a*a

def add_section(d, info, name, data):
    salign, falign = info['salign'], info['falign']
    last=max(info['secs'], key=lambda s:s['va'])
    sec_va = align(last['va']+last['vsz'], salign)
    sec_raw = align(len(d), falign)
    d = bytearray(d) + b'\x00'*(sec_raw-len(d))
    raw = bytes(data) + b'\x00'*(align(len(data), falign)-len(data))
    d += raw
    ent = info['sectab'] + info['nsec']*40
    hdr = name.encode('latin1').ljust(8,b'\x00') + struct.pack('<IIII', len(data), sec_va, len(raw), sec_raw) \
          + b'\x00'*12 + struct.pack('<I', 0xC0000040)   # 초기화데이터+읽기+쓰기
    d[ent:ent+40] = hdr
    d[info['pe']+6:info['pe']+8] = struct.pack('<H', info['nsec']+1)
    d[info['sizeimg']:info['sizeimg']+4] = struct.pack('<I', align(sec_va+len(data), salign))
    ni = parse_pe(bytes(d))
    return d, ni, sec_va, sec_raw

if __name__=='__main__':
    src='/mnt/user-data/uploads/Zorbus/Zorbus.exe'
    d=open(src,'rb').read(); info=parse_pe(d)
    rl=reloc_targets(d, info)
    ss=find_strings(d)
    idx={}
    for o in rl:
        v=struct.unpack('<I', d[o:o+4])[0]; idx.setdefault(v,[]).append(o)
    have=sum(1 for p,L,s in ss if off2va(info,p) in idx)
    print(f'문자열 {len(ss)}개 중 .reloc 참조가 있는 것 {have}개 ({have/len(ss)*100:.1f}%)')
