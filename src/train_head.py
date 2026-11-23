"""YAMNet 임베딩(1,024개) 위에 작은 분류기(사이렌 · 경적 · 배경)를 학습하고, 웹 알림 규칙으로 평가한다.

입력 (extract_yamnet.py 결과)
    data/yamnet/train_windows.csv · train_emb.npy   (--splits train --keep-only 로 추출)
    data/yamnet/{val,test}_windows.csv · _emb.npy · _scores.npy · labels.json
    configs/classes.yaml (클래스 순서 · 알림 대상) · configs/yamnet_map.yaml (비교용 YAMNet 그대로 점수)

모델 두 가지를 같은 조건으로 학습
    logreg  1024 → 3            (로지스틱 회귀, 가장 단순)
    mlp     1024 → 256 → 3      (은닉층 1개 · ReLU · dropout)
    - 입력은 train 평균 · 표준편차로 맞춤 (내보낼 때 첫 층에 합쳐 넣어서 웹은 곱하기 · 더하기만 하면 됨)
    - 클래스 수가 달라서(배경이 훨씬 많음) 적은 클래스에 가중치를 더 줌
    - val keep 조각의 손실이 5번 연속 나아지지 않으면 멈추고 가장 좋았던 상태를 씀

평가는 eval_yamnet.py와 같은 규칙
    - 0.5초마다 최근 0.975초 → 클래스 확률, 최근 3번 중 2번 threshold 이상이면 확정, 같은 소리 5초 재알림 금지
    - threshold 두 가지를 val(all)로 고르고 test로 보고: 재현율 목표 / 오알림 목표
    - 같은 표에 YAMNet 그대로(max)와 지금 웹 기준(classes.yaml threshold)을 같이 넣어 비교
    - 어떤 모델을 쓸지는 val 결과로 추천 (test는 확인용)

사용법
    python src/train_head.py                        # 학습 데이터 = 한국 + 해외 (기본)
    python src/train_head.py --train-on korean      # 비교 실험: 한국만 / overseas = 해외만

결과 (data/yamnet/head/<train-on>/)
    report.md                요약 보고서 (devlog · PR 설명에 옮겨 쓰기)
    head_logreg.json         웹용 가중치 (임시 형식 — 하민 님 H2 형식이 나오면 맞춤)
    head_mlp.json
    calibration_logreg.json  점수 → 확률 변환표 (score: head_v1)
    calibration_mlp.json
    history.csv              epoch별 손실
    files.csv                test 파일마다 모델별 확정 점수
"""
import argparse
import json
import time
from datetime import date

import numpy as np
import pandas as pd
import torch
import yaml
from sklearn.metrics import roc_auc_score
from torch import nn

import eval_yamnet as ev  # 같은 알림 규칙(two_of_three · count_alerts) · 변환표 도구를 그대로 씀

ROOT, YDIR = ev.ROOT, ev.YDIR
# 분류기 확률은 1 근처에 몰려 있어서 0.99 위도 촘촘하게 봄 (0.99에서 멈추면 더 높은 기준을 못 봄)
TOP = [0.991, 0.992, 0.993, 0.994, 0.995, 0.996, 0.997, 0.998, 0.999, 0.9995, 0.9999]
GRID = np.unique(np.round(np.concatenate([np.arange(0.01, 0.995, 0.01), TOP]), 4))      # 재현율 계산용
GRID_FA = np.unique(np.round(np.concatenate([np.arange(0.02, 0.975, 0.02),
                                             np.arange(0.98, 0.9905, 0.002), TOP]), 4))  # 시간당 오알림 계산용
GROUPS = ev.GROUPS
SEED = 42


# ---------------------------------------------------------------- 불러오기
def load_classes():
    classes = yaml.safe_load((ROOT / "configs/classes.yaml").read_text(encoding="utf-8"))["classes"]
    names = [c["id"] for c in classes if c["enabled"]]                      # 모델 출력 순서
    alert = [c["id"] for c in classes if c["enabled"] and c["priority"] > 0]  # 알림 대상
    web_th = {c["id"]: c.get("threshold", 0.3) for c in classes if c["id"] in alert}
    return names, alert, web_th


def load_emb(split, names):
    w = pd.read_csv(YDIR / f"{split}_windows.csv", low_memory=False)
    e = np.load(YDIR / f"{split}_emb.npy")
    if len(w) != len(e):
        raise SystemExit(f"{split}: windows.csv {len(w)}행 ≠ 임베딩 {len(e)}행")
    m = w["class"].isin(names).to_numpy()
    w = w[m].reset_index(drop=True)
    w["y"] = w["class"].map({c: i for i, c in enumerate(names)}).astype(int)
    return w, e[m]


