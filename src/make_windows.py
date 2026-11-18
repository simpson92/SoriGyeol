"""16kHz 소리 파일을 1초 조각으로 나누고, 학습에 쓸 조각을 고른다.

조각 고르기 규칙 (2026-11-18, notebooks/01_listen_spectrogram.ipynb 확인 결과):
    1. 1초 조각 · 0.5초 간격. 1초보다 짧은 파일은 조각 1개 (학습할 때 뒤를 0으로 채움)
    2. 거의 무음 조각 버림 (SILENCE_DB 미만)              → drop_reason = silence
       (ESC-50은 짧은 소리 뒤를 디지털 무음으로 채워 둠)
    3. ESC-50 · UrbanSound8K의 사이렌 · 경적만,
       가장 큰 조각보다 QUIET_DB 넘게 작은 조각 버림        → drop_reason = quiet
       (짧은 소리라 조용한 조각에는 그 소리가 없음.
        AI Hub는 소리가 파일 전체에 있고, 가장 큰 조각이 다른 소리일 때가 있어 적용 안 함)
    4. 학습(train)만 파일당 최대 MAX_PER_FILE조각, 파일 전체에서 고르게  → drop_reason = cap
       검증 · 테스트는 줄이지 않음 (파일 단위로 알림 규칙을 평가하기 위해)

모든 조각을 표에 남기고, 버린 조각은 drop_reason에 이유를 적는다.
학습 코드는 keep=True인 조각만 쓴다. 규칙을 바꾸면 이 스크립트만 다시 실행하면 된다.

사용법 (resample_16k.py 다음에):
    python src/make_windows.py

결과:
    data/processed/windows.csv
    열: path16k, start(초), db, keep, drop_reason, class, split, dataset, source_id, file_id(manifest 행 번호)
"""
from pathlib import Path

import numpy as np
import pandas as pd
import soundfile as sf
from tqdm import tqdm

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "data" / "processed" / "manifest.csv"
OUT = ROOT / "data" / "processed" / "windows.csv"
RAW = ROOT / "data" / "raw"
AUDIO16K = ROOT / "data" / "processed" / "audio16k"

SR = 16000
WIN, HOP = 1.0, 0.5
SILENCE_DB = -60.0
QUIET_DB = 10.0
QUIET_RULE = {"datasets": {"esc50", "us8k"}, "classes": {"siren", "horn"}}
MAX_PER_FILE = 10


def window_db(y: np.ndarray) -> np.ndarray:
    """1초 조각마다 소리 크기(dBFS). 1초보다 짧으면 0으로 채워 조각 1개"""
    w, h = int(WIN * SR), int(HOP * SR)
    if len(y) < w:
        y = np.pad(y, (0, w - len(y)))
    frames = np.lib.stride_tricks.sliding_window_view(y, w)[::h]
    rms = np.sqrt(np.mean(frames.astype(np.float64) ** 2, axis=1))
    return 20 * np.log10(rms + 1e-10)


def even_pick(idx: np.ndarray, k: int) -> np.ndarray:
    """idx 중 k개를 처음부터 끝까지 고르게"""
    if len(idx) <= k:
        return idx
    return idx[np.unique(np.linspace(0, len(idx) - 1, k).round().astype(int))]


def main() -> None:
    df = pd.read_csv(MANIFEST, low_memory=False)
    files = df[df["use"]]

    rows, missing, done = [], 0, set()
    for fid, r in tqdm(files.iterrows(), total=len(files), unit="file"):
        p16 = AUDIO16K / (ROOT / r["path"]).relative_to(RAW)
        if not p16.exists():
            missing += 1
            continue
        y, _ = sf.read(p16, dtype="float32")
        done.add(fid)
        db = window_db(y)
        reason = np.full(len(db), "", dtype=object)

        reason[db < SILENCE_DB] = "silence"
        if r["dataset"] in QUIET_RULE["datasets"] and r["class"] in QUIET_RULE["classes"]:
            alive = reason == ""
            if alive.any():
                reason[alive & (db < db[alive].max() - QUIET_DB)] = "quiet"
        if r["split"] == "train":
            alive = np.flatnonzero(reason == "")
            keep = even_pick(alive, MAX_PER_FILE)
            reason[np.setdiff1d(alive, keep)] = "cap"

        p16_rel = p16.relative_to(ROOT).as_posix()
        for i, (d, why) in enumerate(zip(db, reason)):
            rows.append((p16_rel, round(i * HOP, 2), round(float(d), 1), why == "", why,
                         r["class"], r["split"], r["dataset"], r["source_id"], fid))

    if missing:
        print(f"[주의] 16kHz 파일이 없는 소리 {missing}개 — 먼저 python src/resample_16k.py 실행")

    w = pd.DataFrame(rows, columns=["path16k", "start", "db", "keep", "drop_reason", "class", "split",
                                    "dataset", "source_id", "file_id"])
    w.to_csv(OUT, index=False, encoding="utf-8")

    # ---------------- 확인용 요약 ----------------
    print(f"\n저장: {OUT.relative_to(ROOT)}  (전체 조각 {len(w):,}개)\n")

    print("[버린 이유별 조각 수]")
    print(pd.crosstab(w["dataset"], w["drop_reason"].replace("", "(사용)"), margins=True,
                      margins_name="합계").to_string())

    kept = w[w["keep"]]
    print("\n[사용하는 조각: 클래스 × split]")
    print(pd.crosstab(kept["class"], kept["split"], margins=True, margins_name="합계")
          .reindex(columns=["train", "val", "test", "합계"], fill_value=0).to_string())

    files_left = kept.groupby("file_id").size()
    lost = done - set(files_left.index)
    print(f"\n조각이 하나도 남지 않은 파일: {len(lost)}개")
    if lost:
        print(df.loc[sorted(lost)].groupby(["dataset", "class"]).size().to_string())


if __name__ == "__main__":
    main()