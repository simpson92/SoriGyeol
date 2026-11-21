"""YAMNet 그대로(재학습 없이) 웹 알림 규칙으로 평가하고, 기준 점수(threshold)와 변환표를 만든다.

입력 (extract_yamnet.py 결과)
    data/yamnet/{val,test}_windows.csv · _scores.npy · labels.json
    configs/classes.yaml (알림 대상 클래스) · configs/yamnet_map.yaml (클래스별 YAMNet 라벨)

웹 앱과 같은 규칙
    - 클래스 점수 = 묶은 라벨 점수 중 최댓값(max). 비교용으로 합(sum)도 계산
    - 0.5초마다 판단, 최근 3번 중 2번 이상 threshold 넘으면 알림 확정 (alert.js)
    - 같은 소리는 5초 안에 다시 알리지 않음 → 배경 파일의 "시간당 오알림"을 셀 때 사용
    - 조각이 1개뿐인 짧은 파일(1초 미만)은 3중2가 불가능해서 그 1개만 넘으면 확정으로 봄

정하는 방법
    - threshold: val에서 파일 단위 재현율이 --target-recall 이상인 가장 높은 값 → test로 보고
    - 변환표(calibration.json): val의 keep 조각으로 isotonic fit → test로 확인
    - 한국 = AI Hub, 해외 = ESC-50 + UrbanSound8K 로 나눠서도 보고

사용법
    python src/eval_yamnet.py
    python src/eval_yamnet.py --target-recall 0.85 --select-on korean

결과 (data/yamnet/eval/)
    report.md          요약 보고서 (devlog · PR 설명에 옮겨 쓰기)
    thresholds.csv     클래스 × 방식(max/sum) × threshold별 재현율 · 오알림 (val·test, 한국·해외)
    files.csv          파일마다 클래스별 확정 점수
    calibration.json   변환표 (확인 후 configs/calibration.json으로 복사해 PR)
    bg_suspects.csv    배경인데 사이렌·경적 점수가 높은 파일 (직접 들어 보고 manual_exclude 검토)
    misses.csv         추천 threshold에서 놓친 사이렌·경적 파일과 YAMNet이 대신 고른 라벨
    curves.png         threshold별 재현율 · 시간당 오알림 그림
"""
import argparse
import json
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd
import yaml
from sklearn.isotonic import IsotonicRegression
from sklearn.metrics import average_precision_score, roc_auc_score

ROOT = Path(__file__).resolve().parents[1]
YDIR = ROOT / "data" / "yamnet"
OUT = YDIR / "eval"
MANIFEST = ROOT / "data" / "processed" / "manifest.csv"

HOP_S = 0.5
COOLDOWN = 10            # 5초 = 10번 (같은 소리 재알림 금지)
GRID = np.round(np.arange(0.01, 1.51, 0.01), 2)   # 재현율 계산용 (sum은 1을 넘을 수 있음)
GRID_FA = np.round(np.arange(0.05, 1.51, 0.05), 2)  # 시간당 오알림 계산용 (느려서 간격 넓게)
MODES = ("max", "sum")
GROUPS = {"korean": ["aihub"], "overseas": ["esc50", "us8k"], "all": ["aihub", "esc50", "us8k"]}
LEVELS = [{"min": 0.8, "name": "확실"}, {"min": 0.5, "name": "보통"}, {"min": 0.0, "name": "낮음"}]


# ---------------------------------------------------------------- 불러오기
def load_config():
    classes = yaml.safe_load((ROOT / "configs/classes.yaml").read_text(encoding="utf-8"))["classes"]
    mapping = yaml.safe_load((ROOT / "configs/yamnet_map.yaml").read_text(encoding="utf-8"))["mapping"]
    alert = [c["id"] for c in classes if c["enabled"] and c["priority"] > 0 and mapping.get(c["id"])]
    return alert, mapping


def label_index(mapping, alert, labels):
    idx = {}
    for c in alert:
        missing = [l for l in mapping[c] if l not in labels]
        if missing:
            raise SystemExit(f"yamnet_map.yaml의 라벨이 YAMNet에 없어요 ({c}): {missing}")
        idx[c] = [labels.index(l) for l in mapping[c]]
    return idx


