# 소리결(SoriGyeol) 데이터 받기

> 팀원용 · Windows + WSL(Ubuntu) + VS Code 기준
> 한국 데이터(AI Hub) 1개 + 해외 데이터 3개를 메인 환경과 **똑같은 위치·구조**로 받는 방법이에요.

각 단계의 **✅ 확인** 결과가 같게 나오면 성공이에요.

| 데이터 | 출처 | 받는 방법 | 용량 | 시간 |
|---|---|---|---|---|
| UrbanSound8K | 해외 | 명령어 | 6GB | **몇 시간** (서버가 느림) |
| AI Hub 도시 소리 | 한국 | 웹 신청 → 다운로드 | 약 26GB | 인터넷 속도에 따라 |
| ESC-50 | 해외 | 명령어 | 600MB | 몇 분 |
| FSD50K 라벨 | 해외 | 명령어 | 335KB | 몇 초 |

> UrbanSound8K가 제일 오래 걸려서 **가장 먼저 걸어두고**, 기다리는 동안 나머지를 받아요.

---

## 0. 준비

```bash
cd ~/ai_vision/SoriGyeol
source .venv/bin/activate
git pull
mkdir -p data/raw
```

`unzip`이 없으면 먼저 설치하세요.

```bash
sudo apt install unzip
```

**저장 공간**: 압축 해제 중에는 잠깐 두 배가 필요해서, Windows **C 드라이브에 60GB 이상** 여유가 있는지 확인하세요.

---

## 1. UrbanSound8K 다운로드 시작 (6GB, 몇 시간)

VS Code 터미널 오른쪽 위 **`+` 버튼으로 새 터미널**을 열어서 실행하고, **그대로 켜두세요.**

```bash
cd ~/ai_vision/SoriGyeol
mkdir -p data/raw/urbansound8k && cd data/raw/urbansound8k
wget -c "https://zenodo.org/records/1203745/files/UrbanSound8K.tar.gz?download=1" -O UrbanSound8K.tar.gz
```

> 중간에 끊기거나 VS Code를 껐다면, 같은 폴더에서 **위의 `wget` 줄을 다시 실행**하면 받던 데서 이어서 받아요.
> 압축 해제는 다운로드가 끝난 뒤 **5단계**에서 해요.

이제 **원래 터미널**로 돌아가서 다음 단계를 진행하세요.

---

## 2. AI Hub 도시 소리 데이터 (한국, 약 26GB)

> ⚠️ AI Hub 이용정책상 데이터를 다른 사람에게 복사해서 넘길 수 없어요. **각자 직접 신청**해야 해요.

### 2-1. 회원가입 · 신청

