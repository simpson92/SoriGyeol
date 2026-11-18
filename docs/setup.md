# 소리결(SoriGyeol) 개발 환경 세팅 가이드

> 팀원용 · Windows + WSL(Ubuntu) + VS Code 기준 · 2026-11-16 작성

이 순서대로 따라 하면 메인 개발 환경과 **똑같은 환경**이 만들어져요.
각 단계의 **✅ 확인** 결과가 같게 나오면 다음 단계로 넘어가면 돼요.

---

## 0. 사전 준비

| 항목 | 확인 방법 |
|---|---|
| GitHub 초대 수락 | 메일 또는 [github.com/notifications](https://github.com/notifications)에서 `simpson92/SoriGyeol` 초대 **Accept** |
| WSL(Ubuntu) 설치 | Windows 시작 메뉴에서 **Ubuntu** 실행되면 OK |
| VS Code + WSL 확장 | VS Code 확장(Extensions)에서 **WSL** 설치 |

---

## 1. VS Code를 WSL로 열기

1. VS Code 실행
2. 왼쪽 아래 **파란색 `><` 버튼** 클릭 → **Connect to WSL**
3. 왼쪽 아래가 **`WSL: Ubuntu`** 로 바뀌면 성공
4. 메뉴 **Terminal → New Terminal** (또는 `Ctrl + ~`)로 터미널 열기

✅ 확인: 터미널에 `사용자이름@컴퓨터이름:~$` 형태가 보임

---

## 2. Git 사용자 정보 확인

```bash
git --version
git config user.name
git config user.email
```

이름이나 이메일이 비어 있으면 **본인 GitHub 계정 정보**로 설정:

```bash
git config --global user.name "본인GitHub아이디"
git config --global user.email "본인GitHub이메일"
```

✅ 확인: 두 명령 모두 본인 정보가 출력됨

---

## 3. 레포 받기 (clone)

```bash
mkdir -p ~/ai_vision
cd ~/ai_vision
git clone https://github.com/simpson92/SoriGyeol.git
cd SoriGyeol
code .
```

`code .`을 실행하면 이 폴더가 VS Code 새 창으로 열려요. **이후 작업은 새 창의 터미널에서** 해주세요.

✅ 확인

```bash
git status
git remote -v
```

- `On branch main` 이 나옴
- `origin  https://github.com/simpson92/SoriGyeol.git` 이 나옴
- 왼쪽 탐색기에 `configs/ docs/ notebooks/ src/ web/ .gitignore README.md requirements.txt` 가 보임

> `data/`, `models/` 폴더는 GitHub에 올리지 않기 때문에 처음엔 없어요. 다음 명령으로 만들어 두세요.
> ```bash
> mkdir -p data/raw data/processed models
> ```

---

## 4. GPU 확인

```bash
nvidia-smi
```

- **NVIDIA GPU가 있으면**: GPU 이름과 메모리가 표로 나옴 → 6단계에서 **GPU 버전** 설치
- **에러가 나면**: GPU가 없거나 드라이버 문제 → 6단계에서 **CPU 버전** 설치 (그래도 진행 가능)

---

## 5. uv 설치 + Python 3.11 가상환경

시스템 Python은 건드리지 않고, **이 프로젝트 폴더 안에서만** Python 3.11을 써요.

```bash
# uv 설치
curl -LsSf https://astral.sh/uv/install.sh | sh
source $HOME/.local/bin/env
uv --version

# 3.11 가상환경 만들고 켜기 (~/ai_vision/SoriGyeol 안에서)
uv venv --python 3.11 .venv
source .venv/bin/activate
python --version
```

✅ 확인

- 터미널 줄 앞에 **`(.venv)`** 가 붙음
- `Python 3.11.x` 출력

---

## 6. PyTorch 설치

**GPU가 있는 경우 (4단계에서 표가 나옴)**

```bash
uv pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu128
```

**GPU가 없는 경우**

```bash
uv pip install torch torchaudio --index-url https://download.pytorch.org/whl/cpu
```

용량이 커서 몇 분 걸릴 수 있어요.

---

## 7. 나머지 라이브러리 설치

```bash
uv pip install -r requirements.txt
```

---

## 8. 최종 확인

```bash
python -c "import numpy, librosa, soundfile, sklearn, torch; print('torch', torch.__version__); print('numpy', numpy.__version__); print('librosa', librosa.__version__); print('GPU', torch.cuda.is_available())"
```

✅ 메인 환경 기준 결과

```
torch 2.11.0+cu128
numpy 2.4.6
librosa 0.11.0
GPU True
```

- 버전 숫자가 조금 달라도 에러 없이 출력되면 OK
- GPU가 없는 환경이면 `GPU False` 가 정상

여기까지 되면 세팅 완료예요! 🎉

---

## 매번 작업 시작할 때

```bash
cd ~/ai_vision/SoriGyeol
source .venv/bin/activate
git pull
```

1. 프로젝트 폴더로 이동
2. 가상환경 켜기 (`(.venv)` 붙는지 확인)
3. **작업 전에 항상 `git pull`** 로 최신 내용 받기

## 작업 올릴 때

```bash
git add 바꾼파일
git status
git commit -m "무엇을 했는지 한 줄로"
git push
```

## 주의할 점

- `data/`, `models/`, `.venv/` 는 **절대 커밋하지 않기** (`.gitignore`에 이미 등록됨)
- `git add` 후 `git status`로 데이터나 모델 파일이 섞이지 않았는지 꼭 확인
- 작업 기록은 `docs/devlog.md`에 날짜별로 이어서 작성

---

## 자주 나오는 문제

| 증상 | 원인 | 해결 |
|---|---|---|
| `fatal: not a git repository` | 레포 폴더 밖에서 실행함 | `cd ~/ai_vision/SoriGyeol` 후 다시 실행 |
| `uv: command not found` | 설치 직후 경로가 반영 안 됨 | `source $HOME/.local/bin/env` 실행, 또는 터미널 새로 열기 |
| `(.venv)`가 안 보임 | 가상환경이 꺼져 있음 | `source .venv/bin/activate` |
| `No module named 'numpy'` 경고 | 7단계 설치 전 | 7단계 실행하면 사라짐 |
| `GPU False` (GPU가 있는데) | CPU 버전 torch가 설치됨 | 6단계 **GPU 버전** 명령으로 다시 설치 |
| push 할 때 비밀번호를 물어봄 | GitHub는 비밀번호 대신 토큰 사용 | GitHub → Settings → Developer settings → **Personal access tokens**에서 토큰 발급 후 비밀번호 자리에 입력 |
| push 할 때 `Permission denied` / `403` | 초대 수락 안 함 | 0단계 초대 **Accept** 확인 |
