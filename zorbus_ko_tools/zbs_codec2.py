#!/usr/bin/env python3
"""Zorbus.zbs 코덱 v2 — 게임 실제 알고리즘 그대로 (exe 역분석 2026-09-09)

파일 구조
    [0:2]        스킵되는 머리 2바이트
    [2:2+L]      XOR( RLE(원본), KEY )      L = filesize - 2 - 28
    [2+L:6+L]    복호 후 크기 (u32 LE)
    [6+L:6+L+24] 3개의 Int64 체크섬 (암호화 저장)

KEY 생성 (게임 로직)
    key_str = str(L) + PREFIX32          # 길이 39
    pad[k]  = int(key_str[38-k])         # 문자→숫자, 숫자 아니면 0
    → pad[0:32] 는 고정, pad[32:39] 는 L의 자릿수(역순)
    XOR 순서: 짝수 스텝은 pad[i](i=0,1,2,… 순환 39),
              홀수 스텝은 pad[j](j=38,37,…,1 순환 38)
    ⇒ 유효 주기 lcm(2,39,38) = 1482
"""
import numpy as np

N = 39
PREFIX_DIGITS = [2,6,2,3,7,8,5,4,3,6,1,6,3,4,6,2,4,8,5,9,7,2,5,8,2,4,3,2,3,1,4,2]
HEAD = 2
TRAILER = 28          # 4바이트 크기 + 24바이트 체크섬

def make_pad(payload_len: int):
    s = str(payload_len)
    if len(s) + len(PREFIX_DIGITS) != N:
        raise ValueError(f'길이 자릿수 {len(s)} — 39자 가정이 깨짐')
    pad = list(PREFIX_DIGITS)          # pad[0:32]
    pad += [int(s[6-t]) for t in range(7)]   # pad[32:39] = 자릿수 역순
    return pad

def keystream(payload_len: int):
    """유효 XOR 키 1482바이트 (payload 길이에 의존)"""
    pad = make_pad(payload_len)
    out = np.empty(1482, dtype=np.uint8)
    i, j, flag = 0, N-1, 0
    for k in range(1482):
        flag ^= 1
        out[k] = pad[i] if flag else pad[j]
        i += 1
        if i == N: i = 0
        j -= 1
        if j == 0: j = N-1
    return out

def _xor(buf: bytes, payload_len: int) -> bytes:
    a = np.frombuffer(buf, dtype=np.uint8)
    ks = keystream(payload_len)
    return (a ^ ks[np.arange(len(a)) % 1482]).tobytes()

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

def unpack(raw: bytes):
    """→ (head2, plain, declen, checksums24)"""
    L = len(raw) - HEAD - TRAILER
    payload = _xor(raw[HEAD:HEAD+L], L)
    declen = int.from_bytes(raw[HEAD+L:HEAD+L+4], 'little')
    return raw[:HEAD], rle_decode(payload), declen, raw[HEAD+L+4:]

def pack(head2: bytes, plain: bytes, checksums24: bytes) -> bytes:
    payload = rle_encode(plain)
    L = len(payload)
    return (head2 + _xor(payload, L)
            + len(plain).to_bytes(4, 'little') + checksums24)