def load_split(split, idx):
    w = pd.read_csv(YDIR / f"{split}_windows.csv", low_memory=False)
    s = np.load(YDIR / f"{split}_scores.npy").astype(np.float32)
    if len(w) != len(s):
        raise SystemExit(f"{split}: windows.csv {len(w)}행 ≠ 점수 {len(s)}행")
    for c, ix in idx.items():
        w[f"{c}_max"] = s[:, ix].max(axis=1)
        w[f"{c}_sum"] = s[:, ix].sum(axis=1)
    if MANIFEST.exists():  # 소분류(예: 이륜차경적/차량경적)를 붙여 둠
        m = pd.read_csv(MANIFEST, usecols=["orig_label"], low_memory=False)
        w["orig_label"] = m["orig_label"].reindex(w["file_id"]).to_numpy()
    else:
        w["orig_label"] = ""
    return w, s


# ---------------------------------------------------------------- 알림 규칙
def two_of_three(x: np.ndarray) -> np.ndarray:
    """조각마다 '최근 3번 중 두 번째로 큰 점수' → 이 값이 threshold 이상이면 그 시점에 확정"""
    if len(x) == 1:
        return x.copy()
    p = np.concatenate([[-np.inf, -np.inf], x])
    return np.sort(np.stack([p[:-2], p[1:-1], p[2:]], axis=1), axis=1)[:, 1]


def count_alerts(c2: np.ndarray, th: float) -> int:
    """5초 안 재알림 금지를 지키며 확정 횟수 세기"""
    n, last = 0, -COOLDOWN
    for t in np.flatnonzero(c2 >= th):
        if t - last >= COOLDOWN:
            n, last = n + 1, t
    return n


def file_table(w, alert):
    """파일마다: 클래스·방식별 확정 점수(파일 안 최댓값)와 2중3 시계열"""
    rows, series = [], {}
    for path, g in w.groupby("path16k", sort=False):
        g = g.sort_values("start")
        r = {"path16k": path, "class": g["class"].iat[0], "dataset": g["dataset"].iat[0],
             "orig_label": g["orig_label"].iat[0], "n_windows": len(g),
             "seconds": (len(g) - 1) * HOP_S + 1.0}
        for c in alert:
            for m in MODES:
                c2 = two_of_three(g[f"{c}_{m}"].to_numpy())
                r[f"{c}_{m}"] = float(c2.max())
                series[(path, c, m)] = c2
        rows.append(r)
    return pd.DataFrame(rows), series


def curves(f, series, split, alert):
    """threshold별 재현율 · 배경 오알림"""
    out = []
    for gname, ds in GROUPS.items():
        fg = f[f["dataset"].isin(ds)]
        bg = fg[fg["class"] == "background"]
        hours = bg["seconds"].sum() / 3600
        for c in alert:
            pos = fg[fg["class"] == c]
            for m in MODES:
                conf_pos = pos[f"{c}_{m}"].to_numpy()
                conf_bg = bg[f"{c}_{m}"].to_numpy()
                fa = {th: sum(count_alerts(series[(p, c, m)], th) for p in bg["path16k"]) / hours
                      for th in GRID_FA} if hours else {}
                for th in GRID:
                    out.append({"split": split, "group": gname, "class": c, "mode": m, "threshold": th,
                                "n_files": len(pos), "recall": (conf_pos >= th).mean() if len(pos) else np.nan,
                                "bg_files": len(bg), "bg_file_fa": (conf_bg >= th).mean() if len(bg) else np.nan,
                                "bg_hours": hours, "fa_per_hour": fa.get(th, np.nan)})
    return pd.DataFrame(out)


def fa_at(f, series, alert_th, ds, mode):
    """여러 클래스의 threshold를 같이 쓸 때 배경 시간당 오알림 (클래스 합)"""
    bg = f[(f["class"] == "background") & f["dataset"].isin(ds)]
    hours = bg["seconds"].sum() / 3600
    n = sum(count_alerts(series[(p, c, mode)], th) for c, th in alert_th.items() for p in bg["path16k"])
    return n / hours if hours else np.nan, hours


def pick_threshold(cv, c, m, group, target):
    """val에서 재현율 ≥ target인 가장 높은 threshold. 못 미치면 재현율이 가장 높은 값"""
    v = cv[(cv["split"] == "val") & (cv["group"] == group) & (cv["class"] == c) & (cv["mode"] == m)]
    ok = v[v["recall"] >= target]
    if len(ok):
        return float(ok["threshold"].max()), True
    return float(v.sort_values(["recall", "threshold"], ascending=[False, False])["threshold"].iat[0]), False


