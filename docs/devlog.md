# 소리결(SoriGyeol) 개발 일지

---

## 2026-11-16 · 0단계 프로젝트 준비 (1) — 레포 세팅

### 한 일
- GitHub 레포 생성 및 이름 정리 (`-SoriGyeol-` → `SoriGyeol`)
- 로컬 폴더(WSL `~/ai_vision/SoriGyeol`)를 깃 저장소로 초기화하고 원격 레포 연결
- 기본 폴더 구조, `.gitignore`, README 초안 작성 → 첫 커밋 · 푸시

### 환경 확인
| 항목 | 결과 |
|---|---|
| 작업 환경 | Windows + WSL(Ubuntu), VS Code |
| Python | 3.14.4 (시스템 기본) |
| Git | 2.53.0 |
| GPU | NVIDIA GeForce RTX 3060 (12GB) |

### 실행한 명령어
```bash
git init -b main
git remote add origin https://github.com/simpson92/SoriGyeol.git
mkdir -p configs docs notebooks src web data/raw data/processed models
touch configs/.gitkeep docs/.gitkeep notebooks/.gitkeep src/.gitkeep web/.gitkeep
git add .
git commit -m "프로젝트 초기 구조 생성"
git push -u origin main
```

### 폴더 구조
```
SoriGyeol/
├── configs/     클래스 목록 등 설정 파일
├── data/        데이터 (Git 제외)
│   ├── raw/        받은 원본
│   └── processed/  정리된 데이터
├── docs/        아키텍처, 개발 일지, 실험 기록
├── models/      학습된 모델 (Git 제외)
├── notebooks/   데이터 탐색용
├── src/         파이썬 코드
├── web/         데모 화면, 이후 PWA
└── README.md
```

### 결정과 이유
- **레포 이름 변경**: 이름에 특수문자를 넣자 GitHub가 `-`로 바꿔 `-SoriGyeol-`이 됨 → 포트폴리오 링크로 쓰기 좋게 `SoriGyeol`로 변경
- **WSL에서 작업**: 데이터 처리·학습과 AI Hub 데이터 다운로드(분할 압축 병합에 리눅스 명령 필요)에 유리. 실시간 마이크는 WSL에서 다루기 어려우므로, 데모 단계에서 **브라우저로 마이크를 받는 방식**으로 해결 예정 (PWA와 같은 방식이라 작업이 이어짐)
- **`data/`, `models/`는 Git에서 제외**: 용량이 크고 데이터셋 이용 조건상 재배포 불가 → README에 받는 방법만 기록
- **Python 3.14 대신 3.11 사용 예정**: 3.14는 너무 최신이라 오디오·AI 라이브러리 호환 위험 → 프로젝트 전용 3.11 가상환경을 따로 구성

### 문제와 해결
| 문제 | 원인 | 해결 |
|---|---|---|
| `git status` → `not a git repository` | VS Code의 GitHub 로그인과 폴더의 깃 연결은 별개 | `git init` + `git remote add`로 연결 |

### 다음 할 일
- [x] Python 3.11 가상환경 생성
- [x] PyTorch(GPU) 및 오디오 라이브러리 설치
- [x] GPU 인식 확인

---

## 2026-11-16 · 0단계 프로젝트 준비 (2) — 개발 환경 구성

### 한 일
- uv로 프로젝트 전용 Python 3.11 가상환경(`.venv`) 생성
- PyTorch GPU 버전(CUDA 12.8) 설치 및 GPU 인식 확인
- 데이터·오디오 기본 라이브러리 설치
- `requirements.txt` 작성 후 커밋 · 푸시

### 설치 결과
| 항목 | 버전 |
|---|---|
| uv | 0.13.8 |
| Python (가상환경) | 3.11.18 |
| PyTorch / torchaudio | 2.11.0 + cu128 |
| numpy | 2.4.6 |
| librosa | 0.11.0 |
| GPU 인식 | `torch.cuda.is_available()` → **True** (RTX 3060) |

### 실행한 명령어
```bash
# uv 설치
curl -LsSf https://astral.sh/uv/install.sh | sh
source $HOME/.local/bin/env

# 3.11 가상환경 생성 · 활성화
uv venv --python 3.11 .venv
source .venv/bin/activate

# PyTorch (GPU)
uv pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu128

# 데이터 · 오디오 라이브러리
uv pip install numpy pandas matplotlib scikit-learn librosa soundfile tqdm pyyaml ipykernel

# 확인
python -c "import numpy, librosa, soundfile, sklearn, torch; print(numpy.__version__, librosa.__version__, torch.cuda.is_available())"
```

### 설치한 라이브러리와 용도
| 라이브러리 | 용도 |
|---|---|
| torch, torchaudio | 모델 학습, 오디오 변환 |
| numpy, pandas | 숫자 계산, 데이터 목록 정리 |
| matplotlib | 그래프, 스펙트로그램 시각화 |
| scikit-learn | 평가 지표 (재현율, 혼동행렬) |
| librosa, soundfile | 오디오 파일 읽기, 소리 분석 |
| tqdm | 진행률 표시 |
| pyyaml | 설정 파일(클래스 목록 등) 읽기 |
| ipykernel | 노트북에서 가상환경 사용 |

### 결정과 이유
- **uv로 Python 3.11 별도 설치**: 시스템 Python(3.14)은 그대로 두고 프로젝트 폴더 안에서만 3.11 사용 → 다른 프로젝트에 영향 없음, 설치 속도도 빠름
- **CUDA 12.8용 PyTorch**: 드라이버가 CUDA 13.3까지 지원하므로 12.8 빌드 사용 가능
- **라이브러리는 특정 데이터셋에 종속되지 않음**: 어떤 오디오 데이터든 공통으로 쓰는 도구라, 데이터셋을 바꿔도 재설치 불필요
- **데이터 교체에 대비한 구조(예정)**: 데이터셋마다 변환 코드를 두고 모두 같은 형식의 목록 표(파일 경로 · 원래 라벨 · 우리 클래스 · 출처 · 원본 녹음 ID)로 통일. 라벨 매핑은 `configs/`의 설정 파일로 관리 → 학습 코드는 이 표만 읽음
- **VS Code 인터프리터는 지정하지 않음**: 작업 시작할 때마다 `source .venv/bin/activate`로 직접 활성화

### 문제와 해결
| 문제 | 원인 | 해결 |
|---|---|---|
| GPU 확인 시 `No module named 'numpy'` 경고 | PyTorch만 먼저 설치해 numpy가 없었음 | numpy 설치 후 경고 사라짐 |

### 작업 시작할 때마다
```bash
cd ~/ai_vision/SoriGyeol
source .venv/bin/activate
```

### 다음 할 일
- [x] 1차 클래스 확정
- [x] AI Hub "도시 소리 데이터" 다운로드 신청
- [x] 해외 공개 데이터 다운로드 (UrbanSound8K, ESC-50)
- [x] 데이터 살펴보기 (클래스별 개수, 길이, 샘플레이트)

---

## 2026-11-17 · 1단계 데이터 준비 (1) — 다운로드 · 탐색 · 클래스 확정

### 한 일
- AI Hub "도시 소리 데이터" 신청(자동 승인) 및 필요한 부분만 선택 다운로드
- ESC-50, UrbanSound8K 다운로드 · 압축 해제 · 개수 검증
- AI Hub zip 압축 해제 스크립트 작성 (`src/unzip_aihub.py`, 한글 파일명 깨짐 방지)
- AI Hub 라벨(JSON) 구조 분석
- FSD50K는 라벨 파일(335KB)만 받아 클래스 구성 확인
- 1차 클래스 확정 및 라벨 연결표 작성 (`configs/classes.yaml`)

