"""configs/classes.yaml + configs/yamnet_map.yaml → web/classes.json

웹 앱(브라우저)은 YAML을 읽지 못하므로 웹에 필요한 것만 JSON 하나로 내보낸다.
  - classes.yaml   → 클래스의 id·이름·우선순위·사용 여부 (+ 있으면 threshold)
  - yamnet_map.yaml → 클래스마다 묶을 YAMNet 라벨 (yamnet_labels)

둘 중 하나라도 고친 뒤에는 이 스크립트를 실행하고, web/classes.json을 같은 PR에 넣는다.

실행 (레포 맨 위에서):
    python src/export_web_classes.py
"""

import json
import sys
from collections import Counter
from pathlib import Path

try:
    import yaml
except ImportError:
    sys.exit("pyyaml이 필요해요. 먼저 실행하세요: uv pip install pyyaml")

ROOT = Path(__file__).resolve().parents[1]
CLASSES = ROOT / "configs" / "classes.yaml"
YAMNET_MAP = ROOT / "configs" / "yamnet_map.yaml"
DST = ROOT / "web" / "classes.json"

KEYS = ("id", "name_ko", "priority", "enabled")
OPTIONAL_KEYS = ("threshold",)  # 있으면 같이 내보냄 (YAMNet 평가로 정한 클래스별 기준 점수)


def load_yaml(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def main() -> None:
    cfg = load_yaml(CLASSES)
    mapping = load_yaml(YAMNET_MAP).get("mapping", {})

    # 같은 YAMNet 라벨이 두 클래스에 들어 있으면 점수가 양쪽에 겹쳐 잡히므로 막는다
    dup = [label for label, n in Counter(l for ls in mapping.values() for l in ls).items() if n > 1]
    if dup:
        sys.exit(f"yamnet_map.yaml에서 두 클래스에 같이 들어간 라벨이 있어요: {dup}")

    known_ids = {c["id"] for c in cfg["classes"]} | {c["id"] for c in cfg.get("candidates", [])}
    unknown = sorted(set(mapping) - known_ids)
    if unknown:
        print(f"[주의] yamnet_map.yaml에 classes.yaml에 없는 id가 있어요: {unknown}")

    classes = []
    for c in cfg["classes"]:
        missing = [k for k in KEYS if k not in c]
        if missing:
            sys.exit(f"classes.yaml의 '{c.get('id', '?')}' 항목에 {missing}가 없어요.")
        item = {k: c[k] for k in KEYS}
        item.update({k: c[k] for k in OPTIONAL_KEYS if k in c})
        item["yamnet_labels"] = mapping.get(c["id"], [])
        classes.append(item)

    # 알림 대상인데 연결된 YAMNet 라벨이 없으면 웹에서 절대 감지되지 않으므로 알려 준다
    no_labels = [c["id"] for c in classes if c["enabled"] and c["priority"] > 0 and not c["yamnet_labels"]]
    if no_labels:
        print(f"[주의] 알림 대상인데 yamnet_map.yaml에 라벨이 없는 클래스: {no_labels}")

    out = {
        "_note": "자동 생성 파일. 직접 고치지 말고 configs/classes.yaml · configs/yamnet_map.yaml을 고친 뒤 "
                 "src/export_web_classes.py를 실행하세요.",
        "version": cfg.get("version"),
        "classes": classes,
    }
    DST.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    alerts = [c["name_ko"] for c in classes if c["enabled"] and c["priority"] > 0 and c["yamnet_labels"]]
    print(f"{DST.relative_to(ROOT)} 저장 완료 · 클래스 {len(classes)}개 · 알림 대상: {', '.join(alerts) or '없음'}")


if __name__ == "__main__":
    main()