# ---------------------------------------------------------------- 학습
def make_model(hidden, n_in, n_out, dropout):
    if hidden == 0:
        return nn.Linear(n_in, n_out)
    return nn.Sequential(nn.Linear(n_in, hidden), nn.ReLU(), nn.Dropout(dropout), nn.Linear(hidden, n_out))


def train_one(name, hidden, Xtr, ytr, Xva, yva, n_cls, args, dev):
    torch.manual_seed(SEED)
    Xt = torch.from_numpy(Xtr).to(dev).float()
    mean, std = Xt.mean(0), Xt.std(0) + 1e-6
    Xt = (Xt - mean) / std
    yt = torch.from_numpy(np.array(ytr, dtype=np.int64)).to(dev)
    Xv = (torch.from_numpy(Xva).to(dev).float() - mean) / std
    yv = torch.from_numpy(np.array(yva, dtype=np.int64)).to(dev)

    counts = torch.bincount(yt, minlength=n_cls).float()
    cw = counts.sum() / (n_cls * counts)                 # 적은 클래스에 큰 가중치
    lossf = nn.CrossEntropyLoss(weight=cw)
    model = make_model(hidden, Xt.shape[1], n_cls, args.dropout).to(dev)
    opt = torch.optim.Adam(model.parameters(), lr=args.lr, weight_decay=args.weight_decay)

    best, best_state, best_ep, wait, hist = float("inf"), None, 0, 0, []
    for ep in range(1, args.epochs + 1):
        model.train()
        perm = torch.randperm(len(Xt), device=dev)
        tot = 0.0
        for i in range(0, len(Xt), args.batch):
            b = perm[i:i + args.batch]
            opt.zero_grad()
            loss = lossf(model(Xt[b]), yt[b])
            loss.backward()
            opt.step()
            tot += loss.item() * len(b)
        model.eval()
        with torch.no_grad():
            vl = sum(lossf(model(Xv[i:i + 8192]), yv[i:i + 8192]).item() * len(yv[i:i + 8192])
                     for i in range(0, len(Xv), 8192)) / len(Xv)
        hist.append({"model": name, "epoch": ep, "train_loss": tot / len(Xt), "val_loss": vl})
        if vl < best - 1e-4:
            best, best_ep, wait = vl, ep, 0
            best_state = {k: v.detach().clone() for k, v in model.state_dict().items()}
        else:
            wait += 1
            if wait >= args.patience:
                break
    model.load_state_dict(best_state)
    model.eval()
    info = {"best_epoch": best_ep, "epochs_run": ep, "val_loss": best,
            "class_weight": [round(float(x), 3) for x in cw]}
    return model, mean, std, hist, info


def predict(model, X, mean, std, dev):
    out = []
    with torch.no_grad():
        for i in range(0, len(X), 16384):
            x = (torch.from_numpy(X[i:i + 16384]).to(dev).float() - mean) / std
            out.append(torch.softmax(model(x), dim=1).cpu().numpy())
    return np.concatenate(out)


# ---------------------------------------------------------------- 웹용으로 내보내기
def export_layers(model, mean, std):
    """정규화((x - mean) / std)를 첫 층에 합쳐서 dense 층 목록으로: y = W x + b"""
    lin = [m for m in (model if isinstance(model, nn.Sequential) else [model]) if isinstance(m, nn.Linear)]
    mean, std = mean.cpu().double().numpy(), std.cpu().double().numpy()
    layers = []
    for i, m in enumerate(lin):
        W = m.weight.detach().cpu().double().numpy()
        b = m.bias.detach().cpu().double().numpy()
        if i == 0:
            W = W / std            # 각 입력 열을 std로 나눔
            b = b - W @ mean       # 평균 빼기를 편향으로
        layers.append({"in": W.shape[1], "out": W.shape[0],
                       "activation": "softmax" if i == len(lin) - 1 else "relu", "W": W, "b": b})
    return layers


def forward_np(layers, X):
    h = X.astype(np.float64)
    for L in layers:
        h = h @ np.asarray(L["W"]).T + np.asarray(L["b"])
        if L["activation"] == "relu":
            h = np.maximum(h, 0)
        else:
            h = np.exp(h - h.max(axis=1, keepdims=True))
            h = h / h.sum(axis=1, keepdims=True)
    return h


