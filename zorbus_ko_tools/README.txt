Zorbus 한글화 작업 도구 모음
============================

[내가 할 일]
- 이 폴더는 참고/재빌드용입니다. 게임을 한글로 하려면 이 폴더가 아니라
  Zorbus_ko_patch.zip 안의 Zorbus.exe / Data/Zorbus.zbs 를 게임 폴더에 덮어쓰세요.
- 직접 돌려보려면: Python 3.11 이상 + numpy 필요.
    pip install numpy
- 원본 파일(Zorbus_EN_original.exe, 원본 Zorbus.zbs)을 같은 폴더에 두고
  아래 명령을 실행하면 패치본이 다시 만들어집니다.
    python3 build_exe.py     -> Zorbus.exe 생성
    python3 apply_zbs2.py    -> Zorbus.zbs 생성


1. 포맷 요약
------------
Zorbus.exe
  Delphi 7~2007 계열 Win32 (비유니코드) VCL 프로그램.
  텍스트 출력은 전부 ANSI GDI(TextOutA / DrawTextA 등) → 인코딩은 CP949 고정.
  문자열은 Delphi AnsiString 상수 형태:
      FF FF FF FF | 길이(4바이트) | 본문 | 00

Zorbus.zbs
  난독화 공식:  파일 = XOR( RLE(원본), PAD )
    - PAD : 1482바이트 고정 패드(값 0~9), PAD[i % 1482]
    - RLE : 같은 바이트가 2번 연속되면 그 뒤 1바이트가 "전체 반복 횟수"
            예) 'r','r',0x02 -> "rr" / 0x00,0x00,0xFF -> 0이 255개
  해제된 내용은 고정 크기 레코드 배열 + 뒤쪽의 \r\n 구분 텍스트 블롭.