### 받은 데이터
| 데이터 | 위치 (`data/raw/`) | 내용 | 확인 결과 |
|---|---|---|---|
| AI Hub 도시 소리 | `aihub_urban_sound/` | 교통소음 소리 + 교통·생활·사업장소음 라벨 (Training + Validation) | wav 28,643 · json 67,793 |
| ESC-50 | `esc50/ESC-50-master/` | 50종 × 40개, 5초 | wav 2,000 |
| UrbanSound8K | `urbansound8k/UrbanSound8K/` | 10종, 최대 4초, fold1~10 | wav 8,732 |
| FSD50K (라벨만) | `fsd50k/FSD50K.ground_truth/` | 200종 클래스 목록과 라벨 | 소리 파일은 받지 않음 |

AI Hub에서 받은 파일 (원천데이터는 교통소음만):
`TL_1·2·3`(라벨), `TS_1.교통소음`(23GB), `VL_1·2·3`(라벨), `VS_1.교통소음`(3GB)

### 실행한 명령어
```bash
# ESC-50
mkdir -p data/raw/esc50 && cd data/raw/esc50
wget https://github.com/karolpiczak/ESC-50/archive/refs/heads/master.zip -O esc50.zip
unzip -q esc50.zip && rm esc50.zip

# UrbanSound8K (Zenodo, 약 6GB, 느림)
mkdir -p data/raw/urbansound8k && cd data/raw/urbansound8k
wget -c "https://zenodo.org/records/1203745/files/UrbanSound8K.tar.gz?download=1" -O UrbanSound8K.tar.gz
tar -xzf UrbanSound8K.tar.gz && rm UrbanSound8K.tar.gz

# AI Hub (웹에서 받은 폴더를 data/raw/aihub_urban_sound/ 에 넣은 뒤)
python src/unzip_aihub.py data/raw/aihub_urban_sound            # 압축 해제
python src/unzip_aihub.py data/raw/aihub_urban_sound --delete   # 확인 후 zip 삭제

# FSD50K 라벨만
mkdir -p data/raw/fsd50k && cd data/raw/fsd50k
wget -c "https://zenodo.org/records/4060432/files/FSD50K.ground_truth.zip?download=1" -O FSD50K.ground_truth.zip
unzip -q FSD50K.ground_truth.zip && rm FSD50K.ground_truth.zip
```

### AI Hub 데이터 분석 결과
- **라벨 JSON 구조**: 소리 종류(대·중·소분류), 소리 구간(start~end), 녹음 환경(장소·시간대·날씨), 소리 방향·거리, 데시벨, 음질
- **원천데이터는 이미 소리 구간만 잘린 파일**: 무작위 8개 확인 결과 소리 파일 길이 = 라벨 구간 길이 → 직접 자를 필요 없음
- **실제 파일 이름은 JSON의 `labelName`** (예: `2.이륜자동차_34971_1.wav`), 원본 녹음 1개당 구간 1개
- 원본 44.1kHz 모노, 길이 1~19초로 다양 → 16kHz로 변환 예정
- 녹음 방식이 "인위적 · 생성" → 실제 거리 소리와 차이가 있을 수 있음 (직접 녹음 테스트셋의 필요성)
- 개수가 공개 수량의 약 90%: AI Hub는 학습:검증:테스트 = 8:1:1로 구축, 테스트 10%는 비공개로 판단

**교통소음 소분류별 개수 (Training + Validation)**
| 소분류 | 개수 | 소분류 | 개수 |
|---|---|---|---|
| 차량경적 | 3,588 | 비행기 | 1,952 |
| 차량사이렌 | 2,239 | 헬리콥터 | 3,660 |
| 차량주행음 | 1,909 | 기차 | 2,366 |
| 이륜차경적 | 5,079 | 지하철 | 2,617 |
| 이륜차주행음 | 5,233 | **합계** | **28,643** |

생활소음(발소리, 가구, 청소기, 세탁기, 개, 고양이, 공구, 악기)과 사업장소음(절삭기, 송풍기, 압축기, 항타기, 파쇄기, 콘크리트펌프, 발전기)에는 **경보음 없음** → 대신 한국 생활 배경 소리·오알림 테스트용으로 가치 있음

### FSD50K 라벨 확인 결과
| 라벨 | 개수 | 판단 |
|---|---|---|
| Alarm | 1,864 | 상위 분류. 전화벨 685, 경적 183, 초인종 144, 사이렌 132, 자전거 벨 129 등이 섞여 있음. **"Alarm" 단독 369개**만 실제 경보음 후보 |
| Siren / Vehicle horn | 132 / 183 | 1차 클래스 보충 가능 |
| Bicycle_bell | 129 | 2차 후보 "자전거 벨" 데이터 확보 가능 |
| Doorbell / Knock | 144 / 373 | 실내 모드 후보용 |
| 후진 경고음, 건널목 경보음 | 없음 | 직접 녹음 필요 |

→ **화재경보·연기감지기 전용 클래스는 없음.** 경보음 때문에 25GB 전체를 받을 근거는 아직 부족

### 1차 클래스 확정 (`configs/classes.yaml`)
| 클래스 | 상태 | 데이터 (AI Hub + UrbanSound8K + ESC-50) |
|---|---|---|
| 사이렌 | ✅ 학습 | 2,239 + 929 + 40 = **3,208** |
| 경적 (자동차 + 이륜차) | ✅ 학습 | 8,667 + 429 + 40 = **9,136** |
| 배경 | ✅ 학습 | 17,737 + 7,000 + 1,720 = **26,457** |
| 화재·경보음 | ⏸ 꺼둠 | ESC-50 40개뿐 |

**나중에 추가할 후보**
- 2차 (보행 안전 확장, 직접 녹음 중심): 후진 경고음 → 자전거 벨 → 철도 건널목 경보음
- 실내 모드: 노크·초인종

### 결정과 이유
- **1차는 사이렌 · 경적 · 배경 3개로 시작**: 데이터가 충분한 소리로 학습부터 데모까지 먼저 완성. 1차 목표는 "아이디어가 실제로 동작함"을 증명하는 것이라 클래스 수보다 완성도가 중요
- **1차 범위 기준 = 놓치면 다칠 수 있는 소리**: 노크·초인종은 보행 안전 범위 밖이고, 휴대폰 기본 기능으로 이미 해결된 영역이라 제외
- **자동차 경적 + 이륜차 경적 → "경적" 하나로**: 사용자 입장에서는 같은 행동(비키기)이 필요
- **헷갈리는 소리는 제외(exclude)**: 총소리, 유리 깨짐, 아기 울음, 교회 종, 노크는 배경으로 넣지 않음 → 나중에 클래스로 추가될 때 모델이 혼동하지 않도록
- **AI Hub는 교통소음 원천만 다운로드, 라벨은 3종 모두**: 생활·사업장소음 원천(84GB)을 받을지 라벨로 미리 판단하기 위함
- **ESC-50은 압축 해제 후 zip 삭제, UrbanSound8K도 검증 후 삭제**: 원본 주소가 남아 있어 언제든 재다운로드 가능
- **데이터 공유**: ESC-50 · UrbanSound8K는 비상업 공유 가능(CC BY-NC) → 복사 전달 가능. AI Hub는 신청자 본인에게 허락되는 방식 → 팀원도 직접 신청(자동 승인)

