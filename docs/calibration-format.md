# 점수 → 확률 변환표 형식 (calibration.json)

웹이 "사이렌 · 확실/보통/낮음"처럼 **믿을 만한 정도**를 보여 주려고 쓰는 표예요.
준형님이 한국 테스트셋으로 평가한 뒤 이 형식으로 만들어 주면, 웹이 그대로 읽어요.

- 정하는 사람: 하민 (웹이 읽는 형식)
- 만드는 사람: 준형 (평가 결과로 출력)
- 파일 위치: `configs/calibration.json`
- 웹 반영: `python src/export_web_classes.py`가 `web/classes.json`의 각 클래스에 `calibration`으로 넣음 (웹은 classes.json 하나만 읽음)

## 형식

```json
{
  "version": 1,
  "score": "yamnet521_max",
  "method": "isotonic",
  "eval": { "set": "korean_test", "n": 3044, "date": "2026-11-27" },
  "levels": [
    { "min": 0.8, "name": "확실" },
    { "min": 0.5, "name": "보통" },
    { "min": 0.0, "name": "낮음" }
  ],
  "classes": {
    "siren": { "x": [0.0, 0.12, 0.3, 0.55, 1.0], "y": [0.02, 0.1, 0.45, 0.85, 0.97] },
    "horn":  { "x": [0.0, 0.2, 0.41, 1.0],       "y": [0.01, 0.15, 0.6, 0.9] }
  }
}
```

(숫자는 예시예요. 실제 값은 평가 결과로 채워요.)

| 필드 | 뜻 |
|---|---|
| `version` | 형식 버전. 지금은 1 |
| `score` | **어떤 점수를 변환하는 표인지**. 웹이 지금 쓰는 점수와 다르면 웹은 이 표를 무시함 |
| `method` | 만든 방법 (`isotonic` 권장, `platt`도 가능하지만 x/y 점으로 바꿔서 출력) |
| `eval` | 어느 데이터로 몇 개를 평가해 만들었는지 (기록용) |
| `levels` | 확률을 화면 글자로 바꾸는 구간. 위에서부터 `min` 이상이면 그 이름 |
| `classes.<id>` | 클래스별 변환 점들. `id`는 classes.yaml의 id와 같아야 함 |

`score` 값은 이렇게 써요.

| 값 | 뜻 |
|---|---|
| `yamnet521_max` | 지금 웹 방식: yamnet_map.yaml로 묶은 YAMNet 라벨 점수 중 최댓값 |
| `head_v1` (예) | 나중에 YAMNet 위 작은 분류기를 붙이면 그 분류기 출력. 분류기를 바꾸면 이름도 바꾸고 표도 새로 만듦 |

## 규칙 (웹이 이렇게 계산해요)

1. `x`와 `y`는 길이가 같고, `x`는 작은 값부터 커지는 순서예요.
2. `y`는 0~1 사이이고 줄어들지 않아요 (점수가 높을수록 확률도 같거나 높음).
3. 점수가 `x` 사이에 있으면 **두 점을 직선으로 이어서** 확률을 구해요.
4. 점수가 `x[0]`보다 작으면 `y[0]`, 마지막 `x`보다 크면 마지막 `y`를 써요.
5. 표에 없는 클래스는 확률을 표시하지 않아요 (점수만 표시).
6. 소수점은 4자리까지면 충분해요.

**알림을 울릴지는 지금처럼 classes.yaml의 `threshold`(점수 기준)로 정해요.** 확률은 화면에 보여 주는 용도예요.

## 만드는 코드 예시 (준형)

scikit-learn의 isotonic 회귀가 이 형식(점 + 직선 연결)과 똑같이 동작해서 그대로 꺼내면 돼요.

```python
import json
from sklearn.isotonic import IsotonicRegression

def to_points(scores, labels):
    # scores: 이 클래스 점수 (0~1), labels: 정답이 이 클래스면 1, 아니면 0
    iso = IsotonicRegression(y_min=0, y_max=1, out_of_bounds="clip").fit(scores, labels)
    return {"x": [round(float(v), 4) for v in iso.X_thresholds_],
            "y": [round(float(v), 4) for v in iso.y_thresholds_]}

cal = {
    "version": 1,
    "score": "yamnet521_max",
    "method": "isotonic",
    "eval": {"set": "korean_test", "n": 3044, "date": "2026-11-27"},
    "levels": [{"min": 0.8, "name": "확실"}, {"min": 0.5, "name": "보통"}, {"min": 0.0, "name": "낮음"}],
    "classes": {
        "siren": to_points(siren_scores, siren_labels),
        "horn": to_points(horn_scores, horn_labels),
    },
}
json.dump(cal, open("configs/calibration.json", "w", encoding="utf-8"), ensure_ascii=False, indent=2)
```

주의: 점수를 계산하는 방식(라벨 묶음, 1초 창, 창마다 최댓값)은 웹과 같아야 해요.
같은 `configs/yamnet_map.yaml`을 쓰면 돼요.
