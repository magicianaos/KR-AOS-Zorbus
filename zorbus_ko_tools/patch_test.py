import struct, shutil, sys

SRC = '/mnt/user-data/uploads/Zorbus/Zorbus.exe'
DST = '/mnt/user-data/outputs/Zorbus.exe'

# (파일오프셋, 원본길이, 한글번역)
PATCHES = [
    (0x9c060, 42, "조사/조준 모드에서 커서 중앙 정렬"),
    (0x9c200, 19, "장식 색상 영역"),
    (0x9c27c, 13, "바닥 기호"),
    (0x9c2d0, 31, "장식용 혈흔, 점액, 뼈"),
    (0x9c34c, 19, "밝은 암시야"),
    (0x9c420, 20, "가구 애니메이션"),
    (0x9c82c, 11, "글꼴 크기"),
    (0x9ca2c, 17, "줄 높이 비율"),
    (0x25464c, 9, "본문 글꼴"),
    (0x254660, 9, "책 글꼴"),
]

d = bytearray(open(SRC,'rb').read())
for off, oldlen, ko in PATCHES:
    b = ko.encode('cp949')
    assert len(b) <= oldlen, f"너무 김: {ko} {len(b)}>{oldlen}"
    # 원본 길이 필드 검증
    cur = struct.unpack('<I', d[off-4:off])[0]
    assert cur == oldlen and d[off-8:off-4]==b'\xff\xff\xff\xff', f"헤더 불일치 @{hex(off)}"
    # 본문 영역 초기화 후 새 문자열 + NUL
    d[off:off+oldlen+1] = b'\x00'*(oldlen+1)
    d[off:off+len(b)] = b
    # 길이 필드 갱신
    d[off-4:off] = struct.pack('<I', len(b))
    print(f"  {hex(off)}  {oldlen:3d} -> {len(b):3d}  {ko}")

open(DST,'wb').write(bytes(d))
print("\n출력:", DST, len(d), "bytes")
