# 소리결 Git 작업 규칙

> 2026-11-17 정함 · 팀원 2명 (웹 앱 / 모델·데이터)

## 원칙

- `main`은 항상 동작하는 상태로 둔다. GitHub Pages가 `main`의 `web/`을 배포한다.
- 작업 하나마다 브랜치를 새로 만들고, 끝나면 PR로 `main`에 합친 뒤 지운다.
- 브랜치를 며칠 이상 오래 끌지 않는다. 길어지면 작게 나눠서 먼저 합친다.

## 브랜치 이름

| 영역 | 이름 | 예시 |
|---|---|---|
| 웹 앱 | `web/작업이름` | `web/vibration`, `web/wake-lock` |
| 모델·데이터 | `data/작업이름` | `data/esc50-prep`, `data/yamnet-eval` |
| 문서 | `docs/작업이름` | `docs/setup-guide` |

작업이름은 영어 소문자와 `-`로 짧게 쓴다.

## 순서

**1. 시작할 때**

```bash
git switch main
git pull
git switch -c web/작업이름
```

**2. 작업하고 올릴 때**

```bash
git add 바꾼파일
git status                     # data/, .wav, .venv가 섞이지 않았는지 확인
git commit -m "feat(web): 무엇을 했는지 한 줄로"
git push -u origin web/작업이름   # 처음 한 번만 -u, 그다음부터는 git push
```

**3. 합치기 (GitHub)**

1. 레포 페이지의 **Compare & pull request** 버튼으로 PR을 만든다.
2. 다른 팀원이 확인하고 **Merge** 한다.

**4. 합친 뒤 정리**

```bash
git switch main
git pull
git branch -d web/작업이름
```

## 커밋 메시지

`종류(영역): 내용` 형식으로 한 줄로 쓴다.

| 종류 | 언제 |
|---|---|
| `feat` | 새 기능 |
| `fix` | 버그 수정 |
| `docs` | 문서 |
| `data` | 데이터 정리, 평가 스크립트 |
| `chore` | 설정, 정리 |

예: `feat(web): 사이렌 감지 시 화면 깜빡임`, `data(eval): YAMNet 사이렌 감지율 측정`

## 주의

- `data/`, `models/`, `.venv/`는 커밋하지 않는다 (`.gitignore`에 등록됨).
- 이미 push한 커밋은 `--amend`나 `reset`으로 고치지 않는다. 다른 사람이 받은 기록과 어긋난다. 고칠 게 있으면 새 커밋으로 고친다.
- `docs/devlog.md`는 하루 한 사람이 정리해서 올린다 (두 사람이 동시에 끝에 추가하면 충돌이 잘 난다).
