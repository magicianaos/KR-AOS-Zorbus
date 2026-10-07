#!/usr/bin/env python3
"""Zorbus.zbs 코덱

포맷 (2026-09-09 해독 완료)
  파일 = XOR( RLE(원본데이터), PAD )
  - PAD : 1482바이트 고정 패드, 각 바이트 값 0~9. 파일 오프셋 i에 대해 PAD[i % 1482]
  - RLE : 같은 바이트가 2번 연속하면 그 다음 1바이트가 "전체 반복 횟수"
          예) 'r','r',0x02 -> "rr"   /   0x00,0x00,0xFF -> 0x00 * 255
  - 문자열 : [길이(1바이트, 긴 것은 2바이트 LE)] + 본문 + 0x00
"""
import numpy as np, os

PAD_PATH = os.path.join(os.path.dirname(__file__), 'zbs_pad.bin')
P = 1482

def load_pad():
    return np.frombuffer(open(PAD_PATH,'rb').read(), dtype=np.uint8)

def unxor(data: bytes) -> bytes:
    a = np.frombuffer(data, dtype=np.uint8)
    pad = load_pad()
    return (a ^ pad[np.arange(len(a)) % P]).tobytes()

doxor = unxor          # XOR은 대칭

def rle_decode(b: bytes) -> bytes:
    out = bytearray(); i = 0; n = len(b)
    while i < n:
        c = b[i]; out.append(c); i += 1
        if i < n and b[i] == c:
            out.append(c); i += 1
            if i < n:
                cnt = b[i]; i += 1
                if cnt > 2: out.extend(bytes([c]) * (cnt - 2))
    return bytes(out)

def rle_encode(b: bytes) -> bytes:
    out = bytearray(); i = 0; n = len(b)
    while i < n:
        c = b[i]; run = 1
        while i + run < n and b[i+run] == c and run < 255: run += 1
        if run == 1:
            out.append(c); i += 1
        else:
            out += bytes([c, c, run]); i += run
    return bytes(out)

def decode_file(path: str) -> bytes:
    return rle_decode(unxor(open(path,'rb').read()))

def encode_file(plain: bytes) -> bytes:
    return doxor(rle_encode(plain))

if __name__ == '__main__':
    import sys
    src = sys.argv[1] if len(sys.argv)>1 else '/mnt/user-data/uploads/Zorbus/Data/Zorbus.zbs'
    raw = open(src,'rb').read()
    plain = rle_decode(unxor(raw))
    # 왕복 검증
    back = doxor(rle_encode(plain))
    print(f'복호 {len(raw):,} -> {len(plain):,} bytes')
    print('왕복 무결성:', 'OK' if back == raw else f'불일치 ({sum(a!=b for a,b in zip(back,raw))} bytes)')