### 문제와 해결
| 문제 | 원인 | 해결 |
|---|---|---|
| UrbanSound8K 다운로드 약 5시간 예상 | Zenodo 서버 속도 | 별도 터미널에서 계속 받으며 다른 작업 진행 (`wget -c`로 이어받기 가능) |
| AI Hub zip 한글 파일명 깨짐 위험 | zip 안 이름이 CP949(윈도우 한글)로 저장됨 | 이름을 복원하며 푸는 스크립트 작성 |
| JSON 출력 시 한글이 `도...`로 보임 | `json.tool`이 한글을 코드로 표시 | 깨진 것 아님, 해석해서 확인 |
| 라벨 개수가 공개 수량보다 10% 적음 | 테스트 데이터 비공개 | 문제없음으로 판단 |
| FSD50K 클래스 목록을 웹에서 확인 불가 | 목록이 데이터 파일 안에만 있음 | 335KB 라벨 파일만 받아 직접 집계 |

### 다음 할 일
- [x] 데이터 목록 표(manifest) 만드는 코드 작성: 세 데이터셋을 같은 형식(파일 경로 · 원래 라벨 · 우리 클래스 · 출처 · 원본 ID · 길이)으로 통합
- [x] 학습 / 검증 / 테스트 분할 규칙 정하기 (UrbanSound8K fold 유지, 원본 ID 기준)
- [ ] 소리 몇 개 직접 들어보고 스펙트로그램으로 그려보기

---

## 2026-11-17 오후 · 협업 정리 — 배포 · 이용정책 · 팀원 데이터

