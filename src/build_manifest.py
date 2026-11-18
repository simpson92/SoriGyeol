"""세 데이터셋을 하나의 목록 표(manifest)로 합친다.

AI Hub 도시 소리, UrbanSound8K, ESC-50의 소리 파일을 모두 찾아서
"파일 경로 · 원래 라벨 · 우리 클래스 · 원본 녹음 ID · 길이" 같은 형식의 표 하나로 만든다.
라벨 연결은 configs/classes.yaml 을 따른다. 학습 코드는 이 표만 읽으면 된다.

사용법 (프로젝트 폴더에서):
    python src/build_manifest.py

결과:
    data/processed/manifest.csv

열 설명:
    path         소리 파일 경로 (프로젝트 폴더 기준)
    dataset      aihub / us8k / esc50
    orig_label   데이터셋의 원래 라벨
    class        우리 클래스 (siren, horn, background, alarm ...) 또는 exclude
    use          True면 1차 학습에 사용 (classes.yaml에서 enabled: true인 클래스)
    source_id    원본 녹음 ID. 같은 ID는 반드시 같은 split에 넣는다
                 (aihub_<라벨 파일 이름> / fs_<Freesound 번호>)
    orig_split   데이터셋이 원래 나눠 둔 구분 (aihub: train/val, us8k·esc50: fold번호)
    duration, sample_rate, channels   소리 파일 정보
    place ~ sound_quality             AI Hub 녹음 환경 정보 (다른 데이터셋은 빈칸)
"""
import json
import re
import sys
from pathlib import Path

import pandas as pd
import soundfile as sf
import yaml
from tqdm import tqdm

ROOT = Path(__file__).resolve().parents[1]          # 프로젝트 폴더
CONFIG = ROOT / "configs" / "classes.yaml"
OUT = ROOT / "data" / "processed" / "manifest.csv"

AIHUB_META = {  # 열 이름: JSON에서 꺼낼 위치
    "place": ("environment", "place"),
    "day_night": ("environment", "dayNight"),
    "weather": ("environment", "weather"),
    "direction": ("environment", "direction"),
    "distance": ("environment", "distance"),
    "decibel": ("annotation", "decibel"),
    "sound_quality": ("annotation", "soundQuality"),
}


# ------------------------------------------------------------
# 라벨 연결
# ------------------------------------------------------------
def make_mapper(cfg: dict, ds_name: str, class_ids: set):
    """데이터셋 라벨 → 우리 클래스로 바꾸는 함수를 만든다."""
    ds = cfg["datasets"][ds_name]
    mapping = ds.get("mapping", {})
    default = ds.get("default")

    for label, cls in mapping.items():
        if cls != "exclude" and cls not in class_ids:
            sys.exit(f"[설정 오류] {ds_name}: '{label}' → '{cls}' 는 classes에 없는 클래스예요.")

    unknown = set()

    def mapper(label: str) -> str:
        if label in mapping:
            return mapping[label]
        if default:
            return default
        unknown.add(label)
        return "UNKNOWN"

    mapper.unknown = unknown
    return mapper


# ------------------------------------------------------------
# 데이터셋별 목록 만들기
# ------------------------------------------------------------
def collect_aihub(cfg: dict, mapper) -> list[dict]:
    root = ROOT / cfg["datasets"]["aihub_urban_sound"]["root"]
    if not root.exists():
        print(f"[건너뜀] AI Hub 폴더 없음: {root}")
        return []

    # 라벨 JSON 찾아 두기: 파일 이름(확장자 제외) → 경로들
    json_index: dict[str, list[Path]] = {}
    for p in root.rglob("*.json"):
        json_index.setdefault(p.stem, []).append(p)

    rows, missing_json = [], 0
    for wav in tqdm(sorted(root.rglob("*.wav")), desc="AI Hub", unit="file"):
        parts = wav.relative_to(root).parts
        split = "train" if any(s.endswith("Training") for s in parts) else \
                "val" if any(s.endswith("Validation") for s in parts) else ""

        label = re.sub(r"^\d+\.", "", wav.parent.name)          # "4.이륜차경적" → "이륜차경적"
        json_stem = re.sub(r"_\d+$", "", wav.stem)             # "..._34971_1" → "..._34971"

        row = {
            "path": wav, "dataset": "aihub", "orig_label": label,
            "class": mapper(label), "source_id": f"aihub_{json_stem}", "orig_split": split,
        }

        # 같은 이름의 JSON이 여러 개면 같은 split(Training/Validation) 쪽을 고른다
        cands = json_index.get(json_stem, [])
        same = [c for c in cands if split == "" or
                any(s.endswith("Training" if split == "train" else "Validation")
                    for s in c.relative_to(root).parts)]
        jpath = (same or cands or [None])[0]

        if jpath is None:
            missing_json += 1
        else:
            meta = json.loads(jpath.read_text(encoding="utf-8-sig"))
            src = {"environment": meta.get("environment", {}),
                   "annotation": (meta.get("annotations") or [{}])[0]}
            for col, (sec, key) in AIHUB_META.items():
                row[col] = src[sec].get(key)
        rows.append(row)

    if missing_json:
        print(f"[주의] AI Hub 라벨 JSON을 못 찾은 소리 {missing_json}개 (환경 정보 빈칸)")
    return rows