1. [aihub.or.kr](https://aihub.or.kr) **회원가입** (휴대폰 본인인증 필요, 내국인만 신청 가능)
2. 아래 주소로 **"도시 소리 데이터"** 페이지 접속
   ```
   https://aihub.or.kr/aihubdata/data/view.do?dataSetSn=585
   ```
   - 맞는 페이지인지 확인: 분야 **재난안전환경** · 유형 **오디오** · 구축년도 **2021**
   - 이름이 비슷한 "소음 환경 음성인식 데이터", "극한 소음 음성인식 데이터"는 다른 데이터예요
3. **다운로드** 버튼 → 이용 목적 입력 (예: `소리 분류 모델 학습 (팀 포트폴리오 프로젝트)`) → **자동 승인**

### 2-2. 8개 파일만 선택해서 다운로드

다운로드 창(**AI 학습용 다운로드**)이 열리면 폴더를 펼쳐서 **아래 8개만** 체크하세요.
처음이면 다운로드 프로그램(INNORIX) 설치를 물어볼 수 있어요. 설치하면 돼요.

| 폴더 | 파일 | 체크 | 용량 |
|---|---|---|---|
| `1.Training / 라벨링데이터` | TL_1.교통소음.zip | ✅ | 25MB |
| | TL_2.생활소음.zip | ✅ | 19MB |
| | TL_3.사업장소음.zip | ✅ | 16MB |
| `1.Training / 원천데이터` | **TS_1.교통소음.zip** | ✅ | **23GB** |
| | TS_2.생활소음.zip | ⬜ 받지 않음 | 35GB |
| | TS_3.사업장소음.zip | ⬜ 받지 않음 | 49GB |
| `2.Validation / 라벨링데이터` | VL_1.교통소음.zip | ✅ | 3MB |
| | VL_2.생활소음.zip | ✅ | 2MB |
| | VL_3.사업장소음.zip | ✅ | 993KB |
| `2.Validation / 원천데이터` | **VS_1.교통소음.zip** | ✅ | **3GB** |
| | VS_2.생활소음.zip | ⬜ 받지 않음 | 3GB |
| | VS_3.사업장소음.zip | ⬜ 받지 않음 | 3GB |

체크한 뒤 **[선택 다운로드]** 클릭. Windows **다운로드 폴더**에 `130.도시 소리 데이터` 폴더가 생기고, 그 안에 zip 파일들이 들어 있어요.

> 라벨링데이터(설명서 JSON)는 3종 모두, 원천데이터(소리 파일)는 **교통소음만** 받는 거예요.

### 2-3. WSL 프로젝트 폴더로 옮기기

1. 터미널에서 내 WSL 홈 경로를 확인해요.
   ```bash
   echo $HOME
   ```
   `/home/사용자이름` 형태로 나와요.

2. Windows **파일 탐색기 주소창**에 아래를 붙여넣어요. (`사용자이름`은 위에서 확인한 이름으로 바꾸기)
   ```
   \\wsl.localhost\Ubuntu\home\사용자이름\ai_vision\SoriGyeol\data\raw
   ```

3. 여기에 **`aihub_urban_sound`** 폴더를 새로 만들어요.

4. 다운로드 폴더의 **`130.도시 소리 데이터` 폴더를 통째로** `aihub_urban_sound` 안에 끌어다 넣어요. (26GB라 몇 분 걸려요)

> ⚠️ 폴더 이름과 안쪽 구조는 **절대 바꾸지 마세요.** 모든 팀원이 같은 구조여야 같은 코드가 동작해요.

```
data/raw/aihub_urban_sound/
└── 130.도시 소리 데이터/
    └── 01.데이터/
        ├── 1.Training/
        │   ├── 라벨링데이터/   TL_1~3 zip
        │   └── 원천데이터/     TS_1 zip
        └── 2.Validation/
            ├── 라벨링데이터/   VL_1~3 zip
            └── 원천데이터/     VS_1 zip
```

### 2-4. 압축 풀기

AI Hub zip은 파일 이름이 윈도우 한글(CP949)로 저장돼 있어서, 그냥 `unzip`으로 풀면 이름이 깨져요.
레포에 있는 스크립트로 풀어요. (TS_1이 커서 몇 분 걸려요)

```bash
cd ~/ai_vision/SoriGyeol
source .venv/bin/activate
python src/unzip_aihub.py data/raw/aihub_urban_sound
```

> 중간에 끊겨도 **같은 명령을 다시 실행**하면 다 풀린 건 건너뛰고 이어서 해요.

### 2-5. 확인

```bash
find data/raw/aihub_urban_sound -maxdepth 6 -type d | head -20
find data/raw/aihub_urban_sound -name "*.wav" | wc -l
find data/raw/aihub_urban_sound -name "*.json" | wc -l
```

✅ 확인
- 폴더 이름이 `1.자동차`, `2.이륜자동차`처럼 **한글로 정상** 표시
- wav **28643**
- json **67793**

소분류별 개수도 확인해요.

```bash
find data/raw/aihub_urban_sound -path "*원천데이터*" -name "*.wav" \
  | awk -F/ '{print $(NF-2)" / "$(NF-1)}' | sort | uniq -c
```

✅ 아래와 같으면 성공

```
3588 1.자동차 / 1.차량경적
2239 1.자동차 / 2.차량사이렌
1909 1.자동차 / 3.차량주행음
5079 2.이륜자동차 / 4.이륜차경적
5233 2.이륜자동차 / 5.이륜차주행음
1952 3.항공기 / 6.비행기
3660 3.항공기 / 7.헬리콥터
2366 4.열차 / 8.기차
2617 4.열차 / 9.지하철
```

### 2-6. zip 파일 정리

확인이 끝나면 zip을 지워서 공간을 확보해요. (다시 풀지 않고 zip만 지워요)

```bash
python src/unzip_aihub.py data/raw/aihub_urban_sound --delete
```

Windows **다운로드 폴더에 남은 `130.도시 소리 데이터` 원본도 삭제**하세요.

---

## 3. ESC-50 (해외, 600MB, 몇 분)

```bash
cd ~/ai_vision/SoriGyeol
mkdir -p data/raw/esc50 && cd data/raw/esc50
wget https://github.com/karolpiczak/ESC-50/archive/refs/heads/master.zip -O esc50.zip
unzip -q esc50.zip && rm esc50.zip
ls ESC-50-master/audio | wc -l
cd ~/ai_vision/SoriGyeol
```

✅ 마지막 숫자가 **2000**이면 성공

---

## 4. FSD50K 라벨 (해외, 335KB, 몇 초)

소리 파일은 받지 않고, 클래스 목록과 라벨 파일만 받아요.

```bash
cd ~/ai_vision/SoriGyeol
mkdir -p data/raw/fsd50k && cd data/raw/fsd50k
wget -c "https://zenodo.org/records/4060432/files/FSD50K.ground_truth.zip?download=1" -O FSD50K.ground_truth.zip
unzip -q FSD50K.ground_truth.zip && rm FSD50K.ground_truth.zip
ls FSD50K.ground_truth
cd ~/ai_vision/SoriGyeol
```

✅ `dev.csv  eval.csv  vocabulary.csv`가 보이면 성공

---

## 5. UrbanSound8K 압축 풀기 (1단계 다운로드가 끝난 뒤)

```bash
cd ~/ai_vision/SoriGyeol/data/raw/urbansound8k
tar -xzf UrbanSound8K.tar.gz
find UrbanSound8K/audio -name "*.wav" | wc -l
```

✅ 숫자가 **8732**면 성공. 압축 파일을 지우세요.

```bash
rm UrbanSound8K.tar.gz
cd ~/ai_vision/SoriGyeol
```

---

## 6. 최종 확인

```bash
cd ~/ai_vision/SoriGyeol
echo "AI Hub wav    : $(find data/raw/aihub_urban_sound -name '*.wav' | wc -l)  (정답 28643)"
echo "AI Hub json   : $(find data/raw/aihub_urban_sound -name '*.json' | wc -l)  (정답 67793)"
echo "ESC-50        : $(ls data/raw/esc50/ESC-50-master/audio | wc -l)  (정답 2000)"
echo "UrbanSound8K  : $(find data/raw/urbansound8k/UrbanSound8K/audio -name '*.wav' | wc -l)  (정답 8732)"
echo "FSD50K 라벨   : $(ls data/raw/fsd50k/FSD50K.ground_truth | wc -l)  (정답 3)"
echo "남은 zip/tar  : $(find data/raw \( -name '*.zip' -o -name '*.tar.gz' \) | wc -l)  (정답 0)"
```

모든 숫자가 정답과 같으면 데이터 준비 끝! 🎉

**최종 폴더 구조**

```
data/raw/
├── aihub_urban_sound/130.도시 소리 데이터/01.데이터/...
├── esc50/ESC-50-master/
├── fsd50k/FSD50K.ground_truth/
└── urbansound8k/UrbanSound8K/
```

- `data/` 폴더는 `.gitignore`에 등록돼 있어서 GitHub에 올라가지 않아요. **커밋할 필요 없어요.**
- 폴더 이름과 위치를 **위와 똑같이** 맞춰야 나중에 같은 코드가 그대로 동작해요.

---

## 자주 나오는 문제

| 증상 | 해결 |
|---|---|
| `unzip: command not found` | `sudo apt install unzip` 후 해당 단계 다시 실행 |
| `No module named 'tqdm'` 등 (2-4단계) | 가상환경이 꺼져 있음 → `source .venv/bin/activate` 후 다시 실행 |
| AI Hub 폴더 이름이 `└┌╡┐`처럼 깨짐 | `unzip`으로 직접 푼 경우 → 풀린 폴더를 지우고 `src/unzip_aihub.py`로 다시 풀기 |
| AI Hub wav 개수가 28643이 아님 | 원천데이터를 TS_1·VS_1 외에 더 받았거나 덜 받음 → 2-2단계 체크 목록 확인 |
| 탐색기에서 `\\wsl.localhost\...` 주소가 안 열림 | `\\wsl$\Ubuntu\home\사용자이름\...`으로 시도 |
| UrbanSound8K가 너무 느림 | 정상이에요 (Zenodo 서버가 느림). 켜두고 다른 작업 |
| 다운로드가 중간에 끊김 | 같은 폴더에서 `wget -c ...` 줄을 다시 실행 → 이어받기 |

---

## 이용 조건 (꼭 지켜야 해요)

| 데이터 | 조건 |
|---|---|
| AI Hub 도시 소리 | **다른 사람에게 복사·전달 금지** (각자 신청) · 이용 시 **"한국지능정보사회진흥원의 사업결과"임을 밝혀야 함** (모델·포트폴리오 포함) |
| ESC-50, UrbanSound8K | **비상업적 이용만** 가능 (CC BY-NC) · 출처 표시 필요 · 비상업 목적이면 공유 가능 |
| FSD50K | 출처 표시 필요 |

출처 문구는 프로젝트 README에 함께 정리할 예정이에요.