def pick_threshold_fa(cv, c, m, group, max_fa):
    """val에서 배경 시간당 오알림 ≤ max_fa인 가장 낮은 threshold (= 그 안에서 재현율 최대)"""
    v = cv[(cv["split"] == "val") & (cv["group"] == group) & (cv["class"] == c) & (cv["mode"] == m)]
    v = v.dropna(subset=["fa_per_hour"])
    ok = v[v["fa_per_hour"] <= max_fa]
    if len(ok):
        return float(ok["threshold"].min()), True
    return float(v["threshold"].max()), False


# ---------------------------------------------------------------- 변환표
def iso_points(x, y):
    iso = IsotonicRegression(y_min=0, y_max=1, out_of_bounds="clip").fit(x.astype(np.float64), y)
    pts = {}
    for a, b in zip(iso.X_thresholds_, iso.y_thresholds_):
        pts[round(float(a), 4)] = round(float(b), 4)  # 반올림으로 x가 겹치면 뒤(큰 y)를 남김 → x가 겹치지 않게
    xs = sorted(pts)
    return iso, {"x": xs, "y": [pts[a] for a in xs]}


def ece(p, y, bins=10):
    e, edges = 0.0, np.linspace(0, 1, bins + 1)
    for lo, hi in zip(edges[:-1], edges[1:]):
        m = (p >= lo) & (p < hi if hi < 1 else p <= hi)
        if m.any():
            e += m.mean() * abs(p[m].mean() - y[m].mean())
    return e


# ---------------------------------------------------------------- 보고서 도우미
def md_table(df, floatfmt="{:.3f}"):
    cols = list(df.columns)
    lines = ["| " + " | ".join(map(str, cols)) + " |", "|" + "---|" * len(cols)]
    for _, r in df.iterrows():
        cells = [floatfmt.format(v) if isinstance(v, (float, np.floating)) and not pd.isna(v) else
                 ("-" if pd.isna(v) else str(v)) for v in r]
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)


def top_labels(scores_rows, labels, k=3):
    mean = scores_rows.mean(axis=0)
    top = np.argsort(mean)[::-1][:k]
    return " · ".join(f"{labels[i]} {mean[i] * 100:.0f}%" for i in top)


def save_plot(cv, alert, chosen):
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        from matplotlib import font_manager
        for name in ("Noto Sans CJK KR", "NanumGothic", "Malgun Gothic"):
            if any(name in f.name for f in font_manager.fontManager.ttflist):
                plt.rcParams["font.family"] = name
                break
    except ImportError:
        return False
    fig, axes = plt.subplots(1, len(alert), figsize=(6 * len(alert), 4), squeeze=False)
    for ax, c in zip(axes[0], alert):
        d = cv[(cv["class"] == c) & (cv["mode"] == "max") & (cv["threshold"] <= 1.0)]
        for (split, group), st in [(("val", "all"), "-"), (("test", "korean"), "-"), (("test", "overseas"), "--")]:
            e = d[(d["split"] == split) & (d["group"] == group)]
            ax.plot(e["threshold"], e["recall"], st, label=f"재현율 {split}·{group}")
        ax2 = ax.twinx()
        e = d[(d["split"] == "test") & (d["group"] == "korean")].dropna(subset=["fa_per_hour"])
        ax2.plot(e["threshold"], e["fa_per_hour"], ":", color="gray", label="시간당 오알림 test·korean")
        ax2.set_ylabel("배경 시간당 오알림"), ax2.set_ylim(bottom=0)
        ax.axvline(chosen[(c, "max")], color="red", lw=0.8)
        ax.axvline(0.3, color="black", lw=0.5, ls="--")
        ax.set_title(f"{c} (max) · 빨간 선 = 재현율 목표 · 점선 = 지금 웹 0.3")
        ax.set_xlabel("threshold"), ax.set_ylabel("파일 단위 재현율"), ax.set_ylim(0, 1.02)
        ax.legend(loc="lower left", fontsize=8), ax2.legend(loc="upper right", fontsize=8)
    fig.tight_layout()
    fig.savefig(OUT / "curves.png", dpi=120)
    return True


