"""Verifica che il runtime Python dia ESATTAMENTE le stesse probabilità di WEKA
sul file Adaboost.model. Richiede JDK + python-weka-wrapper3.
Uso: python tests/test_model_equivalence.py"""
import os, sys, random
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from ml.weka_bridge import WekaClassifier, ExportedAdaBoost, FEATURES, FEATURE_NAMES

weka, exp = WekaClassifier(), ExportedAdaBoost()
weka.load()
rnd = random.Random(42)
N, worst = 3000, 0.0
for i in range(N):
    f = {k: (rnd.choice(v) if rnd.random() > 0.08 else "") for k, v in FEATURES.items()}   # ~8% mancanti
    lw, cw, mw = weka.predict(f)
    le, ce, me = exp.predict(f)
    assert lw == le, f"classe diversa su {f}: WEKA={lw} Python={le}"
    worst = max(worst, abs(cw - ce), abs(mw - me))
print(f"✅ {N} casi casuali: stessa classe in tutti, differenza massima di probabilità = {worst:.2e}")
assert worst < 1e-9
