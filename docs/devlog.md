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
- [ ] Python 3.11 가상환경 생성
- [ ] PyTorch(GPU) 및 오디오 라이브러리 설치
- [ ] GPU 인식 확인