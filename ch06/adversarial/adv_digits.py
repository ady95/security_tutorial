"""06-3 Adversarial Example — 작은 손글씨 숫자 분류 모델을 FGSM 으로 속이고, 적대적 학습으로 방어한다

    python adv_digits.py train          # 기본 모델 학습 → model_base.npz
    python adv_digits.py attack         # FGSM 으로 기본 모델 공격, 예시 한 장과 정확도 표
    python adv_digits.py observe        # 무엇이 무엇으로 바뀌었나, 틀린 답의 확신도
    python adv_digits.py defend         # 적대적 학습 → model_robust.npz
    python adv_digits.py verify         # 두 모델을 FGSM 과 PGD(반복 공격)로 다시 시험

데이터: scikit-learn 에 들어 있는 8x8 손글씨 숫자 1,797장 (내려받기 없음). GPU 불필요.
모델 파일은 pickle 이 아니라 가중치만 담은 .npz 로 저장한다 (06-2: 모델 파일도 코드처럼 다룬다).
"""
import sys
import time
import unicodedata
from collections import Counter
from pathlib import Path

import numpy as np
from sklearn.datasets import load_digits
from sklearn.model_selection import train_test_split
from sklearn.neural_network import MLPClassifier

HERE = Path(__file__).resolve().parent
BASE, ROBUST = HERE / "model_base.npz", HERE / "model_robust.npz"
EPS_LIST = [0.05, 0.1, 0.2, 0.3]     # 픽셀 값(0~1)을 최대 얼마까지 바꿀 수 있는가
SHOW_EPS = 0.1                        # 예시와 관찰에 쓰는 크기
SEED = 0


def load_data():
    digits = load_digits()
    X = digits.data / 16.0                                    # 0~16 → 0~1
    return train_test_split(X, digits.target, test_size=0.3, random_state=SEED, stratify=digits.target)


# ---- 모델: 입력 64 → 은닉 64(ReLU) → 출력 10(softmax) -----------------------------------
def to_weights(clf: MLPClassifier) -> dict:
    return {"W1": clf.coefs_[0], "b1": clf.intercepts_[0], "W2": clf.coefs_[1], "b2": clf.intercepts_[1]}


def save(path: Path, w: dict):
    np.savez(path, **w)


def load(path: Path) -> dict:
    if not path.exists():
        sys.exit(f"{path.name} 이 없습니다. 먼저 train(또는 defend)을 실행하세요.")
    with np.load(path, allow_pickle=False) as f:              # 가중치 숫자만 읽는다
        return {k: f[k] for k in f.files}


def forward(w: dict, X):
    a1 = X @ w["W1"] + w["b1"]
    h = np.maximum(a1, 0)
    z = h @ w["W2"] + w["b2"]
    p = np.exp(z - z.max(axis=1, keepdims=True))
    return a1, p / p.sum(axis=1, keepdims=True)


def predict(w: dict, X):
    p = forward(w, X)[1]
    return p.argmax(axis=1), p.max(axis=1)


def accuracy(w: dict, X, y) -> float:
    return float((predict(w, X)[0] == y).mean())


def input_grad(w: dict, X, y):
    """손실(교차 엔트로피)을 입력 픽셀로 미분한 값. 공격자는 이 방향으로 픽셀을 민다."""
    a1, p = forward(w, X)
    dz = p.copy()
    dz[np.arange(len(y)), y] -= 1
    dh = (dz @ w["W2"].T) * (a1 > 0)
    return dh @ w["W1"].T


# ---- 공격 ---------------------------------------------------------------------------
def fgsm(w: dict, X, y, eps: float):
    """FGSM: 기울기의 부호 방향으로 모든 픽셀을 eps 만큼 한 번에 민다."""
    return np.clip(X + eps * np.sign(input_grad(w, X, y)), 0, 1)


def pgd(w: dict, X, y, eps: float, steps: int = 20):
    """PGD: 작은 걸음으로 여러 번 밀되, 원본에서 eps 이상 멀어지지 않게 한다 (FGSM 의 반복판)."""
    alpha, Xa = eps / 4, X.copy()
    for _ in range(steps):
        Xa = Xa + alpha * np.sign(input_grad(w, Xa, y))
        Xa = np.clip(np.clip(Xa, X - eps, X + eps), 0, 1)
    return Xa


# ---- 화면 출력 -------------------------------------------------------------------------
SHADES = " .:-=+*#%@"


def pad(text: str, width: int, right: bool = False) -> str:
    """한글은 화면에서 두 칸을 차지하므로 표시 폭 기준으로 맞춘다."""
    gap = " " * max(0, width - sum(2 if unicodedata.east_asian_width(ch) in "WF" else 1 for ch in text))
    return gap + text if right else text + gap


def ascii_img(x) -> list[str]:
    return ["".join(SHADES[min(9, int(v * 9.999))] * 2 for v in row) for row in x.reshape(8, 8)]


def ascii_diff(d) -> list[str]:
    return ["".join(("++" if v > 1e-9 else "--" if v < -1e-9 else "  ") for v in row) for row in d.reshape(8, 8)]


# ---- 명령 ---------------------------------------------------------------------------
def train():
    Xtr, Xte, ytr, yte = load_data()
    t0 = time.time()
    clf = MLPClassifier(hidden_layer_sizes=(64,), max_iter=500, random_state=SEED).fit(Xtr, ytr)
    w = to_weights(clf)
    save(BASE, w)
    print(f"[학습] 학습 {len(Xtr)}장 · 시험 {len(Xte)}장 · {time.time() - t0:.1f}초")
    print(f"[정확도] 깨끗한 시험 이미지 {accuracy(w, Xte, yte):.1%} → {BASE.name}")