def to_json(layers, names, name, info, train_on, n_train):
    r = lambda a: [float(f"{v:.6g}") for v in np.ravel(a)]
    return {
        "version": 1, "name": "head_v1", "model": name,
        "note": "임시 형식 — 하민 님 H2(분류기 가중치 형식 문서)가 나오면 맞춤",
        "input": {"type": "yamnet_embedding", "dim": 1024, "window_s": 0.975, "l2_normalize": False,
                  "normalize": "첫 층에 합쳐 넣음 (입력 임베딩을 그대로 넣으면 됨)"},
        "classes": names,
        "layers": [{"in": L["in"], "out": L["out"], "activation": L["activation"],
                    "W": [r(row) for row in L["W"]], "b": r(L["b"])} for L in layers],
        "train": {"date": str(date.today()), "train_on": train_on, "n_windows": int(n_train), **info},
    }


# ---------------------------------------------------------------- 평가 (eval_yamnet.py와 같은 규칙)
def file_series(w, cols):
    """파일마다 클래스별 '최근 3번 중 두 번째로 큰 값' 시계열과 확정 점수(최댓값)"""
    rows, series = [], {}
    w = w.sort_values(["path16k", "start"])
    for path, g in w.groupby("path16k", sort=False):
        r = {"path16k": path, "class": g["class"].iat[0], "dataset": g["dataset"].iat[0],
             "orig_label": g["orig_label"].iat[0], "seconds": (len(g) - 1) * ev.HOP_S + 1.0}
        for key, col in cols.items():
            c2 = ev.two_of_three(g[col].to_numpy())
            r[key] = float(c2.max())
            series[(path, key)] = c2
        rows.append(r)
    return pd.DataFrame(rows), series


def fa_per_hour(f, series, ths, ds):
    """ths = {열 이름: threshold}. 여러 클래스를 같이 쓸 때 배경 시간당 오알림 (클래스 합)"""
    bg = f[(f["class"] == "background") & f["dataset"].isin(ds)]
    hours = bg["seconds"].sum() / 3600
    n = sum(ev.count_alerts(series[(p, k)], th) for k, th in ths.items() for p in bg["path16k"])
    return n / hours if hours else np.nan


def recall(f, c, key, th, ds):
    pos = f[(f["class"] == c) & f["dataset"].isin(ds)]
    return float((pos[key] >= th).mean()) if len(pos) else np.nan


def pick(f, series, c, key, target, max_fa):
    """val(all)에서: 재현율 목표 = 재현율 ≥ target인 가장 높은 값 / 오알림 목표 = 시간당 ≤ max_fa인 가장 낮은 값"""
    ds = GROUPS["all"]
    rec = [(th, recall(f, c, key, th, ds)) for th in GRID]
    ok = [th for th, r in rec if r >= target]
    th_rec = max(ok) if ok else max(rec, key=lambda t: (t[1], t[0]))[0]
    th_fa = None
    for th in GRID_FA:
        if fa_per_hour(f, series, {key: th}, ds) <= max_fa:
            th_fa = float(th)
            break
    return float(th_rec), (th_fa if th_fa is not None else float(GRID_FA[-1]))


