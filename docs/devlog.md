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
- [ ] 데이터 목록 표(manifest) 만드는 코드 작성: 세 데이터셋을 같은 형식(파일 경로 · 원래 라벨 · 우리 클래스 · 출처 · 원본 ID · 길이)으로 통합
- [ ] 학습 / 검증 / 테스트 분할 규칙 정하기 (UrbanSound8K fold 유지, 원본 ID 기준)
- [ ] 소리 몇 개 직접 들어보고 스펙트로그램으로 그려보기