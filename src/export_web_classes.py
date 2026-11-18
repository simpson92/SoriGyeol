"""configs/classes.yaml → web/classes.json

웹 앱(브라우저)은 YAML을 읽지 못하므로, 클래스의 id·이름·우선순위·사용 여부만 JSON으로 내보낸다.
classes.yaml을 고친 뒤에는 이 스크립트를 실행하고, web/classes.json을 함께 커밋한다.

실행 (레포 맨 위에서):
    python src/export_web_classes.py
"""

import json
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    sys.exit("pyyaml이 필요해요. 먼저 실행하세요: uv pip install pyyaml")

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "configs" / "classes.yaml"
DST = ROOT / "web" / "classes.json"
KEYS = ("id", "name_ko", "priority", "enabled")


def main() -> None:
    cfg = yaml.safe_load(SRC.read_text(encoding="utf-8"))

    classes = []
    for c in cfg["classes"]:
        missing = [k for k in KEYS if k not in c]
        if missing:
            sys.exit(f"classes.yaml의 '{c.get('id', '?')}' 항목에 {missing}가 없어요.")
        classes.append({k: c[k] for k in KEYS})

    out = {
        "_note": "자동 생성 파일. 직접 고치지 말고 configs/classes.yaml을 고친 뒤 src/export_web_classes.py를 실행하세요.",
        "version": cfg.get("version"),
        "classes": classes,
    }
    DST.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    alerts = [c["name_ko"] for c in classes if c["enabled"] and c["priority"] > 0]
    print(f"{DST.relative_to(ROOT)} 저장 완료 · 클래스 {len(classes)}개 · 알림 대상: {', '.join(alerts) or '없음'}")


if __name__ == "__main__":
    main()