def attack():
    _, Xte, _, yte = load_data()
    w = load(BASE)
    pred, conf = predict(w, Xte)
    Xa = fgsm(w, Xte, yte, SHOW_EPS)
    apred, aconf = predict(w, Xa)
    # 원래 맞혔는데 공격 후 틀린 첫 이미지를 예시로 보여 준다
    i = next(i for i in range(len(yte)) if pred[i] == yte[i] and apred[i] != yte[i])
    print(f"[예시] 시험 이미지 #{i} · 정답 {yte[i]} · eps {SHOW_EPS}")
    print(f"{pad('원본', 16)}  {pad('공격 후', 16)}  바뀐 방향(+ 밝게, - 어둡게)")
    for a, b, c in zip(ascii_img(Xte[i]), ascii_img(Xa[i]), ascii_diff(Xa[i] - Xte[i])):
        print(f"{a}  {b}  {c}")
    print(f"원본 → {pred[i]} (확신도 {conf[i]:.0%})   공격 후 → {apred[i]} (확신도 {aconf[i]:.0%})")
    print(f"픽셀 최대 변화 {np.abs(Xa[i] - Xte[i]).max():.2f} · 바뀐 픽셀 {(np.abs(Xa[i] - Xte[i]) > 1e-9).sum()}/64\n")
    print("[정확도] eps 별 FGSM 공격 후 (시험 이미지 전체)")
    print(f"  공격 없음  {accuracy(w, Xte, yte):.1%}")
    for eps in EPS_LIST:
        print(f"  eps {eps:<5} {accuracy(w, fgsm(w, Xte, yte, eps), yte):.1%}")


def observe():
    _, Xte, _, yte = load_data()
    w = load(BASE)
    pred, _ = predict(w, Xte)
    Xa = fgsm(w, Xte, yte, SHOW_EPS)
    apred, aconf = predict(w, Xa)
    flipped = (pred == yte) & (apred != yte)
    print(f"[관찰] eps {SHOW_EPS} · 원래 맞혔다가 틀리게 된 이미지 {flipped.sum()}/{(pred == yte).sum()}")
    print("  자주 바뀐 쌍 (정답 → 모델 답):", ", ".join(f"{a}→{b} {n}건" for (a, b), n in
                                                Counter(zip(yte[flipped], apred[flipped])).most_common(5)))
    print(f"  틀린 답의 평균 확신도 {aconf[flipped].mean():.0%} · 90% 이상 확신한 틀린 답 {(aconf[flipped] >= 0.9).sum()}건")
    print(f"  평균 픽셀 변화(절댓값) {np.abs(Xa - Xte).mean():.3f} · 최대 {np.abs(Xa - Xte).max():.2f}")


def defend(epochs: int = 150):
    """적대적 학습: 매 에포크마다 '현재 모델'을 공격한 이미지를 만들어 깨끗한 이미지와 함께 학습한다."""
    Xtr, Xte, ytr, yte = load_data()
    rng = np.random.default_rng(SEED)
    clf = MLPClassifier(hidden_layer_sizes=(64,), random_state=SEED)
    t0 = time.time()
    clf.partial_fit(Xtr, ytr, classes=np.arange(10))
    for _ in range(epochs):
        eps = rng.uniform(0.05, 0.3, size=(len(Xtr), 1))       # 여러 크기의 공격을 섞는다
        Xadv = np.clip(Xtr + eps * np.sign(input_grad(to_weights(clf), Xtr, ytr)), 0, 1)
        clf.partial_fit(np.vstack([Xtr, Xadv]), np.concatenate([ytr, ytr]))
    w = to_weights(clf)
    save(ROBUST, w)
    print(f"[적대적 학습] {epochs} 에포크 · {time.time() - t0:.1f}초 → {ROBUST.name}")
    print(f"[정확도] 깨끗한 시험 이미지 {accuracy(w, Xte, yte):.1%} (기본 모델 {accuracy(load(BASE), Xte, yte):.1%})")


def verify():
    _, Xte, _, yte = load_data()
    models = {"기본 모델": load(BASE), "적대적 학습 모델": load(ROBUST)}
    print(pad("공격", 16) + "".join(pad(name, 18, right=True) for name in models))
    print(pad("공격 없음", 16) + "".join(f"{accuracy(w, Xte, yte):>18.1%}" for w in models.values()))
    for kind, fn in (("FGSM", fgsm), ("PGD", pgd)):
        for eps in EPS_LIST:
            row = "".join(f"{accuracy(w, fn(w, Xte, yte, eps), yte):>18.1%}" for w in models.values())
            print(f"{kind + ' eps ' + str(eps):<16}{row}")
    # 다른 모델로 만든 공격 이미지가 옮겨 가는가 (공격자가 대상 모델 내부를 모를 때)
    Xt = fgsm(models["기본 모델"], Xte, yte, 0.2)
    print(f"\n[전이] 기본 모델로 만든 FGSM eps 0.2 이미지 → 적대적 학습 모델 {accuracy(models['적대적 학습 모델'], Xt, yte):.1%}")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    np.set_printoptions(precision=3, suppress=True)
    cmd = sys.argv[1] if len(sys.argv) > 1 else "attack"
    {"train": train, "attack": attack, "observe": observe, "defend": defend, "verify": verify}[cmd]()