def collect_us8k(cfg: dict, mapper) -> list[dict]:
    root = ROOT / cfg["datasets"]["urbansound8k"]["root"]
    csv = root / "metadata" / "UrbanSound8K.csv"
    if not csv.exists():
        print(f"[건너뜀] UrbanSound8K 목록 없음: {csv}")
        return []
    df = pd.read_csv(csv)
    return [{
        "path": root / "audio" / f"fold{r.fold}" / r.slice_file_name,
        "dataset": "us8k", "orig_label": r["class"], "class": mapper(r["class"]),
        "source_id": f"fs_{r.fsID}", "orig_split": f"fold{r.fold}",
    } for _, r in df.iterrows()]


def collect_esc50(cfg: dict, mapper) -> list[dict]:
    root = ROOT / cfg["datasets"]["esc50"]["root"]
    csv = root / "meta" / "esc50.csv"
    if not csv.exists():
        print(f"[건너뜀] ESC-50 목록 없음: {csv}")
        return []
    df = pd.read_csv(csv)
    return [{
        "path": root / "audio" / r.filename,
        "dataset": "esc50", "orig_label": r.category, "class": mapper(r.category),
        "source_id": f"fs_{int(r.src_file)}", "orig_split": f"fold{r.fold}",
    } for _, r in df.iterrows()]


# ------------------------------------------------------------
# 소리 파일 정보 (길이 · 샘플레이트 · 채널)
# ------------------------------------------------------------
def add_audio_info(df: pd.DataFrame) -> pd.DataFrame:
    info = []
    for p in tqdm(df["path"], desc="소리 정보 읽기", unit="file"):
        try:
            i = sf.info(p)
            info.append((round(i.frames / i.samplerate, 3), i.samplerate, i.channels))
        except Exception:
            info.append((None, None, None))
    df[["duration", "sample_rate", "channels"]] = info
    df["sample_rate"] = df["sample_rate"].astype("Int64")
    df["channels"] = df["channels"].astype("Int64")
    return df


# ------------------------------------------------------------
def main() -> None:
    cfg = yaml.safe_load(CONFIG.read_text(encoding="utf-8"))
    class_ids = {c["id"] for c in cfg["classes"]}
    enabled = {c["id"] for c in cfg["classes"] if c.get("enabled", True)}

    mappers = {name: make_mapper(cfg, name, class_ids)
               for name in ("aihub_urban_sound", "urbansound8k", "esc50")}

    rows = (collect_aihub(cfg, mappers["aihub_urban_sound"])
            + collect_us8k(cfg, mappers["urbansound8k"])
            + collect_esc50(cfg, mappers["esc50"]))
    if not rows:
        sys.exit("[오류] 소리 파일을 하나도 찾지 못했어요. data/raw 위치를 확인하세요.")

    # 연결표에 없는 라벨이 있으면 멈춘다 (classes.yaml에 추가해야 함)
    for name, m in mappers.items():
        if m.unknown:
            sys.exit(f"[설정 오류] {name}: classes.yaml mapping에 없는 라벨 {sorted(m.unknown)}")

    df = pd.DataFrame(rows)
    for col in AIHUB_META:
        if col not in df:
            df[col] = None
    df = add_audio_info(df)
    df["use"] = df["class"].isin(enabled)
    df["path"] = [Path(p).relative_to(ROOT).as_posix() for p in df["path"]]

    cols = ["path", "dataset", "orig_label", "class", "use", "source_id", "orig_split",
            "duration", "sample_rate", "channels", *AIHUB_META]
    df = df[cols]

    OUT.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUT, index=False, encoding="utf-8")

    # ---------------- 확인용 요약 ----------------
    print(f"\n저장: {OUT.relative_to(ROOT)}  ({len(df):,}행)\n")

    print("[데이터셋 × 클래스]")
    print(pd.crosstab(df["class"], df["dataset"], margins=True, margins_name="합계").to_string())

    print("\n[1차 학습에 쓰는 클래스 (use=True)]")
    used = df[df["use"]]
    summary = used.groupby("class").agg(개수=("path", "size"),
                                        시간=("duration", lambda s: round(s.sum() / 3600, 1)))
    summary.columns = ["개수", "총 길이(시간)"]
    print(summary.to_string())

    bad = df[df["duration"].isna()]
    print(f"\n읽지 못한 소리 파일: {len(bad)}개")
    for p in bad["path"].head(5):
        print("  ", p)

    print("\n[샘플레이트 · 채널]")
    print(df.groupby(["dataset", "sample_rate", "channels"]).size().to_string())

    ds_per_id = df.groupby("source_id")["dataset"].nunique()
    print(f"여러 데이터셋에 같이 있는 원본 녹음: {(ds_per_id > 1).sum()}개")


if __name__ == "__main__":
    main()