# ---------------------------------------------------------------- 본체
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--train-on", choices=["all", "korean", "overseas"], default="all",
                    help="학습에 쓸 데이터 (평가는 항상 같은 val · test)")
    ap.add_argument("--hidden", type=int, default=256, help="mlp 은닉층 크기")
    ap.add_argument("--dropout", type=float, default=0.2)
    ap.add_argument("--lr", type=float, default=1e-3)
    ap.add_argument("--weight-decay", type=float, default=1e-4)
    ap.add_argument("--batch", type=int, default=512)
    ap.add_argument("--epochs", type=int, default=40)
    ap.add_argument("--patience", type=int, default=5)
    ap.add_argument("--target-recall", type=float, default=0.90)
    ap.add_argument("--max-fa", type=float, default=1.0, help="오알림 목표: val 배경 시간당 오알림 (클래스마다)")
    args = ap.parse_args()

    out = YDIR / "head" / args.train_on
    out.mkdir(parents=True, exist_ok=True)
    dev = "cuda" if torch.cuda.is_available() else "cpu"
    np.random.seed(SEED)
    names, alert, web_th = load_classes()
    print(f"클래스 {names} · 알림 대상 {alert} · 학습 데이터 {args.train_on} · 장치 {dev}")

    # 데이터
    wtr, etr = load_emb("train", names)
    if "keep" in wtr:
        k = wtr["keep"].to_numpy(bool)
        wtr, etr = wtr[k].reset_index(drop=True), etr[k]
    k = wtr["dataset"].isin(GROUPS[args.train_on]).to_numpy()
    wtr, etr = wtr[k].reset_index(drop=True), etr[k]
    data = {sp: load_emb(sp, names) for sp in ("val", "test")}
    wva, eva = data["val"]
    kv = wva["keep"].to_numpy(bool)
    print(f"[train] 조각 {len(wtr):,}개 · " + " · ".join(f"{c} {int((wtr['class'] == c).sum()):,}" for c in names))
    for sp, (w, _) in data.items():
        print(f"[{sp}] 조각 {len(w):,}개 (keep {int(w['keep'].sum()):,}) · 파일 {w['path16k'].nunique():,}개")

    # YAMNet 그대로(비교 기준) 점수 붙이기
    _, mapping = ev.load_config()
    labels = json.loads((YDIR / "labels.json").read_text(encoding="utf-8"))
    idx = ev.label_index(mapping, alert, labels)
    for sp in ("val", "test"):
        w, _ = data[sp]
        base, _ = ev.load_split(sp, idx)                   # 같은 windows.csv 순서
        keep_rows = base["class"].isin(names).to_numpy()
        base = base[keep_rows].reset_index(drop=True)
        for c in alert:
            w[f"yamnet_{c}"] = base[f"{c}_max"].to_numpy()
        w["orig_label"] = base["orig_label"].to_numpy()

    # 학습 · 예측
    models = {"logreg": 0, "mlp": args.hidden}
    hist_all, infos, exported = [], {}, {}
    for name, hidden in models.items():
        t0 = time.time()
        model, mean, std, hist, info = train_one(name, hidden, etr, wtr["y"].to_numpy(),
                                                 eva[kv], wva["y"].to_numpy()[kv], len(names), args, dev)
        info["seconds"] = round(time.time() - t0, 1)
        hist_all += hist
        infos[name] = info
        for sp in ("val", "test"):
            w, e = data[sp]
            p = predict(model, e, mean, std, dev)
            for i, c in enumerate(names):
                if c in alert:
                    w[f"{name}_{c}"] = p[:, i]
        exported[name] = to_json(export_layers(model, mean, std), names, name, info, args.train_on, len(wtr))
        # 내보낸 JSON 숫자(반올림 포함)로 다시 계산해서 torch 결과와 같은지 확인 → 웹에서 같은 계산이면 같은 값
        chk = forward_np(exported[name]["layers"], eva[:2000])
        diff = float(np.abs(chk - predict(model, eva[:2000], mean, std, dev)).max())
        info["export_check_max_diff"] = diff
        exported[name]["train"]["export_check_max_diff"] = diff
        (out / f"head_{name}.json").write_text(json.dumps(exported[name], ensure_ascii=False) + "\n",
                                                encoding="utf-8")
        print(f"  {name}: epoch {info['best_epoch']}/{info['epochs_run']} · val 손실 {info['val_loss']:.4f} · "
              f"{info['seconds']}초 · 내보내기 확인 최대 차이 {diff:.1e}")
    pd.DataFrame(hist_all).to_csv(out / "history.csv", index=False, encoding="utf-8-sig")

    # 평가
    srcs = ["yamnet"] + list(models)
    cols = {f"{s}_{c}": f"{s}_{c}" for s in srcs for c in alert}
    files, series = {}, {}
    for sp in ("val", "test"):
        files[sp], series[sp] = file_series(data[sp][0], cols)
    pd.concat([f.assign(split=sp) for sp, f in files.items()]).to_csv(out / "files.csv", index=False,
                                                                       encoding="utf-8-sig")

    settings = []   # (모델, 기준, {class: th})
    for s in srcs:
        th_rec, th_fa = {}, {}
        for c in alert:
            th_rec[c], th_fa[c] = pick(files["val"], series["val"], c, f"{s}_{c}", args.target_recall, args.max_fa)
        settings += [(s, "재현율 목표", th_rec), (s, "오알림 목표", th_fa)]
    settings.insert(0, ("yamnet", "지금 웹 (classes.yaml)", dict(web_th)))

    rows = []
    for s, how, ths in settings:
        r = {"모델": s, "기준": how, "threshold": " / ".join(f"{ths[c]:g}" for c in alert)}
        for c in alert:
            r[f"{c} 재현율 val·all"] = recall(files["val"], c, f"{s}_{c}", ths[c], GROUPS["all"])
        for c in alert:
            r[f"{c} 재현율 test·korean"] = recall(files["test"], c, f"{s}_{c}", ths[c], GROUPS["korean"])
        for c in alert:
            r[f"{c} 재현율 test·overseas"] = recall(files["test"], c, f"{s}_{c}", ths[c], GROUPS["overseas"])
        kk = {f"{s}_{c}": ths[c] for c in alert}
        r["시간당 오알림 val·all"] = fa_per_hour(files["val"], series["val"], kk, GROUPS["all"])
        r["시간당 오알림 test·korean"] = fa_per_hour(files["test"], series["test"], kk, GROUPS["korean"])
        rows.append(r)
    table = pd.DataFrame(rows)

    # 추천 모델: val(all) 오알림 목표에서 알림 대상 재현율 평균이 가장 높은 분류기 (test는 보지 않음)
    fa_rows = table[(table["기준"] == "오알림 목표") & table["모델"].isin(models)]
    score = fa_rows[[f"{c} 재현율 val·all" for c in alert]].mean(axis=1)
    best = fa_rows.loc[score.idxmax(), "모델"]
    best_th = next(ths for s, how, ths in settings if s == best and how == "오알림 목표")

    # 조각 단위 구분력 (test keep 조각)
    wt = data["test"][0]
    auc_rows = []
    for g in ("korean", "overseas"):
        k = wt[wt["keep"] & wt["dataset"].isin(GROUPS[g])]
        for c in alert:
            y = (k["class"] == c).to_numpy()
            r = {"묶음": g, "class": c}
            for s in srcs:
                r[s] = roc_auc_score(y, k[f"{s}_{c}"]) if 0 < y.sum() < len(y) else np.nan
            auc_rows.append(r)

    # 소분류별 재현율 (test, 오알림 목표)
    ft = files["test"]
    sub_rows = []
    fa_th = {s: next(ths for s2, how, ths in settings if s2 == s and how == "오알림 목표") for s in srcs}
    for c in alert:
        for (ds, ol), g in ft[ft["class"] == c].groupby(["dataset", "orig_label"]):
            r = {"class": c, "dataset": ds, "소분류": ol, "파일": len(g),
                 "yamnet 지금 웹": float((g[f"yamnet_{c}"] >= web_th[c]).mean())}
            for s in srcs:
                r[f"{s} 오알림 목표"] = float((g[f"{s}_{c}"] >= fa_th[s][c]).mean())
            sub_rows.append(r)

    # 혼동 (test 한국, 추천 모델 · 오알림 목표)
    conf_rows = []
    fk = ft[ft["dataset"].isin(GROUPS["korean"])]
    for true_c in names:
        g = fk[fk["class"] == true_c]
        r = {"정답": true_c, "파일": len(g)}
        for c in alert:
            r[f"{c} 확정 비율"] = float((g[f"{best}_{c}"] >= best_th[c]).mean()) if len(g) else np.nan
        conf_rows.append(r)

    # 변환표 (score: head_v1) — val keep 조각으로 만들고 test keep 조각으로 확인
    cal_rows = []
    for name in models:
        cal = {"version": 1, "score": "head_v1", "model": name, "method": "isotonic",
               "eval": {"set": "val", "n": int(wva.loc[kv, "path16k"].nunique()), "date": str(date.today())},
               "levels": ev.LEVELS, "classes": {}}
        kvw = wva[kv]
        ktw = wt[wt["keep"] & wt["dataset"].isin(GROUPS["korean"])]
        for c in alert:
            _, pts = ev.iso_points(kvw[f"{name}_{c}"].to_numpy(), (kvw["class"] == c).to_numpy().astype(float))
            cal["classes"][c] = pts
            x, y = ktw[f"{name}_{c}"].to_numpy(), (ktw["class"] == c).to_numpy().astype(float)
            p = np.interp(x, pts["x"], pts["y"])
            cal_rows.append({"모델": name, "class": c, "점 개수": len(pts["x"]),
                             "ECE 그대로": ev.ece(x, y), "ECE 변환 후": ev.ece(p, y),
                             "Brier 그대로": np.mean((x - y) ** 2), "Brier 변환 후": np.mean((p - y) ** 2)})
        (out / f"calibration_{name}.json").write_text(json.dumps(cal, ensure_ascii=False, indent=2) + "\n",
                                                      encoding="utf-8")

    # 보고서
    R = [f"# 작은 분류기 학습 · 평가 (head_v1) · {date.today()}", "",
         f"- 학습 데이터: **{args.train_on}** (train keep 조각 {len(wtr):,}개 · "
         + " · ".join(f"{c} {int((wtr['class'] == c).sum()):,}" for c in names) + ")",
         "- 입력: YAMNet 임베딩 1,024개 (웹과 같은 0.975초) · 출력: " + " · ".join(names) + " 확률",
         "- 평가 규칙: eval_yamnet.py와 같음 (0.5초마다 · 3번 중 2번 · 같은 소리 5초 재알림 금지 · 파일 단위)",
         f"- threshold는 val(all)로 고르고 test로 보고: 재현율 목표 ≥ {args.target_recall} / "
         f"오알림 목표 시간당 ≤ {args.max_fa}회 (클래스마다)",
         f"- 비교 기준 `yamnet` = YAMNet 그대로(max), `지금 웹` = classes.yaml threshold "
         + " / ".join(f"{web_th[c]}" for c in alert), ""]

    R += ["## 1. 학습", "",
          ev.md_table(pd.DataFrame([{"모델": n, "층": "1024 → 3" if h == 0 else f"1024 → {h} → 3",
                                     "best epoch": infos[n]["best_epoch"], "돈 epoch": infos[n]["epochs_run"],
                                     "val 손실": infos[n]["val_loss"], "시간(초)": str(infos[n]["seconds"]),
                                     "클래스 가중치": " · ".join(map(str, infos[n]["class_weight"])),
                                     "내보내기 확인 차이": f"{infos[n]['export_check_max_diff']:.1e}"}
                                    for n, h in models.items()]), "{:.4f}"), ""]

    R += ["## 2. 알림 전체 (클래스 기준을 같이 적용) — YAMNet 그대로 vs 작은 분류기", "",
          ev.md_table(table), "",
          f"- **추천 모델: `{best}`** (val 오알림 목표에서 {' · '.join(alert)} 재현율 평균이 가장 높음, test는 보지 않고 고름)",
          f"- 추천 threshold (오알림 목표): " + " · ".join(f"{c} {best_th[c]:g}" for c in alert), ""]

    R += ["## 3. 조각 단위 구분력 (test keep 조각, AUC)", "", ev.md_table(pd.DataFrame(auc_rows)), ""]
    R += ["## 4. test 소분류별 재현율", "", ev.md_table(pd.DataFrame(sub_rows)), ""]
    R += [f"## 5. test 한국 파일 단위 혼동 (`{best}` · 오알림 목표)", "",
          "정답 클래스별로 각 알림이 확정된 비율", "", ev.md_table(pd.DataFrame(conf_rows)), ""]
    R += ["## 6. 점수 → 확률 변환표 (score: head_v1, test 한국 keep 조각)", "",
          ev.md_table(pd.DataFrame(cal_rows), "{:.4f}"), "",
          "주의: 확률은 val의 클래스 비율(배경이 많음)을 반영함. 학습 때 클래스 가중치를 줘서 softmax 그대로는 사이렌 · 경적 쪽으로 부풀려져 있음 → 변환표로 맞춤", ""]
    R += ["## 다음 할 일", "",
          f"- 추천 모델 `head_{best}.json` · `calibration_{best}.json`과 threshold를 하민 님께 (H2 형식 확인 → H6 웹 적용)",
          "- 웹 적용 후 같은 소리로 웹 · Python 확률이 같은지 대조 (check_yamnet_web.py처럼)",
          "- 비교 실험: `--train-on korean` / `overseas` (같은 한국 test로)", ""]
    (out / "report.md").write_text("\n".join(R), encoding="utf-8")

    show = table[["모델", "기준", "threshold"] + [f"{c} 재현율 test·korean" for c in alert] + ["시간당 오알림 test·korean"]]
    print("\n" + ev.md_table(show))
    print(f"\n추천 모델: {best} · threshold " + " · ".join(f"{c} {best_th[c]:g}" for c in alert))
    print(f"저장: {out.relative_to(ROOT)}/ (report.md · head_*.json · calibration_*.json · history.csv · files.csv)")


if __name__ == "__main__":
    main()