# ---------------------------------------------------------------- 본체
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--target-recall", type=float, default=0.90)
    ap.add_argument("--max-fa", type=float, default=1.0,
                    help="두 번째 추천: val 배경 시간당 오알림을 이 값 이하로 (클래스마다)")
    ap.add_argument("--select-on", choices=["all", "korean"], default="all",
                    help="val의 어느 묶음 재현율로 threshold를 고를지")
    ap.add_argument("--top", type=int, default=100, help="bg_suspects.csv에 남길 파일 수 (클래스마다)")
    args = ap.parse_args()

    OUT.mkdir(parents=True, exist_ok=True)
    alert, mapping = load_config()
    labels = json.loads((YDIR / "labels.json").read_text(encoding="utf-8"))
    idx = label_index(mapping, alert, labels)
    print(f"알림 대상: {alert} · 목표 재현율 {args.target_recall} (val · {args.select_on})")

    data, files, series = {}, {}, {}
    for split in ("val", "test"):
        w, s = load_split(split, idx)
        data[split] = (w, s)
        f, se = file_table(w, alert)
        f.insert(0, "split", split)
        files[split], series[split] = f, se
        print(f"[{split}] 파일 {len(f):,}개 · 조각 {len(w):,}개")

    cv = pd.concat([curves(files[sp], series[sp], sp, alert) for sp in ("val", "test")])
    cv.to_csv(OUT / "thresholds.csv", index=False, encoding="utf-8-sig")
    pd.concat(files.values()).to_csv(OUT / "files.csv", index=False, encoding="utf-8-sig")

    R = [f"# YAMNet 기준 평가 (재학습 없음) · {date.today()}", "",
         f"- 알림 대상: {', '.join(alert)} · 규칙: 0.5초마다 최근 0.975초, 3번 중 2번, 같은 소리 5초 재알림 금지",
         f"- threshold 고르는 법 두 가지 (둘 다 val({args.select_on})로 고르고 test로 보고)",
         f"  - **재현율 목표**: 파일 단위 재현율 ≥ {args.target_recall}인 가장 높은 값",
         f"  - **오알림 목표**: 배경 시간당 오알림 ≤ {args.max_fa}회인 가장 낮은 값 (0.05 간격)",
         "- 한국 = AI Hub, 해외 = ESC-50 + UrbanSound8K. 1초 미만 파일은 조각 1개라 그 1개만 넘으면 확정으로 봄", ""]
    for sp in ("val", "test"):
        f = files[sp]
        R.append(f"- {sp}: " + " · ".join(f"{c} {int((f['class'] == c).sum())}" for c in alert + ["background"])
                 + f" 파일 (조각 1개뿐인 파일 {int((f['n_windows'] == 1).sum())}개)")
    R.append("")

    # 1) 창 단위: max vs sum (threshold와 상관없는 비교)
    R += ["## 1. 조각 단위 구분력 (keep 조각, threshold 무관) — max vs 합", ""]
    rows = []
    for sp in ("val", "test"):
        w = data[sp][0]
        for gname, ds in GROUPS.items():
            k = w[w["keep"] & w["dataset"].isin(ds)]
            for c in alert:
                y = (k["class"] == c).to_numpy()
                if y.all() or not y.any():
                    continue
                for m in MODES:
                    rows.append({"split": sp, "묶음": gname, "class": c, "방식": m,
                                 "AUC": roc_auc_score(y, k[f"{c}_{m}"]), "AP": average_precision_score(y, k[f"{c}_{m}"])})
    auc = pd.DataFrame(rows)
    R += [md_table(auc), "", "AUC·AP가 높을수록 그 클래스와 나머지를 잘 가름 (1이 최고).", ""]

    # 2) threshold 고르기
    chosen, reached, chosen_fa, reached_fa = {}, {}, {}, {}
    for c in alert:
        for m in MODES:
            chosen[(c, m)], reached[(c, m)] = pick_threshold(cv, c, m, args.select_on, args.target_recall)
            chosen_fa[(c, m)], reached_fa[(c, m)] = pick_threshold_fa(cv, c, m, args.select_on, args.max_fa)

    def row_at(c, m, th, sp, group):
        e = cv[(cv["split"] == sp) & (cv["group"] == group) & (cv["class"] == c) & (cv["mode"] == m)]
        r = e.iloc[(e["threshold"] - th).abs().argmin()]
        return r

    R += ["## 2. 추천 threshold (val로 고름) 와 test 결과", ""]
    rows = []
    picks = [(c, m, how, th, ok) for c in alert for m in MODES
             for how, th, ok in (("재현율 목표", chosen[(c, m)], reached[(c, m)]),
                                 ("오알림 목표", chosen_fa[(c, m)], reached_fa[(c, m)]))]
    for c, m, how, th, ok in picks:
        r = {"class": c, "방식": m, "기준": how, "threshold": th, "목표 도달": "예" if ok else "아니오"}
        for sp, g in (("val", args.select_on), ("test", "korean"), ("test", "overseas")):
            r[f"재현율 {sp}·{g}"] = row_at(c, m, th, sp, g)["recall"]
        for sp, g in (("val", args.select_on), ("test", "korean")):
            fa, _ = fa_at(files[sp], series[sp], {c: th}, GROUPS[g], m)
            r[f"시간당 오알림 {sp}·{g}"] = fa
        rows.append(r)
    pick = pd.DataFrame(rows)
    R += [md_table(pick), ""]

    # max vs sum 결정 도움: 같은 재현율에서 오알림이 적은 쪽
    better = {}
    for c in alert:
        p = pick[(pick["class"] == c) & (pick["기준"] == "재현율 목표")].set_index("방식")
        col = f"시간당 오알림 val·{args.select_on}"
        a, b = p.loc["max", col], p.loc["sum", col]
        better[c] = "max" if a <= b else "sum"
        R.append(f"- **{c}**: 같은 목표 재현율에서 val 시간당 오알림 max {a:.2f} vs 합 {b:.2f} → **{better[c]}** 쪽이 적음")
    R.append("")

    # 3) 클래스 기준을 다 같이 쓸 때 + 지금 웹(0.3)
    R += ["## 3. 알림 전체 (클래스 기준을 같이 적용, max) — 재현율 목표 · 오알림 목표 · 지금 웹 0.3", ""]
    rows = []
    for name, ths in (("재현율 목표", {c: chosen[(c, "max")] for c in alert}),
                      ("오알림 목표", {c: chosen_fa[(c, "max")] for c in alert}),
                      ("지금 웹 0.3", {c: 0.3 for c in alert})):
        for sp, g in (("val", "all"), ("test", "korean"), ("test", "overseas")):
            fa, hours = fa_at(files[sp], series[sp], ths, GROUPS[g], "max")
            r = {"설정": name, "split·묶음": f"{sp}·{g}", "배경 시간": round(hours, 2), "시간당 오알림": fa}
            for c in alert:
                r[f"{c} 재현율"] = row_at(c, "max", ths[c], sp, g)["recall"]
            rows.append(r)
    R += [md_table(pd.DataFrame(rows)), ""]

    # 소분류별 재현율 (경적 = 이륜차 / 차량 등)
    th_max = {c: chosen[(c, "max")] for c in alert}
    ft = files["test"]
    rows = []
    for c in alert:
        for (ds, ol), g in ft[ft["class"] == c].groupby(["dataset", "orig_label"]):
            rows.append({"class": c, "dataset": ds, "소분류": ol, "파일": len(g),
                         "재현율(추천)": (g[f"{c}_max"] >= th_max[c]).mean(), "재현율(0.3)": (g[f"{c}_max"] >= 0.3).mean()})
    if rows:
        R += ["test 소분류별 재현율 (max)", "", md_table(pd.DataFrame(rows)), ""]

    # 사이렌 파일에서 경적 알림 등 다른 클래스 확정
    rows = []
    for sp in ("test",):
        f = files[sp]
        for true_c in alert + ["background"]:
            g = f[f["class"] == true_c]
            r = {"정답": true_c, "파일": len(g)}
            for c in alert:
                r[f"{c} 확정 비율"] = (g[f"{c}_max"] >= th_max[c]).mean() if len(g) else np.nan
            rows.append(r)
    R += ["test 파일 단위 혼동 (추천 threshold, max) — 정답 클래스별로 각 알림이 확정된 비율", "",
          md_table(pd.DataFrame(rows)), ""]

    # 4) 변환표 (max)
    R += ["## 4. 점수 → 확률 변환표 (yamnet521_max, isotonic)", ""]
    wv, wt = data["val"][0], data["test"][0]
    kv, kt = wv[wv["keep"]], wt[wt["keep"]]
    cal = {"version": 1, "score": "yamnet521_max", "method": "isotonic",
           "eval": {"set": "val", "n": int(kv["path16k"].nunique()), "date": str(date.today())},
           "levels": LEVELS, "classes": {}}
    rows = []
    for c in alert:
        iso, pts = iso_points(kv[f"{c}_max"].to_numpy(), (kv["class"] == c).to_numpy().astype(float))
        cal["classes"][c] = pts
        for g in ("korean", "all"):
            k = kt[kt["dataset"].isin(GROUPS[g])]
            x, y = k[f"{c}_max"].to_numpy(), (k["class"] == c).to_numpy().astype(float)
            p = np.interp(x, pts["x"], pts["y"])  # 웹과 같은 직선 보간
            rows.append({"class": c, "test 묶음": g, "점 개수": len(pts["x"]),
                         "Brier 점수 그대로": np.mean((x - y) ** 2), "Brier 변환 후": np.mean((p - y) ** 2),
                         "ECE 점수 그대로": ece(x, y), "ECE 변환 후": ece(p, y)})
    (OUT / "calibration.json").write_text(json.dumps(cal, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    R += [md_table(pd.DataFrame(rows), "{:.4f}"), "",
          "Brier · ECE는 낮을수록 '표시한 확률'이 실제 비율과 맞음. 변환 후가 더 낮으면 변환표가 효과 있음.",
          "주의: 확률은 val의 클래스 비율(배경이 많음)을 그대로 반영함. 실제 거리의 비율과는 다를 수 있음.", ""]

    # 5) 배경 의심 파일 · 놓친 파일
    sus, miss = [], []
    for sp in ("val", "test"):
        w, s = data[sp]
        f = files[sp]
        rows_of = w.groupby("path16k").indices
        for c in alert:
            bg = f[f["class"] == "background"].nlargest(args.top, f"{c}_max")
            for _, r in bg.iterrows():
                g = w.iloc[rows_of[r["path16k"]]]
                i = g[f"{c}_max"].idxmax()
                sus.append({"split": sp, "의심 클래스": c, "확정 점수": round(r[f"{c}_max"], 3),
                            "추천 기준 넘음": r[f"{c}_max"] >= th_max[c], "dataset": r["dataset"],
                            "orig_label": r["orig_label"], "가장 높은 조각 시작(초)": w.at[i, "start"],
                            "그 조각 top3": top_labels(s[[i]], labels), "path16k": r["path16k"]})
            for _, r in f[(f["class"] == c) & (f[f"{c}_max"] < th_max[c])].iterrows():
                g = w.iloc[rows_of[r["path16k"]]]
                gk = g[g["keep"]] if g["keep"].any() else g
                miss.append({"split": sp, "class": c, "확정 점수": round(r[f"{c}_max"], 3), "dataset": r["dataset"],
                             "orig_label": r["orig_label"], "조각 수": r["n_windows"],
                             "평균 top3": top_labels(s[gk.index], labels), "path16k": r["path16k"]})
    sus, miss = pd.DataFrame(sus), pd.DataFrame(miss)
    sus.to_csv(OUT / "bg_suspects.csv", index=False, encoding="utf-8-sig")
    miss.to_csv(OUT / "misses.csv", index=False, encoding="utf-8-sig")

    R += ["## 5. 직접 확인할 파일", ""]
    if len(sus):
        n_over = sus.groupby(["split", "의심 클래스"])["추천 기준 넘음"].sum()
        R.append("- 배경인데 추천 기준을 넘은 파일 (bg_suspects.csv 위쪽부터 들어 보기): "
                 + " · ".join(f"{sp} {c} {int(v)}개" for (sp, c), v in n_over.items()))
    if len(miss):
        R.append("- 추천 기준에서 놓친 파일 (misses.csv): "
                 + " · ".join(f"{sp} {c} {n}개" for (sp, c), n in miss.groupby(["split", "class"]).size().items()))
        top1 = miss["평균 top3"].str.split(" · ").str[0].str.rsplit(" ", n=1).str[0]
        for c in alert:
            t = top1[miss["class"] == c].value_counts().head(5)
            if len(t):
                R.append(f"  - 놓친 {c} 파일에서 YAMNet이 가장 높게 준 라벨: "
                         + " · ".join(f"{k} {v}" for k, v in t.items()))
    R.append("")

    if save_plot(cv, alert, chosen):
        R += ["## 6. 그림", "", "![threshold별 재현율과 오알림](curves.png)", ""]

    R += ["## 다음 할 일", "",
          "- 추천 threshold를 classes.yaml에 넣고 `python src/export_web_classes.py` → config/ 브랜치 PR",
          "- calibration.json을 configs/로 복사해 PR (하민 님 H3에서 웹 표시)",
          "- bg_suspects.csv 위쪽 파일을 직접 들어 보고, 진짜 사이렌·경적이면 configs/manual_exclude.csv 검토", ""]
    (OUT / "report.md").write_text("\n".join(R), encoding="utf-8")

    print("\n" + md_table(pick))
    print(f"\n저장: {OUT.relative_to(ROOT)}/ (report.md · thresholds.csv · files.csv · calibration.json · "
          "bg_suspects.csv · misses.csv · curves.png)")


if __name__ == "__main__":
    main()
