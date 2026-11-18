"""학습에 쓰는 소리 파일을 16kHz 모노로 변환해 저장한다.

- 스테레오는 두 채널을 평균해 모노로 만든다.
- 소리 크기는 바꾸지 않는다 (정규화 안 함). 크기 정보가 조각 고르기 · 접근 판단에 쓰이기 때문.
- 이미 변환된 파일은 건너뛰므로, 중간에 멈춰도 다시 실행하면 이어서 한다.

사용법 (make_split.py 다음에):
    python src/resample_16k.py               # 학습 사용(use=True) 파일만
    python src/resample_16k.py --workers 4   # 동시에 처리할 개수 (기본: CPU 수 - 1)

결과:
    data/raw/<경로>.wav  →  data/processed/audio16k/<같은 경로>.wav  (16kHz · 모노 · 16bit)
"""
import argparse
import os
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import librosa
import numpy as np
import pandas as pd
import soundfile as sf
from tqdm import tqdm

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "data" / "processed" / "manifest.csv"
RAW = ROOT / "data" / "raw"
OUT = ROOT / "data" / "processed" / "audio16k"
SR = 16000


def out_path(path: str) -> Path:
    """data/raw/... → data/processed/audio16k/... (manifest의 path 기준)"""
    return OUT / (ROOT / path).relative_to(RAW)


def convert(path: str) -> str:
    dst = out_path(path)
    if dst.exists():
        return "skip"
    try:
        y, sr = sf.read(ROOT / path, dtype="float32", always_2d=True)
        y = y.mean(axis=1)                                   # 모노
        if sr != SR:
            y = librosa.resample(y, orig_sr=sr, target_sr=SR, res_type="soxr_hq")
        y = np.clip(y, -1.0, 1.0)
        dst.parent.mkdir(parents=True, exist_ok=True)
        tmp = dst.with_name(dst.stem + ".tmp.wav")           # 쓰다가 멈춰도 깨진 파일이 남지 않게
        sf.write(tmp, y, SR, subtype="PCM_16")
        tmp.replace(dst)
        return "done"
    except Exception as e:
        return f"error: {e}"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=max(1, (os.cpu_count() or 2) - 1))
    args = ap.parse_args()

    df = pd.read_csv(MANIFEST, low_memory=False)
    paths = df.loc[df["use"], "path"].tolist()
    print(f"변환 대상 {len(paths):,}개 · 동시 처리 {args.workers}개")

    results = []
    with ProcessPoolExecutor(args.workers) as ex:
        for r in tqdm(ex.map(convert, paths, chunksize=32), total=len(paths), unit="file"):
            results.append(r)

    res = pd.Series(results)
    print(f"\n새로 변환 {(res == 'done').sum():,}개 · 이미 있어서 건너뜀 {(res == 'skip').sum():,}개 · "
          f"오류 {res.str.startswith('error').sum()}개")
    for p, r in zip(paths, results):
        if r.startswith("error"):
            print("  ", p, r)

    size = sum(f.stat().st_size for f in OUT.rglob("*.wav")) / 1e9
    print(f"저장 위치: {OUT.relative_to(ROOT)}  ({size:.1f} GB)")


if __name__ == "__main__":
    main()