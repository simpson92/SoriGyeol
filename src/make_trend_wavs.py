"""가까워짐/멀어짐 시험용 소리 파일을 만든다 (웹 web/approach.js 확인용).

ESC-50의 사이렌 녹음을 이어 붙인 뒤 소리 크기를 일정하게 키우거나 줄인다.
PC Chrome의 가짜 마이크(--use-file-for-fake-audio-capture)로 틀어서 화면을 확인한다.

    python src/make_trend_wavs.py                 # → /mnt/c/temp/ 에 저장
    python src/make_trend_wavs.py --out data/tmp  # 다른 폴더에 저장

만드는 파일 (모두 끝에 3초 무음. 가짜 마이크는 파일을 반복 재생하므로 반복 경계를 나눔)
    approach.wav  -24dB에서 시작해 초당 +3dB로 8초 커짐 → 2초 유지      → '가까워지는 중'이 떠야 함
    recede.wav    2초 유지 → 초당 -4dB로 7초 작아짐                         → '멀어지는 중'이 떠야 함
    passby.wav    초당 +3dB로 8초 커짐 → 1초 유지 → 초당 -4dB로 6초 작아짐 → 가까워짐 → 멀어짐 순서
    steady.wav    12초 같은 크기                                             → 아무것도 안 떠야 함
"""

import argparse
import csv
import wave
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
ESC50 = ROOT / "data" / "raw" / "esc50" / "ESC-50-master"
SR = 16000
PEAK_RMS_DBFS = -18.0  # 가장 클 때의 평균 크기 (클리핑 없이 여유를 둠)


def read_wav(path: Path) -> np.ndarray:
    with wave.open(str(path), "rb") as w:
        sr, ch, width = w.getframerate(), w.getnchannels(), w.getsampwidth()
        raw = w.readframes(w.getnframes())
    if width != 2:
        raise ValueError(f"16비트 PCM만 읽을 수 있어요: {path}")
    x = np.frombuffer(raw, dtype="<i2").astype(np.float32) / 32768
    if ch > 1:
        x = x.reshape(-1, ch).mean(axis=1)
    if sr != SR:  # 단순 선형 보간으로 16kHz로 맞춤 (시험용이라 충분)
        n = int(len(x) * SR / sr)
        x = np.interp(np.linspace(0, len(x) - 1, n), np.arange(len(x)), x).astype(np.float32)
    return x


def siren_bed(seconds: float) -> np.ndarray:
    """ESC-50 사이렌 녹음을 같은 크기로 맞춰 이어 붙인다."""
    meta = ESC50 / "meta" / "esc50.csv"
    with open(meta, encoding="utf-8") as f:
        files = sorted(r["filename"] for r in csv.DictReader(f) if r["category"] == "siren")
    if not files:
        raise SystemExit(f"사이렌 파일을 찾지 못했어요: {meta}")

    parts, total = [], 0
    for name in files:
        x = read_wav(ESC50 / "audio" / name)
        loud = np.flatnonzero(np.abs(x) > 1e-4)
        if len(loud) == 0:
            continue
        x = x[loud[0]: loud[-1] + 1]  # 앞뒤 완전 무음만 잘라냄
        rms = np.sqrt(np.mean(x ** 2)) + 1e-9
        parts.append(x / rms)  # 녹음마다 크기가 달라 생기는 가짜 변화를 없앰
        total += len(x)
        if total >= seconds * SR:
            break
    bed = np.concatenate(parts)
    if len(bed) < seconds * SR:  # 그래도 짧으면 반복
        bed = np.tile(bed, int(np.ceil(seconds * SR / len(bed))))
    return bed[: int(seconds * SR)]


def envelope(segments: list[tuple[float, float, float]]) -> np.ndarray:
    """[(초, 시작 dB, 끝 dB), ...] → 샘플별 이득(배수)."""
    db = np.concatenate([np.linspace(a, b, int(s * SR), endpoint=False) for s, a, b in segments])
    return (10 ** (db / 20)).astype(np.float32)


def write_wav(path: Path, x: np.ndarray) -> None:
    y = np.clip(x, -1, 1)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((y * 32767).astype("<i2").tobytes())


PLANS = {
    "approach": [(8, -24, 0), (2, 0, 0)],
    "recede": [(2, 0, 0), (7, 0, -28)],
    "passby": [(8, -24, 0), (1, 0, 0), (6, 0, -24)],
    "steady": [(12, -6, -6)],
}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="/mnt/c/temp", help="저장할 폴더")
    args = ap.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    peak = 10 ** (PEAK_RMS_DBFS / 20)
    for name, plan in PLANS.items():
        gain = envelope(plan)
        bed = siren_bed(len(gain) / SR)
        x = bed * gain * peak
        x = np.concatenate([x, np.zeros(3 * SR, dtype=np.float32)])  # 반복 경계용 무음
        write_wav(out / f"{name}.wav", x)
        print(f"{out / f'{name}.wav'}  {len(x) / SR:.0f}초")


if __name__ == "__main__":
    main()