### 한 일
- push 충돌 해결: 하민 님 커밋이 먼저 올라가 있어 push가 거절됨 → `git pull --rebase` 후 push
- 빈 폴더 표시용 `.gitkeep` 정리 (`notebooks/`만 남김)
- GitHub Pages 설정: Settings → Pages → Source를 **GitHub Actions**로 변경 후 수동 실행
- AI Hub 이용정책 원문 확인 → 팀원도 데이터를 직접 신청하기로 결정
- 하민 님 웹 작업 병합 (PR #1 `web/sound-display`): 브라우저 안 YAMNet 소리 분류, 방향 실험(채널 수 측정), Git 작업 규칙 문서

### GitHub Actions 배포 기록
| 실행 | 시간 | 결과 | 이유 |
|---|---|---|---|
| #1 하민 님 첫 웹 커밋 | 12:14 | 실패 | Pages Source 설정 전 |
| #2 .gitkeep 정리 | 14:30 | 실패 | 같은 이유 |
| #3 수동 실행 | 15:45 | 성공 | 설정 변경 후 |
| #4 PR #1 병합 | 17:31 | 성공 | `web/` 변경 시 자동 배포 정상 |

사이트: https://simpson92.github.io/SoriGyeol/ (휴대폰에서 열림, 분류 모델 준비 2.6초)

### 결정과 이유
- **Pages 설정은 레포 주인만 가능**: 하민 님이 배포 파일(`deploy.yml`)을 만들었지만 Source 변경은 레포 주인 권한이라 직접 처리
- **AI Hub 데이터는 팀원에게 복사해 주지 않음**: 이용정책에 "승인받지 않은 다른 사람에게 제공·양도 금지"가 명시됨 → 하민 님도 직접 신청(자동 승인). 해외 데이터는 용량 때문에 각자 받기로 함 → 받는 방법을 `docs/data-download.md`로 정리
- **출처 표시 의무**: AI Hub는 "한국지능정보사회진흥원의 사업결과임을 밝혀야 하며, 2차적 저작물에도 동일" → README와 모델 배포 시 출처 문구 필수

### 문제와 해결
| 문제 | 원인 | 해결 |
|---|---|---|
| `git push` 거절 | 원격에 하민 님 커밋이 먼저 있음 | `git pull --rebase` 후 push, `pull.rebase true` 설정 |
| Actions #1, #2 실패 | Pages Source가 GitHub Actions로 설정되지 않음 | 설정 변경 후 수동 실행 → 성공 |

---

## 2026-11-18 · 1단계 데이터 준비 (2) — 데이터 목록 표 · 분할

### 한 일
- 해외 데이터 3종의 Freesound 녹음 겹침 확인
- 확인 못 했던 항목 정리: Pages 배포 성공 확인, 문서 업로드(`docs/setup.md`, `docs/data-download.md`, `docs/architecture.pdf`), Git 규칙 수정
- 하민 님과 논의: "가까워지는 중 / 멀어지는 중" 기능 추가, 클래스 기준 통일, YAMNet 평가 담당
- 세 데이터셋을 하나로 합친 목록 표 생성 (`src/build_manifest.py`)
- 학습 / 검증 / 테스트 분할 (`src/make_split.py`)

### 실행한 명령어
```bash
python src/build_manifest.py   # → data/processed/manifest.csv (39,375행)
python src/make_split.py       # → manifest.csv에 split 열 추가
```

### Freesound 녹음 겹침
ESC-50 · UrbanSound8K · FSD50K는 모두 Freesound에서 가져온 소리라 같은 녹음이 겹칠 수 있음

| 비교 | 겹치는 녹음 |
|---|---|
| ESC-50 ∩ UrbanSound8K | **94개** (경적 35, 사이렌 8 포함) |
| ESC-50 ∩ FSD50K | 577개 |
| UrbanSound8K ∩ FSD50K | 439개 |

→ 같은 녹음이 학습과 테스트에 나뉘어 들어가면 성능이 부풀려지므로, 원본 녹음 ID를 데이터셋과 상관없이 `fs_<번호>`로 통일해 함께 나눔

### 데이터 목록 표 (manifest)
열: 파일 경로 · 데이터셋 · 원래 라벨 · 우리 클래스 · 학습 사용 여부 · 원본 녹음 ID · 원래 구분 · 길이 · 샘플레이트 · 채널 · AI Hub 녹음 환경(장소, 방향, 거리, 데시벨 등)

| 클래스 | AI Hub | ESC-50 | UrbanSound8K | 합계 | 총 길이 |
|---|---|---|---|---|---|
| 사이렌 | 2,239 | 40 | 929 | 3,208 | 10.0시간 |
| 경적 | 8,667 | 40 | 429 | 9,136 | 17.4시간 |
| 배경 | 17,737 | 1,720 | 7,000 | 26,457 | 64.4시간 |
| 경보음 (꺼둠) | 0 | 40 | 0 | 40 | — |
| 제외 | 0 | 160 | 374 | 534 | — |

### 분할 규칙과 결과
| 데이터셋 | 학습 | 검증 | 테스트 |
|---|---|---|---|
| AI Hub | Training의 90% | Training의 10% | **Validation 전체 = 한국 테스트셋** |
| UrbanSound8K | fold 1~8 | fold 9 | fold 10 |
| ESC-50 | fold 1~3 | fold 4 | fold 5 |

| 클래스 (학습 사용분) | 학습 | 검증 | 테스트 |
|---|---|---|---|
| 사이렌 | 2,584 | 284 | 340 |
| 경적 | 7,365 | 813 | 958 |
| 배경 | 20,971 | 2,574 | 2,912 |
| **합계** | **30,920** | **3,671** | **4,210** |

한국 테스트셋 3,044개: 사이렌 249 · 경적 918 (이륜차 519 + 차량 399) · 배경 1,877

### 결정과 이유
- **한국 데이터를 테스트 중심으로**: 실제로 쓰일 곳이 한국 거리이므로 한국 소리로 평가해야 실제 성능에 가까움. 해외만 / 한국만 / 혼합 비교 실험도 모두 이 한국 테스트셋으로 평가
- **AI Hub 학습·검증은 소분류별 10%씩**: 차량경적과 이륜차경적처럼 세부 종류 비율이 검증 데이터에서도 유지되게 함
- **경보음·제외 데이터도 목록에 남김** (`use=False`): 나중에 클래스를 켤 때 다시 만들 필요 없음
- **"가까워지는 중 / 멀어지는 중" 추가 (하민 님과 결정)**: 좌우 방향은 대부분의 폰에서 어렵지만(모노 입력, 좁은 마이크 간격) 소리 크기의 변화는 마이크 1개로 알 수 있음. 멀어지는 중은 더 엄격하게 판단 (다가오는 차를 멀어진다고 알리는 것이 가장 위험)
- **웹 표시 클래스를 `configs/classes.yaml` 기준으로 통일**: 데모에 보이는 소리와 학습·평가하는 소리를 같게 맞춤 (사이렌·경적, `car_horn` → `horn`). 화재경보·초인종은 꺼두고 데이터가 모이면 추가
- **YAMNet 평가는 모델 담당이 진행**: 테스트셋으로 측정한 추천 기준 점수를 웹(현재 0.3)에 넘김
- **Git 규칙 수정**: 사이트에 영향이 있는 `web/`, `.github/`만 브랜치 → PR, 나머지는 main에 바로 push

### 문제와 해결
| 문제 | 원인 | 해결 |
|---|---|---|
| AI Hub JSON에는 "44.1kHz · 모노"인데 실제로는 스테레오 3,418개, 22.05k·32k·48k 파일 1,356개 | 메타데이터와 실제 파일이 다름 | 실제 파일 기준으로 판단. 16kHz 변환 때 모두 16kHz 모노로 통일 |
| UrbanSound8K는 8kHz부터 192kHz까지 섞임, 16kHz 미만 58개 | 원본 녹음 장비가 제각각 | 16kHz로 통일. 16kHz 미만 파일의 높은 소리는 원래 없으므로 개수만 기록 |
| 파일 길이가 0.0초부터 60초까지 다양, ESC-50은 짧은 소리를 무음으로 채워 5초로 맞춤 | 데이터셋마다 자르는 방식이 다름 | 1초 조각을 만들 때 소리가 큰 조각만 고르고, 파일당 조각 수에 상한을 둘 예정 |
| 분할 검사에서 같은 녹음이 두 split에 걸친 경우 3건 | UrbanSound8K(1건)와 ESC-50(2건) 자체에 같은 녹음이 여러 fold에 들어간 예외가 있음 | 파일이 가장 많은 split으로 모음 (같으면 test 우선). 최종 걸친 녹음 0개 확인 |
| manifest 읽을 때 `DtypeWarning` | AI Hub 환경 정보 열이 다른 데이터셋에서는 빈칸 | 동작에는 문제없음. 공용 읽기 코드 만들 때 정리 |

### 다음 할 일
- [x] 소리 몇 개 직접 듣고 스펙트로그램으로 그려보기 (긴 경적 파일, 겹친 녹음 중 라벨이 다른 2건 포함)
- [x] 16kHz 모노 변환 + 1초 조각 고르기 규칙 정하기
- [ ] YAMNet baseline 평가 (한국 테스트셋 + 해외 테스트셋) → 추천 기준 점수를 웹에 전달

---

## 2026-11-18 저녁 · 1단계 데이터 준비 (3) — 소리 탐색 · 전처리

### 한 일
- 소리 듣기 · 스펙트로그램 노트북으로 데이터를 눈과 귀로 확인 (`notebooks/01_listen_spectrogram.ipynb`)
- 확인 결과로 1초 조각 고르기 규칙을 정함
- 수동 제외 목록 추가 (`configs/manual_exclude.csv`) → `build_manifest.py`가 읽어서 exclude 처리
- 16kHz 모노 변환 (`src/resample_16k.py`), 1초 조각 표 생성 (`src/make_windows.py`)

### 실행한 명령어
```bash
python src/build_manifest.py   # 수동 제외 2개 적용
python src/make_split.py
python src/resample_16k.py     # 38,799개 → data/processed/audio16k (10.6GB, 약 1분)
python src/make_windows.py     # → data/processed/windows.csv (약 1분)
```

### 노트북으로 확인한 것
| 확인 | 결과 |
|---|---|
| 클래스별 모양 | 사이렌 = 오르내리는 선, 경적 = 가로줄 여러 겹, 배경 = 넓게 퍼진 소음 |
| 사이렌 패턴 | AI Hub(한국)는 부드러운 물결, ESC-50은 계단식, US8K는 소음 속 완만한 상승 → 나라마다 다를 수 있음 (예시 몇 개 기준) |
| AI Hub 긴 경적 (58초) | 경적이 **파일 전체**에 있음 (실제 거리보다 비현실적으로 김 → 인위적 녹음) |
| ESC-50 | 짧은 소리 뒤를 **디지털 무음(−200dB)**으로 채워 5초를 맞춤 |
| 엇갈린 겹친 녹음 | US8K "엔진 공회전"(배경) 3개 중 **2개에 경적이 섞임** |
| 16kHz 미만 | 58개 (US8K), 5.5kHz 위가 비어 있음 → 0.15%라 그대로 사용 |

### 조각 고르기 규칙과 결과
| 규칙 | 적용 대상 | 버린 조각 |
|---|---|---|
| 1초 조각 · 0.5초 간격, 1초 미만은 조각 1개 | 전부 | — |
| 디지털 무음(−90dB 미만) 버림 | 전부 | 1,142 |
| 가장 큰 조각보다 10dB 넘게 작으면 버림 | ESC-50 · US8K의 사이렌 · 경적 | 301 |
| 파일당 최대 10조각, 파일 전체에서 고르게 | 학습(train)만 | 250,609 |

| 사용 조각 | 학습 | 검증 | 테스트 | 합계 |
|---|---|---|---|---|
| 사이렌 | 21,949 | 5,907 | 7,448 | 35,304 |
| 경적 | 38,148 | 10,676 | 11,682 | 60,506 |
| 배경 | 172,932 | 40,649 | 47,010 | 260,591 |
| **합계** | **233,029** | **57,232** | **66,140** | **356,401** |

### 결정과 이유
- **"가장 큰 조각만 고르기"는 AI Hub에 쓰지 않음**: 58초 경적 파일에서 가장 큰 조각이 경적이 아닌 다른 소리(13~19초)였음. 이 기준을 쓰면 경적이 있는 나머지 50초를 버리게 됨
- **ESC-50 · US8K의 사이렌 · 경적에만 크기 기준 적용**: 짧은 소리라 조용한 조각에는 그 소리가 없음 (ESC-50 경적은 조각의 44%만 가장 큰 조각의 10dB 이내)
- **학습만 파일당 10조각, 검증 · 테스트는 전부**: 학습은 긴 파일 하나가 독차지하지 않게, 평가는 파일 단위로 웹과 같은 알림 규칙(3번 중 2번)을 적용하기 위해
- **변환한 소리와 조각 표를 따로 저장**: 규칙을 바꿀 때 오래 걸리는 변환은 다시 하지 않고 표만 다시 만듦. 버린 조각도 이유와 함께 표에 남김
- **소리 크기는 정규화하지 않음**: 크기 정보가 조각 고르기와 "가까워지는 중" 판단에 쓰임
- **배경 오염은 YAMNet으로 전체 검사 예정**: US8K는 구간마다 가장 두드러진 소리 하나만 라벨로 붙여서, 배경 라벨에 경적 · 사이렌이 섞일 수 있음

### 문제와 해결
| 문제 | 원인 | 해결 |
|---|---|---|
| 조각이 하나도 남지 않은 파일 23개 (US8K 사이렌 17개 포함) | 무음 기준 −60dB가 너무 높아 **작게 녹음된 진짜 소리**까지 지움 (이 파일들의 가장 큰 조각 −60.5 ~ −75.3dB) | 기준을 −90dB(디지털 무음만)로 낮춤 → 0개 |
| 배경 파일에 경적이 섞임 | US8K 라벨 방식 | 수동 제외 목록에 추가 |
| 1.25초보다 짧은 파일은 조각 크기 그래프가 안 보임 | 조각이 1개라 선이 그려지지 않음 | 가로선으로 표시하도록 노트북 수정 |
| 노트북 출력에 AI Hub 소리가 들어감 | 재생 버튼이 소리를 파일 안에 저장 | 커밋 전에 출력 지우기 (재배포 금지) |

### 다음 할 일
- [ ] YAMNet baseline 평가: 웹과 같은 조건(0.5초 간격, 3번 중 2번)으로 한국 · 해외 테스트셋 → 클래스별 추천 기준 점수를 `classes.yaml`에
- [ ] YAMNet으로 배경 파일 전체 검사 → 경적 · 사이렌이 섞인 배경을 골라 수동 제외 목록에 추가
- [ ] 자체 CNN 학습 (클래스 불균형: 학습 조각 배경 : 경적 : 사이렌 ≈ 8 : 1.7 : 1)

---

## 2026-11-19 · 협업 정리 (2) — 작업 현황 공유 · 의논 결과

### 한 일
- 11-18 작업 현황 PDF 작성 → 하민 님께 공유 (새로 한 것 · 바뀐 규칙 9개 · 의논할 것 5개, 하민 님 작업 포함)
- 의논할 것 5개를 하나씩 결정 → 의논 결과 PDF로 하민 님께 공유
- Git 규칙 문서에 PR Merge 규칙 반영 (`docs/git-workflow.md`)
- 데일리 CSV 시작 (`docs/daily_csv/`, 11-16부터 커밋 날짜 기준으로 나눠 정리)

### 실행한 명령어
```bash
git switch main
git pull
git add docs/git-workflow.md
git commit -m "docs: PR Merge 규칙 수정 (기본 본인 Merge, 중요한 PR은 Reviewers 지정)"
git push
```

### 의논 결과
| # | 안건 | 결정 | 할 사람 |
|---|---|---|---|
| ① | YAMNet 라벨 연결표 위치 | `web/classifier.js` 안에서 `configs/yamnet_map.yaml`로 빼고, 웹과 Python 평가가 같은 파일을 읽음 | 하민 |
| ② | 점수 합치는 방식 | 평가에서 max와 합을 둘 다 계산해 비교 → 하나로 확정. 그때까지 웹은 지금(max) 그대로 | 준형 |
| ③-1 | 기준 점수 넘기는 방법 | `config/` 브랜치에서 `classes.yaml` + `classes.json`을 함께 고쳐 PR | 준형 |
| ③-2 | 화면 % 표시 | 확신도는 계속 보여 주되 평가로 만든 변환표로 **진짜 확률**로 바꿔 표시 · "알림 기준 30%" 문구는 개발 정보 칸으로 · 화면 구조(메인 1개 + 아래 순위 목록)는 그대로 | 준형 → 하민 |
| ④ | 가까워지는 중 / 멀어지는 중 | 초안 숫자(+1.5dB/초 2번 연속 / −3dB/초 3번 연속)로 지금 바로 시작, 테스트하며 조정 | 하민 |
| ⑤ | PR Merge | 기본은 본인 Merge · 중요하다 싶은 PR은 Reviewers에 상대 지정 → 상대가 Merge | 둘 다 |

### 결정과 이유
- **라벨 연결표를 파일 하나로**: 웹과 평가 코드에 같은 표가 따로 있으면 한쪽만 고쳐졌을 때 기준이 어긋나고, 평가로 정한 기준 점수가 웹에 맞지 않게 됨. 평가는 기다리지 않고 지금 표로 시작, PR이 합쳐지면 파일을 읽도록 변경
- **max와 합을 둘 다 평가**: YAMNet은 라벨마다 점수를 따로 내서(점수를 나눠 갖지 않음) 비슷한 라벨이 같이 높게 나오는 경우가 많음 → max도 크게 손해 보지 않을 가능성이 큼. 반대로 합은 약한 라벨 점수까지 더해져 배경에서 오알림이 늘 수도 있음. 어느 쪽이 사이렌과 배경을 더 잘 가르는지는 측정해 봐야 앎. YAMNet은 한 번만 돌리고 계산만 두 번이라 추가 시간은 거의 없음
- **확신도는 보여 주되 진짜 확률로**: 귀로 확인할 수 없는 사용자에게 "얼마나 확실한지"는 판단 근거가 됨. 하지만 YAMNet 점수는 확률이 아님(0.4가 "사이렌일 확률 40%"가 아님) → 평가 결과로 "점수 → 실제로 그 소리였던 비율" 변환표를 만들어 표시
- **"알림 기준 30%"는 개발 정보 칸으로**: 기준 점수는 사용자가 쓸 데 없는 내부 설정값이고, 클래스별 기준이 생기면 30% 고정 표시는 틀린 정보가 됨
- **가까워지는 중 숫자는 계산으로 정한 출발값**: 거리가 절반이 되면 약 6dB 커짐. 시속 50km 구급차가 50m 앞에서 다가오면 약 +2.4dB/초라 +1.5면 잡힘. 폰을 주머니에 넣거나 걸으면서 방향을 바꿔도 크기가 변하므로 실제 테스트로 조정. YAMNet 평가와 상관없는 기능이라 바로 시작
- **Merge는 기본 본인, 중요하면 상대**: 2명 팀이라 파일 삭제 같은 작은 PR까지 기다릴 필요는 없음. 알림 동작 · 기준 점수 · 배포 설정처럼 사이트 핵심이 바뀌는 PR만 Reviewers로 상대를 지정해 한 번 같이 봄. 잘못 합쳐지면 Revert 버튼으로 되돌림

### 문제와 해결
| 문제 | 원인 | 해결 |
|---|---|---|
| Git 규칙은 "다른 팀원이 Merge"인데 PR #3 · #4는 본인이 Merge | 2명 팀에서 작은 PR까지 기다리기 어려움 | 규칙을 실제에 맞게 수정 (기본 본인 Merge, 중요한 PR만 상대 지정) |
| 화면 "알림 대상 아님 (알림 기준 30%)"가 기본값 0.3으로 고정 (`web/main.js`) | 클래스별 기준 점수 추가 전에 만든 문구 | 개발 정보 칸으로 옮기기로 결정 (하민) |
| 의논 결과 초안에 "웹 PR은 Merge 전에 폰에서 확인"이라고 씀 | Merge 전 브랜치는 사이트에 배포되지 않음 (Pages는 `main`만 배포) | "Merge 전 직접 동작 확인, Merge 후 폰에서 사이트 확인"으로 고침 |

### 다음 할 일
- [ ] YAMNet 기준 성능 평가 (`data/yamnet-eval`): max · 합 비교, 클래스별 추천 기준 점수, 점수 → 확률 변환표, 배경 파일 전수 검사
- [ ] 평가 결과로 기준 점수 PR (`config/` 브랜치) · 변환표 전달
- [ ] [하민] 가까워지는 중 / 멀어지는 중 (`web/approach-trend`)
- [ ] [하민] `configs/yamnet_map.yaml`로 라벨 연결표 이동 · "알림 기준 30%" 문구 이동
- [ ] 자체 CNN 학습 (클래스 균형 · 증강) → 해외만 / 한국만 / 혼합 비교 → ONNX

---

## 2026-11-20 · 협업 정리 (3) — 모델 방향 · 하민 님 PR #6~#11 · Git 규칙 변경

### 한 일
- 하민 님 PR 확인 · Merge: #6 임베딩 확인 페이지 + 변환표 형식 문서, #7 아키텍처 v0.2 · 기획서, #8 아키텍처 PDF 교체 · Git 규칙 변경, #9 가까워지는 중 / 멀어지는 중, #10 소리 카드 높이 고정, #11 데일리 CSV 보완
- (11-19 하민 님 PR #5: `configs/yamnet_map.yaml` 분리, "알림 기준 30%" 문구 → 개발 정보 칸, README 데이터 출처 · 라이선스)
- 자체 모델을 웹에서 돌리는 방식 결정, 하민 님 PC 데이터 재생성 완료 확인

### 하민 님 PR 요약
| PR | 내용 | 바뀐 파일 |
|---|---|---|
| #6 | 웹에서 YAMNet 임베딩(1,024개)을 꺼낼 수 있는지 확인하는 페이지, 점수 → 확률 변환표 형식 | `web/lab/embedder.html`, `docs/calibration-format.md` |
| #7 · #8 | 아키텍처 v0.2(웹 앱 직행, 1차 3클래스, 임베딩 + 작은 분류기), 기획서 최신화, **Git 규칙: 모든 변경 PR · 상대가 Merge** | `docs/architecture.pdf/.html`, `docs/기획서.md`, `docs/git-workflow.md` |
| #9 | 가까워지는 중 / 멀어지는 중 표시, 분류 창 1초 → **0.975초(첫 조각만)**, 깜빡임 중에도 소리 카드 표시, 시험 소리 만들기 | `web/approach.js`, `web/main.js`, `src/make_trend_wavs.py`, `web/lab/compare.html` |
| #10 | 소리 카드 높이 고정 (가까워짐 줄 자리 확보), 순위 칩 한 줄 | `web/style.css` 등 |
| #11 | 데일리 CSV 하민 님 내용 보완 (11-17 ~ 11-19) · 11-20 추가 | `docs/daily_csv/` |

### 결정
| 안건 | 결정 |
|---|---|
| 자체 모델을 웹에서 돌리는 방식 | **YAMNet 임베딩(1,024개) 위 작은 분류기**를 한국 데이터로 학습해 먼저 적용. 자체 log-mel CNN은 비교 실험 (더 좋으면 교체) |
| 임베딩 입력 | 최근 0.975초 1개 (분류와 같은 창) |
| 변환표 형식 | `configs/calibration.json` (`docs/calibration-format.md`, 하민 님 문서) |
| Git 규칙 | 모든 변경은 브랜치 → PR (`docs/` 포함), Reviewers에 상대 지정 → 상대가 확인하고 Merge |
| 데일리 CSV | 각자 그때그때 작성 |
| 폰 실기기 테스트 | 준형 (하민 님 폰에 Chrome 없음) |
| 디자인 | 기능 먼저, 디자인은 나중에 논의 |
| 경보음 'Alarm' 라벨 | 알람 시계에도 59%가 나옴 → 경보음 클래스를 켤 때 평가 후 결정 (지금은 인지만) |

### 결정과 이유
- **임베딩 + 작은 분류기 먼저**: 하민 님 확인 페이지에서 웹이 임베딩 1,024개를 약 35ms에 꺼낼 수 있었음 → Python에서 같은 임베딩으로 작은 분류기만 학습하면 웹에 바로 붙일 수 있음. YAMNet 그대로는 사이렌을 Opera로 착각하는 등 한국 소리에 맞추는 과정이 필요. CNN은 처음부터 학습하고 웹 실행(ONNX)까지 만들어야 해서 시간이 더 걸림 → 비교 실험으로 둠
- **0.975초 첫 조각만**: YAMNet은 0.975초 단위로 판단함. 1초를 넣으면 MediaPipe가 조각 2개로 나누고 두 번째 조각은 빈 소리로 채워져 "조용함"이 끼어듦
- **모든 PR 상대 Merge**: 11-19에 "기본 본인 Merge"로 바꿨으나, 서로 바뀐 내용을 PR에서 한 번씩 확인하기로 다시 합의 (PR #8)

### 문제와 해결
| 문제 | 원인 | 해결 |
|---|---|---|
| 1초 창 결과에 "조용함"이 끼어듦 | 1초 → 0.975초 조각 2개, 두 번째는 빈 소리로 채움 | 최근 0.975초를 넣고 첫 조각 결과만 사용 (PR #9) |
| 배경 → 사이렌으로 바뀌는 순간을 "가까워지는 중"으로 착각 | 사이렌 확정 전 배경 크기까지 기울기에 들어감 | 확정 **이후** 측정만 사용 (확정 약 2초 뒤부터 표시) |
| 실제 사이렌 시험에서 "가까워지는 중"이 너무 잠깐 뜸 | 시작 조건(+1.5dB/초)을 매번 다시 확인 | 한번 뜨면 기울기가 같은 방향(+0.5 / −1dB/초)인 동안 유지, 3번 연속 벗어나면 내림 |
| 아키텍처 PDF 깨짐 | — | PDF 교체 + 원본 HTML 추가 (PR #8) |

### 다음 할 일
- [ ] YAMNet 기준 평가 · 변환표 (준형)
- [ ] 역할 분담 정리 (준형 · 하민)

---

## 2026-11-21 · 협업 정리 (4) — 역할 분담

### 한 일
- 역할 분담 확정: **준형 = 숫자를 만드는 쪽(평가 · 학습 · 실측), 하민 = 숫자를 쓰는 쪽(웹)**
- 하민 님 할 일 H1 ~ H9 정리, 하민 님 Claude용 작업 가이드 전달 (레포에는 넣지 않음)
- 공부자료 ③권(웹 알림 · 협업 규칙 · 의논) 개정 — PR #1 ~ #11, 11-20 결정까지 반영
- 집 PC에 레포 clone (문서 · PR 확인용)

### 역할 분담
| 단계 | 담당 | 내용 |
|---|---|---|
| ① YAMNet 기준 평가 | 준형 | max · 합 비교, threshold, 재현율 · 오알림, 배경 전수 검사 (점수 + 임베딩 저장) |
| ② 변환표 `yamnet521_max` | 준형 | `configs/calibration.json` |
| ③ 임베딩 본 화면 통합 | 하민 | 0.975초 임베딩, MediaPipe 버전 정리 |
| ④ 작은 분류기 학습 | 준형 | 1,024 → 3, `head_v1` 변환표 |
| ⑤ 분류기 웹 적용 | 하민 | JS로 실행 |
| ⑥ 폰 실기기 테스트 | 준형 | 진동 · wake lock · 채널 · 가까워짐 실측 → 숫자를 하민 님께 |
| ⑦ 자체 CNN 비교 (선택) | 준형 | 더 좋으면 하민 님이 웹 연결 |
| ⑧ PWA · 디자인 | 하민 | 디자인은 논의 후 |
| ⑨ 실제 거리 녹음 (나중) | 준형 데이터 / 하민 녹음 도구 | |

### 서로 기다리는 것
| 먼저 끝나야 하는 것 | 그다음 |
|---|---|
| 하민 H2 (분류기 가중치 형식 문서) | 준형 ④ 작은 분류기 학습 |
| 준형 ① ② (threshold · 변환표) | 하민 threshold 반영 · H3 변환표 표시 확인 |
| 준형 ④ | 하민 H6 분류기 웹 적용 |
| 준형 ⑥ 폰 실측 | 하민 H5 가까워짐 숫자 조정 |
| 준형 PR | 하민 님 리뷰 · Merge (반대도 같음) |

---

## 2026-11-21 밤 ~ 11-22 · 2단계 준비 — 임베딩 대조 · 평가 스크립트 · 폰 실측 (집 PC)

### 한 일
- 웹과 Python의 YAMNet 임베딩이 같은지 대조 → **같은 16kHz 입력이면 같음** (`src/check_yamnet_web.py`)
- YAMNet 평가 스크립트 2개 작성: `src/extract_yamnet.py`(점수 · 임베딩 저장), `src/eval_yamnet.py`(웹 알림 규칙으로 평가) — 가짜 데이터로 확인, 진짜 데이터 실행은 학원 PC
- ⑥ 폰 실기기 테스트 (Galaxy S22) → 결과 PDF를 하민 님께 공유 (`soriGyeol_experiments_2026-11-22.pdf`)
- 브랜치 `data/yamnet-eval`에 커밋 (PR은 학원에서 결과까지 넣고 한 번에)

### 실행한 명령어
```bash
# 집 PC 환경 (mediapipe 0.10.21은 Python 3.12 이하 → 3.11로)
sudo apt install -y libgles2 libegl1 libgl1
curl -LsSf https://astral.sh/uv/install.sh | sh
uv venv --python 3.11 .venv
source .venv/bin/activate
uv pip install -r requirements.txt "mediapipe==0.10.21"

# 모델
wget -q -O models/yamnet/yamnet.tflite https://storage.googleapis.com/mediapipe-models/audio_classifier/yamnet/float32/1/yamnet.tflite
wget -q -O models/yamnet/yamnet_embedding_metadata.tflite "https://storage.googleapis.com/mediapipe-assets/yamnet_embedding_metadata.tflite?generation=1668295071595506"

# 대조
python src/check_yamnet_web.py data/test/siren_16k.wav
```

### 웹 · Python 임베딩 대조
| 입력 | 어디서 | 앞 5개 값 | L2 크기 | 분류 top3 (앞 1초) |
|---|---|---|---|---|
| `siren.wav` (44.1kHz) | 웹 (11-20) | 0, 1.5016, 0.1680, 0, 0 | 8.9620 | Opera 15 · Alarm 8 · Classical music 8 |
| | Python | 0, 1.6137, 0.1950, 0, 0 | 8.8117 | Opera 11 · Siren 8 · Speech 8 |
| `siren_16k.wav` (16kHz) | 웹 (PC Chrome 157) | 0, **1.6266, 0.1824**, 0, 0 | **8.8047** | Opera 11 · Alarm 8 · Police car (siren) 8 |
| | Python | 0, **1.6266, 0.1824**, 0, 0 | **8.8045** | Opera 11 · Siren 8 · Alarm 8 |

- 임베딩 개수도 같음: 앞 1초 → 2개, 파일 전체 5초 → 6개
- 44.1kHz에서 난 약 2% 차이 = 16kHz로 바꾸는 방식 차이 (브라우저 자체 변환 vs librosa `soxr_hq`). 학습 데이터(`resample_16k.py`)는 librosa 쪽

### 평가 스크립트
| 파일 | 하는 일 |
|---|---|
| `src/extract_yamnet.py` | `windows.csv`의 1초 조각마다 뒤쪽 0.975초(웹과 같은 입력)를 넣어 점수 521개 + 임베딩 1,024개를 `data/yamnet/`에 저장 (float16, 조각과 1:1). train은 `--splits train --keep-only`로 나중에 |
| `src/eval_yamnet.py` | 웹 알림 규칙(3번 중 2번, 같은 소리 5초 재알림 금지)으로 파일 단위 재현율 · 배경 시간당 오알림 계산. max vs 합, threshold 추천 2가지(재현율 목표 / 오알림 목표), 지금 웹 0.3과 비교, 변환표(val로 만들고 test로 확인), 배경 의심 파일 · 놓친 파일 목록 → `data/yamnet/eval/` |
| `.gitignore` | `.venv-*/` 추가 (학원 PC 추출 전용 가상환경) |

### 폰 실기기 테스트 (⑥)
Galaxy S22 · Android 16 · Chrome 157 · 집 PC 스피커로 유튜브 한국 경찰차 사이렌 재생 · 폰은 약 30cm

| 확인 항목 | 결과 |
|---|---|
| 화면 켜짐 유지 (wake lock) | 정상 |
| 조용할 때 | 조용함 33% · −67 dBFS · 오알림 없음 |
| 사이렌 인식 | "경찰차 사이렌" 59 ~ 92% (기준 30%), −26 ~ −48 dBFS에서 잡힘 |
| 진동 · 화면 깜빡임 | 정상 |
| 화면 끄기 → 켜기 | 끄면 감지 멈춤 (웹 앱의 한계) · 켜면 그대로 이어짐 |
| 마이크 채널 수 | **1** (모노) → 이 폰에서는 방향 정보 없음 |
| 가까워짐 · 멀어짐 | 표시는 뜸, 맞는지는 판단 보류 (영상 속 실제 거리 모름) |

### 결정과 이유
- **Python은 mediapipe 0.10.21**: 1.2.3은 임베딩 모델을 못 읽음. 0.10.21은 웹 확인 페이지와 같은 버전이라 대조도 그대로 맞음. 단 numpy 1.x가 필요해서 학원 PC는 학습용 `.venv`(numpy 2)와 따로 `.venv-mp`에 설치
- **추출과 평가를 나눔**: YAMNet 실행은 오래 걸려 한 번만 하고 결과를 저장, 평가 계산은 몇십 초라 조건(목표 재현율 등)을 바꿔 여러 번 돌릴 수 있게
- **threshold 추천을 두 가지로**: 재현율만 맞추면 기준이 너무 낮아져 배경 오알림이 많아질 수 있음 → "재현율 목표"와 "오알림 목표(시간당 1회 이하)"를 같이 보고 고름
- **점수와 임베딩을 한 번에 저장**: 같은 입력에서 평가(점수)와 작은 분류기 학습(임베딩)을 둘 다 쓰므로 YAMNet을 두 번 돌리지 않음
- **devlog를 같은 브랜치에**: 학원 결과까지 넣은 뒤 PR 하나로 하민 님이 스크립트 · 결과 · 기록을 같이 봄

### 문제와 해결
| 문제 | 원인 | 해결 |
|---|---|---|
| `libGLESv2.so.2: cannot open shared object file` | 집 PC WSL에 그래픽 라이브러리 없음 | `sudo apt install -y libgles2` |
| `apt update` 마지막에 `Timeout was reached` | 인터넷 일시 불안정 | `apt install`만 따로 실행 |
| 임베딩 모델 "Unsupported file format" | mediapipe 1.2.3이 옛 형식 임베딩 모델을 못 읽음 | 0.10.21 사용 |
| 다른 임베딩 모델 주소 404 | 공식 임베딩 모델은 `yamnet_embedding_metadata.tflite` 하나뿐 | 그 파일만 사용 |
| 0.10.21이 Python 3.14에 설치 안 됨 | 0.10.21은 3.12까지 지원 | uv로 `.venv`를 3.11로 다시 만듦 (학원 PC와 같은 버전) |
| 웹 · Python 임베딩이 약 2% 다름 | 44.1kHz → 16kHz 변환 방식 차이 | 16kHz 파일로 다시 대조 → 같음 확인 |
| 폰에서 `siren.wav` 사이렌을 전혀 못 잡음 | 디지털로 넣어도 Siren 8% (Opera 11%)라 시험 소리로 부적합 | 유튜브 한국 사이렌으로 바꾸니 바로 잡힘 |
| 알림 순간을 폰 캡처로 잡기 어려움 | 0.5초마다 화면이 바뀜 | 웹에 기록(CSV) 기능 제안 (아래) |

### 하민 님과 의논할 것
| # | 안건 | 제안 |
|---|---|---|
| 1 | 개발 정보 칸에 기록 시작 / CSV 저장 | 0.5초마다 시각 · 1 ~ 3위 라벨과 점수 · 사이렌 / 경적 점수 · dBFS · 기울기 · 상태를 저장 → 폰 실측과 가까워짐 숫자 조정(H5)을 캡처 없이 |
| 2 | 채널 수 1인데 "2채널이지만 두 채널이 똑같아요" 문구 | 채널 수 1이면 "1채널(모노)이라 방향 정보가 없어요"로 분리 |
| 3 | 알림 유지 중 "사이렌 · 확신도 0%" | 유지하는 동안 마지막 확정 확신도를 보여 주거나 문구 변경 |

- 참고: YAMNet 'Alarm' 라벨이 한국 경찰차 사이렌에 최대 74% (알람 시계 59%에 이어 두 번째) → 경보음 클래스를 켤 때 사이렌과 겹칠 수 있음

### 다음 할 일
- [ ] 학원 PC: `.venv-mp` 만들기 → `extract_yamnet.py` 시험(파일 20개) → 전체 → `eval_yamnet.py`
- [ ] 결과로 threshold PR (`config/` 브랜치: `classes.yaml` + `classes.json`) · `calibration.json` PR · `data/yamnet-eval` PR
- [ ] 기록 기능이 생기면 폰 실측 다시 (확정까지 걸린 시간, 가까워짐 기울기)
- [ ] [하민] H2 분류기 가중치 형식 문서 → 준형 ④ 작은 분류기 학습

## 2026-11-23 · 2단계 (1) — YAMNet 기준 평가 실행 · threshold 결정 (학원 PC)

### 한 일
- 학원 PC에 추출 전용 가상환경 `.venv-mp`(Python 3.11 + mediapipe 0.10.21 + numpy 1.x) 만들고 모델 2개 받음
- `extract_yamnet.py`로 val · test 모든 조각의 YAMNet 점수 521개 + 임베딩 1,024개 저장 (약 2분 15초)
- `eval_yamnet.py`로 웹 알림 규칙 그대로 평가 (약 8초) → `data/yamnet/eval/report.md` · `curves.png` 등
- 결과로 threshold를 정하고 PR #12 (`config/yamnet-baseline`): 사이렌 0.45 · 경적 0.15 + `configs/calibration.json`

### 실행한 명령어
```bash
git fetch && git switch data/yamnet-eval && git pull
sudo apt install -y libgles2 libegl1 libgl1
uv venv --python 3.11 .venv-mp
uv pip install --python .venv-mp/bin/python "mediapipe==0.10.21" pandas soundfile tqdm pyyaml scikit-learn matplotlib
mkdir -p models/yamnet
wget -q -O models/yamnet/yamnet.tflite https://storage.googleapis.com/mediapipe-models/audio_classifier/yamnet/float32/1/yamnet.tflite
wget -q -O models/yamnet/yamnet_embedding_metadata.tflite "https://storage.googleapis.com/mediapipe-assets/yamnet_embedding_metadata.tflite?generation=1668295071595506"

.venv-mp/bin/python src/extract_yamnet.py --limit-files 20   # 시험
time .venv-mp/bin/python src/extract_yamnet.py               # 전체 (val, test) · 2m15s
time .venv-mp/bin/python src/eval_yamnet.py                  # 평가 · 8s
```

### 평가 데이터
| split | 사이렌 | 경적 | 배경 | 조각 |
|---|---|---|---|---|
| val | 284 | 813 | 2,574 | 57,464 |
| test | 340 | 958 | 2,912 | 66,431 |

- 한국 = AI Hub, 해외 = ESC-50 + UrbanSound8K. 한국 test = AI Hub Validation
- 출력 파일(`data/yamnet/`)은 git 제외 → 숫자는 이 기록과 PR #12에 남김

### 결과 1 — 조각 단위 구분력 (AUC, test)
| | 사이렌 max | 사이렌 합 | 경적 max | 경적 합 |
|---|---|---|---|---|
| 한국 | 0.983 | 0.983 | 0.961 | 0.958 |
| 해외 | 0.840 | 0.840 | 0.955 | 0.956 |

- 한국 소리는 사이렌 · 경적 모두 배경과 잘 가름 (재학습 없이도)
- 해외 사이렌은 약함 (US8K 사이렌 재현율 0.54 ~ 0.57)

### 결과 2 — 알림 전체 (클래스 기준 같이 적용, max, 한국 test)
| 설정 | 사이렌 / 경적 threshold | 사이렌 재현율 | 경적 재현율 | 배경 시간당 오알림 |
|---|---|---|---|---|
| 지금 웹 | 0.3 / 0.3 | 0.916 | **0.627** | 1.39 |
| **오알림 목표 (채택)** | **0.45 / 0.15** | 0.871 | **0.753** | **0.35** |
| 재현율 목표 | 0.19 / 0.04 | 0.928 | 0.928 | 7.11 |

- 지금 웹 0.3에서 경적 소분류 재현율: 이륜차경적 0.624 · 차량경적 0.632 → 둘 다 비슷하게 약함
- 놓친 경적 파일에서 YAMNet 1위 라벨: Music 76 · Vehicle 26 · Harmonica 12 → **경적을 음악으로 들음**
- 놓친 사이렌 파일 1위 라벨: Animal 20 · Music 10 · Beep, bleep 7

### 결과 3 — 점수 → 확률 변환표 (isotonic, val로 만들고 test로 확인)
| 클래스 | ECE 그대로 → 변환 후 (한국 test) | Brier 그대로 → 변환 후 |
|---|---|---|
| 사이렌 | 0.047 → 0.007 | 0.032 → 0.019 |
| 경적 | 0.118 → 0.005 | 0.093 → 0.030 |

- 변환 후 "표시한 확률"이 실제 비율과 거의 맞음 → `configs/calibration.json`으로 사용 (웹 표시는 H3)

### 결정과 이유
- **threshold = 오알림 목표(사이렌 0.45 · 경적 0.15)**: 지금보다 경적 재현율 +12.6%p, 오알림 1/4. 사이렌 재현율은 −4.5%p. 재현율 목표는 오알림이 약 8분에 한 번이라 알림을 무시하게 될 수 있어 제외. 작은 분류기(④)가 나오기 전까지 쓰는 **임시 값**
- **점수 방식 max 유지**: 합이 사이렌에서 조금 낫고 경적에서 조금 나쁨. 차이가 작고 웹이 이미 max
- **변환표 사용**: ECE가 크게 줄어 확률 표시용으로 충분
- **④ 작은 분류기가 필요한 이유가 숫자로 확인됨**: 구분력(AUC)은 높은데 경적 점수 자체가 낮게 나와 threshold를 낮춰야 함 → 한국 데이터로 학습한 분류기가 점수 크기를 바로잡을 수 있음

### 다음 할 일
- [ ] [하민] PR #12 리뷰 · Merge → 준형 폰에서 "알림 기준: 사이렌 45% · 경적 15%" 확인
- [ ] [하민] H3 `calibration.json` 웹 표시 (`"set": "val"`인 이유는 PR #12 참고)
- [ ] `bg_suspects.csv` 위쪽 파일 직접 듣기 → 진짜 사이렌 · 경적이면 `manual_exclude.csv` 검토 (학원 PC는 소리가 안 나서 방법 따로)
- [ ] [하민] H2 분류기 가중치 형식 문서 → 준형 ④ 작은 분류기 학습 (`extract_yamnet.py --splits train --keep-only`부터)
