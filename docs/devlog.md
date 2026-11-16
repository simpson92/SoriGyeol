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
- [ ] 1차 클래스 확정 (사이렌 · 자동차/이륜차 경적 · 화재·경보음 · 초인종/노크 · 배경)
- [ ] AI Hub "도시 소리 데이터" 다운로드 신청 (승인에 시간이 걸릴 수 있어 먼저 신청)
- [ ] 해외 공개 데이터 다운로드 (UrbanSound8K, ESC-50)
- [ ] 데이터 살펴보기 (클래스별 개수, 길이, 샘플레이트)