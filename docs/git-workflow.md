# 소리결 Git 작업 규칙

> 2026-11-17 정함 · 2026-11-18 수정 · 2026-11-19 Merge 규칙 수정 · 2026-11-20 모든 변경 PR · 상대가 Merge · 팀원 2명 (웹 앱 / 모델·데이터)

## 원칙

- `main`은 항상 동작하는 상태로 둔다. GitHub Pages가 `main`의 `web/`을 배포한다.
- **모든 변경은 브랜치 → PR로 올린다.** `main`에 바로 push하지 않는다 (`docs/` 포함).
- **PR은 상대가 확인하고 Merge한다.** PR을 만든 사람은 직접 Merge하지 않는다.
- `configs/classes.yaml`, `configs/yamnet_map.yaml`을 고쳤으면 `python src/export_web_classes.py`를 실행해 `web/classes.json`도 같은 PR에 넣는다.
- 브랜치를 며칠 이상 오래 끌지 않는다. 길어지면 작게 나눠서 먼저 합친다.

## 브랜치 이름

| 영역 | 이름 | 예시 |
|---|---|---|
| 웹 앱 | `web/작업이름` | `web/alert`, `web/approach-trend` |
| 모델·데이터 | `data/작업이름` | `data/yamnet-eval` |
| 클래스 설정 | `config/작업이름` | `config/siren-threshold` |
| 문서 | `docs/작업이름` | `docs/devlog-11-20`, `docs/daily-csv` |

작업이름은 영어 소문자와 `-`로 짧게 쓴다.

## 작업 순서

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

1. 레포 페이지의 **Compare & pull request** 버튼으로 PR을 만든다. 설명란에 **무엇을, 왜** 바꿨는지 적는다.
2. PR 화면 오른쪽 **Reviewers**에 상대를 지정한다.
3. **상대가 확인하고 Merge한다.** 고칠 점이 있으면 PR에 댓글로 남기고, 만든 사람이 같은 브랜치에 커밋을 더 올린 뒤 다시 확인한다.
4. `web/` PR은 만든 사람이 PR 전에 직접 동작을 확인한다. Merge하면 바로 배포되므로, Merge 후 배포된 사이트를 휴대폰에서 한 번 더 확인한다.
5. 잘못 합쳐졌으면 PR 페이지의 **Revert** 버튼으로 되돌리는 PR을 만든다 (이것도 상대가 Merge).
6. Merge된 브랜치에는 더 커밋하지 않는다. 이어서 할 일은 새 브랜치로 시작한다.

**4. 합친 뒤 정리**

```bash
git switch main
git pull
git branch -d web/작업이름
git push origin --delete web/작업이름   # GitHub에서 Delete branch를 눌렀다면 생략
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
