"""YAMNet을 웹 앱과 같은 방식으로 돌려, 조각마다 점수 521개와 임베딩 1,024개를 저장한다.

웹 앱(web/classifier.js)과 맞춘 것
    - 0.5초마다 판단, 입력 = 최근 0.975초(15,600샘플), MediaPipe 결과 중 첫 조각만
    - windows.csv의 1초 조각(시작 s)마다 그 조각의 뒤쪽 0.975초 [s+0.025, s+1.0)를 넣음
      → windows.csv 행과 1:1로 맞음 (keep · drop_reason 그대로 사용 가능)
    - 1초보다 짧은 파일은 make_windows.py처럼 뒤를 0으로 채워 1초로 만든 뒤 뒤쪽 0.975초
    - 임베딩: l2_normalize=False, quantize=False (web/lab/embedder.html과 같음)

MediaPipe 버전
    - 0.10.21 사용. 1.2.3 Python은 임베딩 모델(yamnet_embedding_metadata.tflite)을 못 읽음
    - 0.10.21은 numpy 1.x를 요구 → 학습용 .venv와 따로 .venv-mp에 설치 (docs 참고)
    - 같은 16kHz 입력이면 웹과 임베딩 값이 같음 (src/check_yamnet_web.py, 11-22 확인)

사용법 (make_windows.py 다음에)
    python src/extract_yamnet.py                       # val, test 전체 조각
    python src/extract_yamnet.py --splits train --keep-only   # 분류기 학습용 (keep 조각만)
    python src/extract_yamnet.py --limit-files 20      # 빠른 시험 (split마다 파일 20개)

결과 (data/yamnet/)
    {split}_windows.csv   windows.csv에서 고른 행 (저장 순서 = 아래 배열의 행 순서)
    {split}_scores.npy    float16 [조각 수, 521]   YAMNet 라벨 점수
    {split}_emb.npy       float16 [조각 수, 1024]  YAMNet 임베딩
    labels.json           521개 라벨 이름 (점수 열 순서)
    meta.json             실행 조건 기록 (mediapipe 버전, 모델 파일 크기, 날짜 등)
"""
import argparse
import json
import multiprocessing as mp
import os
import time
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
import soundfile as sf
from tqdm import tqdm

ROOT = Path(__file__).resolve().parents[1]
WINDOWS = ROOT / "data" / "processed" / "windows.csv"
OUT = ROOT / "data" / "yamnet"
CLASSIFIER = ROOT / "models" / "yamnet" / "yamnet.tflite"
EMBEDDER = ROOT / "models" / "yamnet" / "yamnet_embedding_metadata.tflite"

SR = 16000
WIN = 16000          # make_windows.py의 1초 조각
CLIP = 15600         # 웹이 실제로 넣는 0.975초
OFFSET = WIN - CLIP  # 400샘플 = 0.025초
N_LABELS, N_EMB = 521, 1024

_clf = _emb = None   # 작업 프로세스마다 하나씩


def _init_worker():
    global _clf, _emb
    os.environ.setdefault("GLOG_minloglevel", "2")
    from mediapipe.tasks.python.audio import audio_classifier as ac
    from mediapipe.tasks.python.audio import audio_embedder as ae
    from mediapipe.tasks.python.core.base_options import BaseOptions

    _clf = ac.AudioClassifier.create_from_options(ac.AudioClassifierOptions(
        base_options=BaseOptions(model_asset_path=str(CLASSIFIER)), max_results=-1))
    _emb = ae.AudioEmbedder.create_from_options(ae.AudioEmbedderOptions(
        base_options=BaseOptions(model_asset_path=str(EMBEDDER)), l2_normalize=False, quantize=False))


def clips_of(y: np.ndarray, starts: np.ndarray) -> list:
    """조각 시작(초)마다 웹과 같은 0.975초 입력"""
    if len(y) < WIN:
        y = np.pad(y, (0, WIN - len(y)))
    out = []
    for s in starts:
        a = int(round(s * SR)) + OFFSET
        c = y[a:a + CLIP]
        if len(c) < CLIP:  # 반올림 오차 대비 (보통 안 생김)
            c = np.pad(c, (0, CLIP - len(c)))
        out.append(c)
    return out


