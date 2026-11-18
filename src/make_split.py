"""manifest에 학습/검증/테스트 구분(split 열)을 붙인다.

규칙 (2026-11-18 결정):
    AI Hub        Training의 90% → train, 10% → val (원본 녹음 단위, 소분류 비율 유지)
                  Validation 전체 → test  (= 한국 테스트셋)
    UrbanSound8K  fold 1~8 → train, fold 9 → val, fold 10 → test
    ESC-50        fold 1~3 → train, fold 4 → val, fold 5 → test
    공통          같은 원본 녹음(source_id)은 반드시 같은 split.
                  ESC-50과 UrbanSound8K에 같이 있는 녹음은 UrbanSound8K 쪽을 따른다.
                  그래도 여러 split에 걸친 녹음(UrbanSound8K 안에서 여러 fold에 있는 경우 등)은
                  파일이 가장 많은 split으로 모은다. 같으면 test > val > train 순.

사용법 (build_manifest.py 다음에 실행):
    python src/make_split.py

결과:
    data/processed/manifest.csv 에 split 열을 붙여 덮어쓴다.
    (build_manifest.py를 다시 돌리면 split 열이 없어지므로 이것도 다시 실행)
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "data" / "processed" / "manifest.csv"

SEED = 42                 # 같은 결과가 나오도록 고정
AIHUB_VAL_RATIO = 0.1
FOLD_SPLIT = {
    "us8k":  {"train": range(1, 9), "val": [9], "test": [10]},
    "esc50": {"train": range(1, 4), "val": [4], "test": [5]},
}


def fold_to_split(dataset: str, orig_split: str) -> str:
    fold = int(orig_split.replace("fold", ""))
    for split, folds in FOLD_SPLIT[dataset].items():
        if fold in folds:
            return split
    raise ValueError(f"알 수 없는 fold: {dataset} {orig_split}")


def split_aihub(df: pd.DataFrame) -> pd.Series:
    """AI Hub: Validation → test, Training → 원본 녹음 단위로 train/val."""
    out = pd.Series("test", index=df.index)
    tr = df[df["orig_split"] == "train"]

    # 원본 녹음 1개 = 1그룹. 소분류(orig_label)별로 10%씩 뽑아 val로
    groups = tr.groupby("source_id")["orig_label"].first()
    rng = np.random.default_rng(SEED)
    val_ids = set()
    for _, ids in groups.groupby(groups):
        ids = ids.index.to_numpy()
        n_val = int(round(len(ids) * AIHUB_VAL_RATIO))
        val_ids.update(rng.choice(ids, size=n_val, replace=False))

    out[tr.index] = np.where(tr["source_id"].isin(val_ids), "val", "train")
    return out


def majority_split(splits: pd.Series) -> str:
    """가장 많은 split. 개수가 같으면 test > val > train (평가 쪽을 지킨다)."""
    counts = splits.value_counts()
    top = counts[counts == counts.max()].index
    for s in ("test", "val", "train"):
        if s in top:
            return s
    return top[0]


def main() -> None:
    if not MANIFEST.exists():
        sys.exit("[오류] manifest.csv가 없어요. 먼저 python src/build_manifest.py 를 실행하세요.")
    df = pd.read_csv(MANIFEST, low_memory=False)
    df["split"] = ""

    # 1) 데이터셋별 기본 규칙
    a = df["dataset"] == "aihub"
    df.loc[a, "split"] = split_aihub(df[a])
    for ds in FOLD_SPLIT:
        m = df["dataset"] == ds
        df.loc[m, "split"] = [fold_to_split(ds, s) for s in df.loc[m, "orig_split"]]

    # 2) ESC-50 ∩ UrbanSound8K 같은 녹음 → UrbanSound8K 쪽 split 따르기
    us_split = df[df["dataset"] == "us8k"].groupby("source_id")["split"].agg(majority_split)
    esc = (df["dataset"] == "esc50") & df["source_id"].isin(us_split.index)
    changed = (df.loc[esc, "split"] != df.loc[esc, "source_id"].map(us_split)).sum()
    df.loc[esc, "split"] = df.loc[esc, "source_id"].map(us_split)

    # 3) 그래도 여러 split에 걸친 녹음 → 가장 많은 split으로 모으기
    n_split = df.groupby("source_id")["split"].nunique()
    multi = n_split[n_split > 1].index
    fixed = []
    for sid in multi:
        m = df["source_id"] == sid
        before = df.loc[m].groupby(["dataset", "split"]).size()
        target = majority_split(df.loc[m, "split"])
        df.loc[m, "split"] = target
        fixed.append((sid, ", ".join(f"{d}:{s} {n}" for (d, s), n in before.items()), target))

    # 4) 검사: 같은 원본 녹음이 두 split에 걸쳐 있으면 안 됨
    leak = df.groupby("source_id")["split"].nunique()
    leak = leak[leak > 1]
    if len(leak):
        print(df[df["source_id"].isin(leak.index)][["path", "source_id", "split"]].head(10))
        sys.exit(f"[오류] 여러 split에 걸친 원본 녹음 {len(leak)}개 — 저장하지 않았어요.")

    df.to_csv(MANIFEST, index=False, encoding="utf-8")

    # ---------------- 확인용 요약 ----------------
    print(f"저장: {MANIFEST.relative_to(ROOT)}  ({len(df):,}행, split 열 추가)\n")
    print(f"ESC-50 중 UrbanSound8K를 따라 split이 바뀐 파일: {changed}개")
    print(f"여러 split에 걸쳐 있어 한쪽으로 모은 녹음: {len(fixed)}개")
    for sid, before, target in fixed:
        print(f"   {sid:<14} {before}  →  {target}")
    print("여러 split에 걸친 원본 녹음 (최종): 0개 ✅\n")

    used = df[df["use"]]
    print("[1차 학습 클래스 × split] (use=True)")
    print(pd.crosstab(used["class"], used["split"], margins=True, margins_name="합계")
          .reindex(columns=["train", "val", "test", "합계"], fill_value=0).to_string())

    print("\n[데이터셋 × split] (use=True)")
    print(pd.crosstab(used["dataset"], used["split"], margins=True, margins_name="합계")
          .reindex(columns=["train", "val", "test", "합계"], fill_value=0).to_string())

    kr = used[(used["dataset"] == "aihub") & (used["split"] == "test")]
    print(f"\n[한국 테스트셋 = AI Hub Validation] {len(kr):,}개")
    print(kr["orig_label"].value_counts().to_string())


if __name__ == "__main__":
    main()