2. 파일 설명
------------
zbs_codec2.py   ★ zbs 코덱 v2 — 게임 실제 알고리즘 그대로. 반드시 이걸 쓸 것.
zbs_codec.py    (구) 고정 패드 코덱. 원본과 크기가 같을 때만 맞음 — 사용 금지
zbs_pad.bin     원본 파일에서 복원한 1482바이트 유효키 (v2 유도에 사용)
apply_zbs2.py   ★ 번역 적용 + v2 코덱으로 Zorbus.zbs 생성
zbs_tool.py     zbs 문자열 추출 / 재조립
zbs_map.py      zbs 레코드 배열 오프셋·크기 정의
zorbus_str.py   exe 안의 Delphi 문자열 상수 추출 -> zorbus_strings.csv
exe_patch.py    exe 문자열 치환기 (.reloc 기반 포인터 재배치 포함)
build_exe2.py   ★ Zorbus.exe 생성 (id 기준 + offset 기준 번역 병합 + 우회 패치 자동 적용)
build_exe.py    (구) id 기준 번역만 적용. 사용 금지
apply_zbs.py    tl/*.py + tl/blob/*.json 을 적용해 Zorbus.zbs 생성
batch.py        exe 번역용 배치 덤프
blob_batch.py   블롭 텍스트 번역용 배치 덤프
blob_dedup.py   동일 원문 줄에 기존 번역 자동 적용
crack*.c, solve*.py   패드 복원에 썼던 분석 코드 (기록용)


3. 번역 데이터 (tl/)   ※ 블롭 본문 38,450줄 = 100% 완료
--------------------
tl/it.py              아이템 이름 437개 (CP949 51바이트 이내)
tl/be.py              생물 이름 508개 (CP949 30바이트 이내)
tl/ta.py              재능/마법 이름 126개 (CP949 40바이트 이내)
tl/exe/ko_*.json      exe UI 문자열 번역
tl/exe/skip.json      번역하지 않을 문자열
tl/exe/keep.json      추출된 문자열 목록 (id -> offset)
tl/exe/ko_ext_off.json  ★ offset 기준 추가 번역 (1차 추출 누락분 460개)
tl/exe/ext_ko.py      위 파일을 만드는 원본 (영문 -> 한글 표)
tl/blob/ko_*.json     설명문/책/대사 번역
tl/blob/ko_auto.json  동일 원문에 자동 적용된 번역
tl/blob/ko_keep_en.json  노래 가사 인용 등 원문 유지 줄
tl/blob/src.json      블롭 원문 목록 + 건너뛰기 표시


4. 길이 제한
------------
exe   : 짧으면 제자리 치환, 길면 .kotext 섹션에 추가 후 포인터 재배치.
        → 길이 제한 사실상 없음.
※ zbs_tool.py ARRAYS 주의
   ta 개수 182, mt 개수 104 는 각각 1씩 과다였다. 마지막 항목의 오프셋이
   be 배열의 시작(0x2A9A9A)과 겹쳐서, 재삽입 시 be:0 의 0x48 필드를 0으로
   덮어써 버린다. 181 / 103 이 맞다.

zbs   : 이름 필드는 고정 크기(ShortString)라 위 바이트 상한을 지켜야 함.
        설명/대사 블롭은 길이 자유. 단 "줄 수"는 반드시 보존해야 함.


5. 작업 이어가는 방법
---------------------
  python3 blob_batch.py 18000        # 다음 번역 묶음 뽑기
  (tl/blob/ko_NNNN.py 에 KO = {id: "한글"} 작성 후 json 으로 덤프)
  python3 blob_dedup.py              # 동일 원문 자동 반영
  python3 apply_zbs.py               # Zorbus.zbs 재생성


6. zbs 무결성 검사 (2026-09-09 추가 해독)
-----------------------------------------
파일 구조
    [0:2]        머리 2바이트 (게임이 건너뜀). 원본은 'PK'
    [2:2+L]      XOR( RLE(원본), KEY ),  L = 파일크기 - 2 - 28
    [2+L:6+L]    복호 후 크기 (u32 LE)
    [6+L:+24]    Int64 체크섬 3개 (자릿수 뒤섞기로 암호화 저장)

★ XOR 키는 "파일 길이에 의존"한다 (이것 때문에 첫 패치가 실패했음)
    key_str = str(L) + PREFIX32          # 총 39자
    pad[k]  = int(key_str[38-k])         # 숫자가 아니면 0
      → pad[0:32] 고정,  pad[32:39] = L의 자릿수를 뒤집은 것
    XOR 진행: 짝수 스텝 pad[i] (i = 0,1,2,… 39 순환)
              홀수 스텝 pad[j] (j = 38,37,… 1 → 38 순환)
    유효 주기 = lcm(2,39,38) = 1482  (기존 zbs_pad.bin 이 이 1482바이트)
    PREFIX32 자릿값 = 2,6,2,3,7,8,5,4,3,6,1,6,3,4,6,2,4,8,5,9,7,2,5,8,2,4,3,2,3,1,4,2

체크섬 3종 (exe 0x00B8B30 / 0x00B888C)
    #1  복호 결과에 대한 값 (exe 0x00B891C, 미해독)
    #2  RLE 토큰 순회 합 : 반복 없으면 += 바이트, 반복이면 += 바이트*2 + 횟수
    #3  XOR 해제 전 원시 페이로드 바이트 합
    저장값은 0x00B89F8 로 뒤섞여 있어 그대로 재계산 불가.
    → exe 0x00B888C (파일오프셋 0x0A7C8C) 를 `B0 01 C3` (mov al,1; ret) 로 패치해
      검사를 통과시킴. 되돌리려면 `55 8B EC` 로 복구.


7. 1차 exe 추출 누락 (2026-09-09 수정)
--------------------------------------
zorbus_str.py 의 is_translatable() 필터가 아래를 내부 식별자로 오인해 걸러냈다.
  - 소문자가 하나도 없는 문자열      -> 메인 메뉴(NEW GAME 등) 전부 누락
  - ^[A-Z][A-Za-z0-9_]*$            -> Head, Waist, Equipment, Unencumbered 등 누락
  - ^[a-z][a-z0-9_]*$               -> bites, dodges, you, east 등 전투 로그 단어 누락
전체 Delphi 상수 10,891개 중 keep.json 에 4,297개만 등록되어 있었다.

누락분 중 표시 문자열만 골라내는 기준 (ko_ext_off.json 생성 규칙)
  - 파일 오프셋 0x70000 미만은 제외  (VCL/RTL 영역: Left, Top, Panel, Strings …)
  - '_' '\' '/' 포함, 파일 확장자, Windows API 이름, 폰트명, 월 이름, 키 이름 제외
  - 설정 태그(공백 없는 콤마 나열: darkvision,hide,hiding) 제외
  - 0x21B6C0~0x21B980 = 매크로 이름 표(%he% %boy% …) 제외 — 번역하면 매크로가 깨짐
  - 0x1D2700~0x1D2C60 = 스팀 도전과제 ID 제외
  - 소문자 한 단어는 아래 표시 클러스터 안에 있을 때만 채택
      0x17B900~0x17BBE0  공격 동사   0x17DEE0~0x17E090  명중/회피 동사·대명사
      0x2348F0~0x234A40  장비 칸 설명 0x234AF8~0x234B90  방향
      0x2206E0~0x220A00  You/you     0x165A00~0x165C00  효과 메시지

전투 로그 어순
  템플릿 인자 순서가 (주체, 동사, 대상) 으로 고정이라 한국어 어순과 맞지 않는다.
  동사를 명사형(참격/타격/물기/회피…)으로 번역하고 템플릿을
  "%s의 %s → %s" 형태로 바꿔 "당신의 참격 → 고블린" 으로 읽히게 했다.


8. 화면 제목·구획 헤더가 ???? 로 나오는 문제 (2026-09-09) — 폰트 아님
----------------------------------------------------------------------
★ 진짜 원인: exe 0x0022A024 의 "자간 벌리기" 함수

    result := s;
    n := Length(result);          // AnsiString → 바이트 길이
    while n >= 2 do begin
      Insert(' ', result, n);     // 0x0022A09C = 상수 " "
      dec(n);
    end;

  바이트 사이마다 공백을 끼워 넣는다. 화면 제목과 구획 헤더가 이 함수를 거친다.
  (EMAIL -> "E M A I L". 'E M A I L' 이라는 상수는 exe 어디에도 없다.)
  CP949 한 글자는 2바이트라 한글이 반토막 나고, 각 바이트가 '?' 로 찍힌다.
  → 이 함수를 거치는 문자열은 반드시 ASCII 로 남겨야 한다. 폰트로는 해결 불가.

영향받는 문자열 찾기
  0x0022A024 를 호출하는 E8 rel32 를 전수 조사(78곳)한 뒤, 호출 직전의
  mov eax, imm32 가 가리키는 Delphi 상수를 역추적 → 71개 확정.
  목록은 tl/exe/spaced_headers.json 에 저장. 65개를 영문으로 되돌렸다.
  나머지 3곳은 런타임 조합 문자열이라 상수가 없다
  (그중 하나가 "<이름> - TALENTS" 조합이라 ' - TALENTS' 도 영문 유지).

  주의: 메인 메뉴 항목(0x0957D8~0x0958F4)은 이 함수를 거치지 않는다. 한글 유지.
        같은 'NEW GAME' 이라도 0x07F3D4(새 게임 화면 제목)는 자간 처리 대상이다.

부수적으로 확인한 폰트 항목
Data/Settings.txt 에는 UI에 노출되지 않는 title_font 항목이 따로 있다.
기본값 Georgia / book_font 기본값 Segoe Print 에는 한글 글리프가 없어서
게임 내 책 본문 등은 폰트를 바꿔야 한다.
   title_font............... 맑은 고딕
   book_font................ 맑은 고딕
game_font(기본 Verdana)는 GDI 폰트 링크로 한글이 나오지만, 위 둘은 안 된다.
※ Settings.txt 는 게임 종료 시 덮어써지므로 게임을 끈 상태에서 수정할 것.

9. 전투 동사 표 위치 (0x17B748 ~ 0x17BBE0)
------------------------------------------
  0x17B748~0x17B7C8  2인칭 무기 동사 (attack strike bash smash beat thrust stab slash cut)
  0x17B7D4~0x17B808  "thrust %s at" 류 (무기 인자 포함)
  0x17B814~0x17B8E4  3인칭 무기 동사
  0x17B8EC~0x17B8FC  punch / kick
  0x17B90C~0x17BBD0  자연 공격 2인칭·3인칭 (touch claw slam bite ...)
1차 작업에서 0x17B900 이후만 잡아 attack/attacks 등이 빠졌었다.


10. 3차 추가 번역 (2026-09-09) — 오프셋 기준
--------------------------------------------
아래는 1차 추출 필터에서 "소문자 한 단어"로 걸러졌던 표시용 배열이다.
전부 오프셋으로 직접 지정해 번역했다 (tl/exe/ext_ko.py 의 ADD).

  0x23377C~0x233808  아이템 대분류 (배낭 머리글: wearable shield weapon ...)
  0x233818~0x233B44  아이템 세부 분류 (armor robe helmet ... gem)
                     ※ alarm_horn / lantern_revealing 은 언더바 = 내부 id, 제외
  0x22F870~0x22F990  자연 공격 종류 (kick touch claw ... tongue)
  0x22F9AC~0x22FA70  피해 유형 (blunt pierce slash ... necrotic)
                     ※ 0x22F9A0 'all' 은 필터 키워드일 수 있어 제외
  0x0760C0~0x0762E4  소음/이벤트 라벨 (지도 위 부유 텍스트)
                     death despair animal creature humanoid footsteps movement
                     snore gluttony noise combat door/closed door/forced
                     door/opened enter/teleporter appear/from/teleporter
                     trap/sprung drumming horn grind cooking torture spell
  0x005EE18          '%s: %d = %d - res %d' -> '%s: %d = %d - 저항 %d'

주의: 0x0762F4 이후(githyanki astraloth kuo-toa dagonoth mindflayer squidurak
      slaad toadaloth umberhulk beetlurkh yuan-ti snakeling ...)는 원작 D&D 이름을
      자체 이름으로 바꾸는 치환표다. 번역 금지.

11. 파일 전송 검증 (중요)
-------------------------
device_commit_files 가 "written" 을 반환하고 mtime 도 바뀌는데 실제 내용은
이전 빌드 그대로인 경우가 있었다 (크기가 같을 때). 매번 커밋 후
다시 스테이징해서 md5 로 대조할 것. 파일명을 바꿔 보내면 확실히 반영된다.

12. r5 추가분 (2026-09-09)
------------------------------------------------------------
tl/exe/ext_ko3.py 의 ADD3 (186 오프셋) 을 ko_ext_off.json 에 병합했다.

  - 생물 종류 배열 0x22D22C~0x22D308 (13종)
      * 같은 단어가 zbs 에도 있지만 내부 ID(it_bones_humanoid) 이고
        생물 레코드의 종류 필드는 정수 인덱스라 exe 배열만 번역해도 안전
      * 0x233D84 의 humanoid 는 아이템 플래그 배열이므로 건드리지 말 것
  - 매크로 치환 단어표 0x22F518~0x22F6F8
      포인터 테이블 0x26D798~0x26D83C 가 (중성,남성,여성) 3칸씩 묶는다.
      로그의 "Someone:" = 0x22F614 someone (3칸 모두 동일)
      매크로 '이름' 표(0x21B6C0~0x21B980) 는 절대 번역 금지
  - 소음/상태 라벨 단일 상수들 (yell, snore, creak, kaboom, wham,
    alarm, ouch, gulp, horn, flees, empty, experiment, anchored,
    charmed, confused, diseased, disrupted, poisoned, possessed,
    regeneration, tracked, withered, unlocked, bloodlust ...)
  - 동사 상수 + 템플릿 어순 교정

어순 교정 규칙
  원문 템플릿은 '%s %s ...'(주어,동사) 또는 '%s %s %s.'(주어,동사,목적어).
  (1) be동사/조동사(are is feel seems get gets can have has) 는
      한국어 템플릿에서 그 %s 를 지운다.
      Delphi Format 은 남는 인자를 무시하므로 안전하다.
  (2) 진짜 동사는 한국어 문장 끝에 %s 를 두고 동사 상수를 번역한다.
  (3) 3인자 템플릿은 동사 자리를 '부사'로 바꿔 자연스럽게 만든다.
      (swap->서로, flee->황급히, push->세게, displace->살짝)
  Delphi 의 위치 지정자 '%1:s' 도 이론상 쓸 수 있으나 서식 예외가
  나면 게임이 죽으므로 실기 검증 전에는 쓰지 않는다.

소리 위치 템플릿
  0x19EED4 'You hear %s %s.' -> '%s, %s에서 들린다.'
  0x19EEA4 '%s make noise in' -> '%s이(가) 내는 소리'
  0x232958 -> '무언가가 내는 소리'

빌드 결과: 총 4,077 오프셋 / 제자리 3,136 · 재배치 941
Zorbus.exe 2,813,440 B  md5 3b5bd3e3f6d41f4695901a9b95c3e340


11. 자간 벌리기 함수 CP949 대응 (2026-09-10) — r6
--------------------------------------------------
8번 항목에서 "이 함수를 거치는 문자열은 영문으로 남겨야 한다"고 결론냈던 것을
함수 자체를 고쳐서 해결했다. 헤더 67개를 한글로 되돌렸다.

원본 루프 (VA 0x22A05D ~ 0x22A070, 20바이트)
    while ebx >= 2 do begin Insert(' ', result, ebx); dec(ebx); end;
  → 바이트 사이마다 공백. CP949 2바이트 글자가 반토막 남.

패치 (hook_spacing.py)
  1) 새 실행 섹션 .kohook (characteristics 0x60000020 = CODE|EXECUTE|READ) 추가
  2) 0x22A05D 를 `jmp .kohook` + NOP 15개로 교체
  3) .kohook 56바이트 루프:
       매 반복마다 문자열을 1번 위치부터 앞으로 파싱해
       (바이트 >= 0x81 이면 2칸, 아니면 1칸) 현재 인덱스가
       '글자 경계'일 때만 Insert 를 호출한다.
     - ASCII 는 모든 위치가 경계 → 원본과 동일 ("E M A I L")
     - 한글은 2바이트 단위 경계 → "설 정"
  4) 루프 끝나면 0x22A071 로 복귀

  주의: 파싱은 현재 인덱스보다 앞쪽만 읽는다. 공백은 항상 뒤쪽(큰 인덱스)부터
        삽입하므로 앞쪽 바이트는 원본 그대로다. 그래서 매번 다시 파싱해도 안전하다.

영문으로 남긴 것 (5개)
  ZORBUS(0x7F3C8·0xA65E8·0x256CAC 상당) — 게임 제목
  ASCII, STEAM — 고유명사

폰트 (필수)
  헤더는 title_font 로 그린다. 기본값 Georgia 에는 한글 글리프가 없다.
  Data/Settings.txt 에서 title_font / book_font 를 '맑은 고딕' 으로 바꿔야 한다.
  (게임 종료 시 덮어써지므로 게임을 끈 상태에서 수정할 것)


12. 조사 자동 선택 훅 (2026-09-10) — r9
----------------------------------------
번역문에 조사를 "이(가)" "을(를)" "은(는)" "와(과)" "로(으로)" 형태로 그대로 써 둔다.
실행 시점에 앞 글자 받침을 보고 하나로 줄여 준다.

훅 위치: SysUtils.Format 래퍼(VA 0x19894)의 꼬리
  0x198A3 의 `pop ebp / ret 4 / nop`(5바이트)를 `jmp .kohook` 으로 교체.
  훅은 [ebp+8](@Result)이 가리키는 힙 문자열을 제자리에서 줄이고
  길이 필드([p-4])를 새로 쓴 뒤 원래대로 `pop ebp / ret 4`.

받침표: .kohook 안에 65536바이트. 인덱스 = (앞글자 CP949 lead<<8)|trail
  값 0 = 받침 없음 / 1 = 받침 있음(ㄹ 제외) / 2 = ㄹ 받침
  0x00~0xFF 구간은 ASCII 용 (숫자 0 1 3 6 7 8 = 받침 있음)

  "로(으로)" 만 ㄹ받침을 따로 본다: 값 1 이면 "으로", 0 또는 2 면 "로".

주의
  - 문자열이 항상 짧아지므로 재할당이 필요 없다. 길이 필드만 줄이면 된다.
  - Format 을 거치지 않는 문자열(zbs 블롭의 %target% 매크로 대사 29곳)은
    적용되지 않는다. 그쪽은 조사 표시를 쓰지 말 것.
  - "치(현재)" 처럼 정상적인 괄호 표기는 6바이트 완전일치가 아니라 안전하다.

위치 지정자
  Delphi Format 의 %0:s 는 이 exe 에서 지원된다 (FormatBuf VA 0x19496 에
  `cmp al,0x3A` 로 인덱스 파싱 확인). 전투 로그 C 템플릿에서 중복 대명사를
  건너뛰는 데 썼다.

전투 로그 인자 구조 (VA 0x18E200~0x18E960 에서 확인)
  [ebp-0x1c] 주체    [ebp-0x2c] 공격 동사   [ebp-0x30] 대상 이름
  [ebp-0x20] hit     [ebp-0x28] destroy/kill
  [ebp-0x38] 대상 대명사   [ebp-0x3c] dodge/parry/block
  템플릿 4종은 모두 "%s의 %s → %s: %s!" 꼴로 통일했다.


13. 추출기가 놓친 문자열 (2026-09-10)
--------------------------------------
zorbus_str.extract 는 32~126 + \t\r\n 이외 바이트가 있으면 문자열을 버린다.
스마트 따옴표(0x94)가 든 상수 1개(0xF906C, 동료 전술 도움말 307바이트)가
여기 걸려 영문으로 남아 있었다. CP949 에서 0x94 가 선행 바이트로 해석되어
"봇?" 같은 글자로 보인다. tl/exe/ko_raw.json 에 오프셋 기준으로 넣어
build_exe2.py 가 제자리 패치한다 (원본 길이 이하만 가능).


14. 줄바꿈 규칙 (중요)
----------------------
게임 문자열의 줄바꿈은 CRLF(\r\n) 다. LF 하나만 있으면 줄이 바뀌지 않고
글자로 그려진다(네모/특수문자). 번역 데이터에서 CR 이 빠져 있던 151곳을
r7 에서 되돌렸다. 새로 번역할 때도 반드시 \r\n 을 쓸 것.
단, 원문이 리터럴 "\n"(백슬래시+n)인 74곳은 그대로 리터럴을 유지한다.


15. 서식 지정자 검증 (2026-09-10) — 필수
-----------------------------------------
번역문의 %d / %s 순서를 원문과 다르게 쓰면 게임이 죽는다.
  "Format '%s' invalid or incompatible with argument."

실제 사고: ' + %d per %s'  ->  ' + %s당 %d'  로 뒤집어 써서
조르버피디아를 열 때마다 예외가 났다(화면도 빈 채로 뜬다).

순서를 바꾸려면 반드시 위치 지정자를 쓸 것.
  ' + %d per %s'  ->  ' + %1:s당 %0:d'      (인덱스는 0부터)

build_exe2.py 가 빌드 전에 check_fmt.py 로 전수 검증하고,
불일치가 있으면 빌드를 중단한다. 수동 확인은
  python3 check_fmt.py


16. 전투 로그의 무기 표기
--------------------------
대상 문자열은 코드에서 이렇게 만들어진다 (VA 0x18E648, 0x18E674).
  [ebp-0x44] = ' with ' + 무기이름
  [ebp-0x30] = 'you'/대상이름 + [ebp-0x44]
즉 무기가 **대상 문자열 뒤에 붙는다**. 템플릿에서 떼어낼 수 없다.

' with '(0x17DFFC) 를 ' ' 로 뒀더니 "당신 창" 처럼 보여서 뜻이 모호했다.
' · 무기 ' 로 바꿔 "당신 · 무기 창" 으로 명시한다.

이 구조 때문에 전투 로그를 완전한 문장("해골이 당신을 공격해...")으로
만들 수 없다. 대상 뒤에 무기가 붙어 조사가 무기에 걸리기 때문이다.
그래서 화살표 로그 형식("A의 V → T: R!")을 유지한다.


17. 어떤 영문 배열을 번역해도 되는가 (2026-09-10)
--------------------------------------------------
exe 안의 소문자 단어 배열은 두 종류가 섞여 있다.

  (A) 표시용 열거형 이름표  -> 번역해도 된다
      - .reloc 참조가 **정확히 1곳**
      - 그 참조가 DATA 영역의 **연속된 포인터 표** 안에 있다
        (앞뒤 4바이트도 reloc 대상)
      - 배열 안 항목이 전부 밑줄 없는 단어
      예) 종족표 0x22D3A8~, 능력치/기술 0x2234AC~, 특기 분류 0x232328~

  (B) 내부 태그/플래그 이름  -> 건드리지 말 것
      같은 배열 안에 밑줄 든 항목이 섞여 있으면 내부용이다.
      예) 0x233C54 아이템 속성 (two_handed, armor_light, potion_body …)
          0x230DCC 상태      (caught_in_web, immunity_critical_hits …)
          0x22D1DC 피해/연출 (an_fireball, an_charm … 뒤에 lightning/holy)

판별 스크립트 예시는 이 문서 아래 15번의 check_fmt.py 와 같은 방식으로
exe_patch.reloc_targets 를 써서 참조 수를 세면 된다.

r12 에서 (A) 기준으로 조르버피디아 관련 31개를 번역했다.
  능력치  body motion mind spirit health stamina
  기술    disable dodge magic melee ranged search stealth
  저항    combat spell trap poison throne well
  특기분류 boost(s) utility combat spell(s) monster(s) automatic activated


18. 조르버피디아 본문 조회 키 (2026-09-10) — 함정
--------------------------------------------------
조르버피디아 본문은 zbs 블롭의 이름표에서 "<이름>_info" 로 찾는다.
그 <이름> 이 바로 exe 열거형 배열(0x2234AC 능력치/기술)의 문자열이다.

  exe 가 만드는 키 :  'body'(0x2234AC) + '_info'  ->  'body_info'
  zbs 이름표 라인   :  blob:45803  'body_info'

즉 exe 쪽 이름만 번역하면 키가 '육체_info' 가 되어 조회에 실패하고
**본문이 통째로 빈 화면**이 된다 (17번 기준으로는 걸러지지 않는다).

해결: zbs 쪽 키도 같이 바꿔 준다. tl/blob/ko_keys.json
  blob:45788 health_info -> 생명력_info   blob:45803 body_info    -> 육체_info
  blob:45789 stamina_info-> 기력_info     blob:45804 motion_info  -> 운동_info
  blob:45809 disable_info-> 해제_info     blob:45805 mind_info    -> 정신_info
  blob:45810 dodge_info  -> 회피_info     blob:45806 spirit_info  -> 영혼_info
  blob:45811 magic_info  -> 마법_info     blob:45812 melee_info   -> 근접_info
  blob:45813 ranged_info -> 원거리_info   blob:45814 search_info  -> 탐색_info
  blob:45815 stealth_info-> 은신_info

각 키는 블롭 전체에서 정확히 1회만 나온다(상호 참조 없음)을 확인하고 바꿨다.
'_info' 는 exe 안에 상수로만 있고 'body_info' 같은 완성된 키 상수는 없다.

★ 새 열거형을 번역하기 전에 반드시 확인할 것:
   zbs 블롭에 "<그 이름>_info" 라인이 있는가?
   있으면 zbs 키도 함께 바꿔야 한다.
   (저항 combat/spell/trap…, 특기분류 boost/utility… 는 _info 키가 없어서 안전)


19. 난독화된 문자열 — 원형 캐릭터 이름 (2026-09-10)
----------------------------------------------------
exe 0x7D1B8~0x7D21C 의 Delphi 상수는 **뒤집기 + 바이트별 XOR 1** 로
난독화돼 있다. 그래서 'Archer' 로는 검색해도 안 나온다.

  저장형태 = reverse( plain bytes XOR 0x01 )
  예) 'Warrior' -> XOR1 'V`sshns' -> reverse 'snhss`V'

원형 캐릭터 7개
  0x7D1B8 Archer(6)   -> 궁수      0x7D1EC Leader(6)  -> 지휘관
  0x7D1C8 Bully(5)    -> 깡패      0x7D1FC Noble(5)   -> 귀족
  0x7D1D8 Infernal(8) -> 마계인    0x7D20C Warrior(7) -> 전사
  0x7D21C Wizard(6)   -> 마법사

같은 방식으로 난독화된 이웃 문자열(0x7D22C 이후)은
be_playable_* / ta_* 내부 ID 다. **번역하면 안 된다.**

번역표: tl/exe/ko_enc.json (오프셋 기준)
build_exe2.py 가 CP949 인코딩 -> XOR1 -> 뒤집기 순으로 제자리 패치한다.
길이는 원본 이하만 가능(재배치 불가). 전부 원본보다 짧아서 문제없다.

CP949 바이트는 lead >= 0x81, trail >= 0x41 이라 XOR 1 이 0x00 을 만들지 않는다.


20. 전투 로그 — 무기를 공격자 쪽으로 옮기는 훅 (2026-09-10)
------------------------------------------------------------
원본은 무기 이름을 **대상 문자열**에 붙인다 (16번 참조).
  [ebp-0x44] = ' with ' + 무기
  [ebp-0x30] = 대상 + [ebp-0x44]      ->  "당신 · 무기 망치"
공격자의 무기가 대상 옆에 찍혀서 누구 무기인지 헷갈린다.

VA 0x18E648 의 16바이트(구분자+무기 조립)를 .kohook 으로 돌려서
공격자 쪽에 붙이고 대상 쪽은 비운다.

  lea eax,[ebp-0x44] / mov ecx,[ebp-0x44] / mov edx,<구분자> / call LStrCat3
      -> [ebp-0x44] = 구분자 + 무기
  lea eax,[ebp-0x1c] / mov ecx,[ebp-0x44] / mov edx,[ebp-0x1c] / call LStrCat3
      -> 공격자 += 구분자 + 무기
  lea eax,[ebp-0x44] / call LStrClr      -> 무기 문자열 비움
  jmp 0x18E658

  LStrCat3 = 0x13FB8 (dest=eax, s1=edx, s2=ecx -> dest = s1+s2)
  LStrClr  = 0x13CEC

구분자 상수는 원래 ' with '(0x17DFFC / VA 0x18EBFC). ' · ' 로 번역했다.
번역이 원본보다 길면 재배치되므로, 훅은 exe 안의 실제 `mov edx,imm32`
값을 읽어서 쓴다 (하드코딩 금지).

결과
  전:  풋내기 모험가의 공격 → 당신 · 무기 망치: 처치!
  후:  풋내기 모험가 · 망치의 공격 → 당신: 처치!


21. 축약 라벨 (2026-09-10) — r14
---------------------------------
아이템 정보 문자열이 화면 폭을 넘으면 긴 단어를 짧은 단어로 치환한다.
  VA 0x229A34 = replace(S=eax, Old=edx, New=ecx)
  조건: `call LStrLen; cmp esi,eax; jge skip`  (esi = 허용 폭)
  즉 폭을 넘을 때만 치환. 단계가 2단인 것도 있다 (Vampiric -> Vamp -> Va).

Old 는 이미 한글로 번역된 긴 형태, New 가 영문 축약형으로 남아 있었다.
그래서 문자열이 길어지면 한글이 다시 영문 축약으로 바뀌어 버렸다.

| 축약 오프셋 | 원문 | 긴 형태(번역) | 축약 번역 |
|---|---|---|---|
| 0x1E2920 | Track | Tracking 추적 중 | 추적 (r5에 이미) |
| 0x1E2930 | Anch  | Anchoring 차원 고정 | 고정 |
| 0x1E2940 | With  | Withering 쇠약화 | 쇠약 |
| 0x1E2950 | Ext   | Extinguishing 꺼짐 | 꺼짐 |
| 0x1E2964 | Ret   | Returning 귀환 | 귀환 |
| 0x1E2984 | Vamp  | Vampiric 흡혈 | 흡혈 |
| 0x1E29A8 | Unh   | Unholy 부정 | 부정 |
| 0x1E29C4 | Poi   | Poison 독 | 독 |
| 0x1E29D0 | Light | Lightning 번개 | 번개 (빛 -> 번개 교정) |
| 0x1E29F4 | Va    | (Vamp 흡혈) | 흡혈 |
| 0x1E2A00 | Sli   | Slime 점액 | 점액 |
| 0x1E2A0C | Imp   | Impact 충격 | 충격 |

한글은 이미 짧아서 대부분 치환이 무의미(no-op)해진다. 그래도 영문이
튀어나오지 않으므로 이게 맞다. 원본보다 길어지는 것은 exe_patch 가 재배치한다.

주의: 0x1E27A0~ 의 소문자 poison/slime/tracking/... 은 비교용(0x14258)이다.
**번역하면 안 된다.**


22. 매크로 대사의 조사 (2026-09-10) — r14
------------------------------------------
`%target%` 같은 매크로는 Format 을 안 거치므로 조사 훅(12번)이 안 먹는다.
매크로 바로 뒤에 오는 조사 표시 27줄을 문장 구조를 바꿔 해결했다.

| 전 | 후 |
|---|---|
| `%target%이(가) 새로운 초신이다!` | `%target%, 새로운 초신이다!` |
| `%target%이(가) 강력한 보호 마법에 감싸인다!` | `%target% 주위를 강력한 보호 마법이 감싼다!` |
| `%killed_god%을(를)` | `%killed_god% 님을` |
| `%killed_god%이(가)` | `%killed_god% 님이` |
| `%player_him%을(를)` | `%player_him%를` |
| `%him%을(를)` | `%him% 따위를` |

`%player_him%` `%player_he%` 는 플레이어 전용이라 항상 그/그녀 → 받침 없음.
그래서 를/는/가 로 고정해도 안전하다.
`%him%` 은 중성 생물이면 '그것'(받침 있음)이 될 수 있어 `따위를` 로 우회했다.

검사: 매크로 바로 뒤 조사 표시 = 0줄 (아래로 확인)
  정규식  (이\(가\)|을\(를\)|은\(는\)|와\(과\)|로\(으로\))  앞이  %[A-Za-z_]+%$
