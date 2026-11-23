"""웹 임베딩 실험 페이지(web/lab/embedder.html)와 같은 조건으로 Python에서 YAMNet을 돌려
결과가 같은지 대조한다.

웹과 맞춘 조건
- 16kHz 모노로 읽기 (채널 평균)
- A) 앞 1초(16,000샘플)만 넣어 임베딩 + 분류 top3
- B) 파일 전체 임베딩 → 창 개수와 시작 시각(ms)
- 임베딩: l2_normalize=False, quantize=False

실행
    python src/check_yamnet_web.py data/test/siren_16k.wav

대조 결과 (11-22, 집 PC · mediapipe 0.10.21 · Chrome 157)
- 이미 16kHz인 siren_16k.wav → 웹과 Python 임베딩 값 같음 (L2 8.8047 / 8.8045)
- 44.1kHz 원본 siren.wav → 약 2% 다름. 원인 = 16kHz 변환 방식 차이
  (브라우저 자체 변환 vs librosa soxr_hq. 학습 데이터는 resample_16k.py = librosa 쪽)
- mediapipe 1.2.3 Python은 이 임베딩 모델을 못 읽음 → 0.10.21 사용
"""
import argparse
import time
from pathlib import Path

import numpy as np
import soundfile as sf
from mediapipe.tasks.python.audio import audio_classifier as ac
from mediapipe.tasks.python.audio import audio_embedder as ae
from mediapipe.tasks.python.components.containers.audio_data import AudioData
from mediapipe.tasks.python.core.base_options import BaseOptions

SR = 16000
ROOT = Path(__file__).resolve().parents[1]
CLASSIFIER = ROOT / "models/yamnet/yamnet.tflite"
# 웹 실험 페이지와 같은 후보 2개 (앞에서부터 되는 것 사용)
EMBEDDERS = [ROOT / "models/yamnet/yamnet_embedding_metadata.tflite",
             ROOT / "models/yamnet/yamnet_embedding.tflite"]


def load_16k_mono(path):
    x, sr = sf.read(path, dtype="float32", always_2d=True)
    print(f"[원본] {sr}Hz · 채널 {x.shape[1]}개 · {len(x) / sr:.2f}초")
    x = x.mean(axis=1)
    if sr != SR:
        import librosa
        x = librosa.resample(x, orig_sr=sr, target_sr=SR)
        print("  → 16kHz로 변환함 (브라우저와 변환 방식이 달라 값이 조금 다를 수 있음)")
    return x.astype(np.float32)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("wav")
    args = ap.parse_args()

    import mediapipe
    print(f"[버전] mediapipe {mediapipe.__version__}")
    if not CLASSIFIER.exists():
        raise SystemExit(f"모델 파일이 없어요: {CLASSIFIER}")

    embedder = None
    for p in EMBEDDERS:
        if not p.exists():
            print(f"[임베딩 모델] 없음: {p.name}")
            continue
        try:
            embedder = ae.AudioEmbedder.create_from_options(ae.AudioEmbedderOptions(
                base_options=BaseOptions(model_asset_path=str(p)),
                l2_normalize=False, quantize=False))
            print(f"[임베딩 모델] 사용: {p.name}")
            break
        except Exception as e:
            print(f"[임베딩 모델] 실패: {p.name} → {str(e).strip().splitlines()[-1][:200]}")
    if embedder is None:
        raise SystemExit("임베딩 모델을 하나도 못 불러왔어요 → 화면을 Claude에게 보여 주세요")
    classifier = ac.AudioClassifier.create_from_options(ac.AudioClassifierOptions(
        base_options=BaseOptions(model_asset_path=str(CLASSIFIER)), max_results=3))

    x = load_16k_mono(args.wav)
    print(f"[파일] {Path(args.wav).name} · {len(x) / SR:.2f}초")

    # A) 앞 1초
    one = AudioData.create_from_array(x[:SR], SR)
    t = time.perf_counter()
    e1 = embedder.embed(one)
    t_embed = (time.perf_counter() - t) * 1000
    t = time.perf_counter()
    c1 = classifier.classify(one)
    t_class = (time.perf_counter() - t) * 1000

    v = e1[0].embeddings[0].embedding
    print(f"\n[1초 창] 임베딩 결과 {len(e1)}개 · 길이 {len(v)} · 걸린 시간 {t_embed:.1f}ms")
    print("  앞 5개 값: " + ", ".join(f"{a:.4f}" for a in v[:5]))
    print(f"  L2 크기: {np.linalg.norm(v):.4f}")
    top = c1[0].classifications[0].categories
    print(f"[1초 창] 분류 top3 ({t_class:.1f}ms): "
          + " · ".join(f"{c.category_name} {c.score * 100:.0f}%" for c in top))

    # B) 파일 전체
    all_ = embedder.embed(AudioData.create_from_array(x, SR))
    print(f"\n[파일 전체] 임베딩 {len(all_)}개 (Python 0.10.21은 시작 시각을 비워 줌, 웹은 0, 975, 1950 …)")

    # 웹 실험 페이지 결과와 비교 (siren_16k.wav 기준, 11-22)
    web5, web_l2 = np.array([0.0000, 1.6266, 0.1824, 0.0000, 0.0000]), 8.8047
    diff = np.abs(np.asarray(v[:5]) - web5).max()
    print("\n[웹과 비교 · siren_16k.wav 기준] 웹: 앞 5개 0.0000, 1.6266, 0.1824, 0.0000, 0.0000 · "
          f"L2 {web_l2} · top3 Opera 11% · Alarm 8% · Police car (siren) 8% · 전체 6개")
    print(f"  앞 5개 최대 차이 {diff:.4f} · L2 차이 {abs(np.linalg.norm(v) - web_l2):.4f}")
    print("  판정: " + ("같음 ✅" if diff < 0.01 else "다름 (siren_16k.wav가 아니면 다른 게 정상)"))


if __name__ == "__main__":
    main()