def run_file(job):
    """파일 하나의 조각들 → (점수, 임베딩, 라벨 이름 목록)"""
    path, starts = job
    from mediapipe.tasks.python.components.containers.audio_data import AudioData

    y, sr = sf.read(ROOT / path, dtype="float32", always_2d=True)
    if sr != SR:
        raise ValueError(f"{path}: {sr}Hz (16kHz 파일이어야 함)")
    y = y.mean(axis=1)

    scores = np.zeros((len(starts), N_LABELS), np.float16)
    embs = np.zeros((len(starts), N_EMB), np.float16)
    names = None
    for i, c in enumerate(clips_of(y, starts)):
        data = AudioData.create_from_array(c, SR)
        cats = _clf.classify(data)[0].classifications[0].categories
        for cat in cats:
            scores[i, cat.index] = cat.score
        if names is None:
            names = {cat.index: cat.category_name for cat in cats}
        embs[i] = _emb.embed(data)[0].embeddings[0].embedding
    return scores, embs, names


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--splits", nargs="+", default=["val", "test"])
    ap.add_argument("--keep-only", action="store_true", help="keep=True 조각만 (train용)")
    ap.add_argument("--workers", type=int, default=max(1, (os.cpu_count() or 2) - 1))
    ap.add_argument("--limit-files", type=int, default=0, help="split마다 앞에서 N개 파일만 (시험용)")
    args = ap.parse_args()

    for p in (WINDOWS, CLASSIFIER, EMBEDDER):
        if not p.exists():
            raise SystemExit(f"파일이 없어요: {p.relative_to(ROOT)}")
    import mediapipe
    print(f"mediapipe {mediapipe.__version__} · 작업 프로세스 {args.workers}개")

    OUT.mkdir(parents=True, exist_ok=True)
    w = pd.read_csv(WINDOWS, low_memory=False)
    labels = None

    for split in args.splits:
        t0 = time.time()
        d = w[w["split"] == split]
        if args.keep_only:
            d = d[d["keep"]]
        if args.limit_files:
            d = d[d["path16k"].isin(d["path16k"].drop_duplicates().head(args.limit_files))]
        d = d.sort_values(["path16k", "start"], kind="stable").reset_index(drop=True)
        groups = [(p, g["start"].to_numpy()) for p, g in d.groupby("path16k", sort=False)]
        print(f"\n[{split}] 파일 {len(groups):,}개 · 조각 {len(d):,}개")

        scores = np.zeros((len(d), N_LABELS), np.float16)
        embs = np.zeros((len(d), N_EMB), np.float16)
        offsets = np.cumsum([0] + [len(s) for _, s in groups])

        ctx = mp.get_context("spawn")
        with ctx.Pool(args.workers, initializer=_init_worker) as pool:
            it = pool.imap(run_file, groups, chunksize=4)
            for k, (sc, em, names) in enumerate(tqdm(it, total=len(groups), unit="file")):
                scores[offsets[k]:offsets[k + 1]] = sc
                embs[offsets[k]:offsets[k + 1]] = em
                if labels is None and names:
                    labels = [names[i] for i in range(N_LABELS)]

        d.to_csv(OUT / f"{split}_windows.csv", index=False, encoding="utf-8")
        np.save(OUT / f"{split}_scores.npy", scores)
        np.save(OUT / f"{split}_emb.npy", embs)
        mins = (time.time() - t0) / 60
        print(f"저장: data/yamnet/{split}_*.npy · {split}_windows.csv ({mins:.1f}분)")

        # 확인: 점수·임베딩이 비어 있는 조각, float16 범위를 넘은 값 (모두 0개가 정상)
        print(f"  점수 전부 0 {int((~scores.any(axis=1)).sum())}개 · 임베딩 전부 0 {int((~embs.any(axis=1)).sum())}개 · "
              f"inf {int(np.isinf(embs).sum() + np.isinf(scores).sum())}개 (모두 0개가 정상)")

    if labels:
        (OUT / "labels.json").write_text(json.dumps(labels, ensure_ascii=False, indent=0), encoding="utf-8")
    meta_path = OUT / "meta.json"
    meta = json.loads(meta_path.read_text(encoding="utf-8")) if meta_path.exists() else {}
    for split in args.splits:
        meta[split] = {
            "date": datetime.now().isoformat(timespec="seconds"),
            "mediapipe": mediapipe.__version__,
            "keep_only": args.keep_only,
            "limit_files": args.limit_files,
            "classifier_bytes": CLASSIFIER.stat().st_size,
            "embedder_bytes": EMBEDDER.stat().st_size,
            "clip_samples": CLIP, "offset_samples": OFFSET,
        }
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
