#!/usr/bin/env python3
"""Esporta Adaboost.model (AdaBoostM1 + DecisionStump) in JSON a piena precisione,
così il modello ORIGINALE può girare anche senza Java (es. Render).
Uso:  python scripts/export_weka_model.py   (richiede python-weka-wrapper3 + JDK)"""
import os, sys, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import weka.core.jvm as jvm
jvm.start(max_heap_size="512m", packages=False)
from weka.core import serialization
from weka.core.dataset import Instances
import jpype

SRC = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "models_weka", "Adaboost.model")
DST = SRC.replace("Adaboost.model", "brcam_adaboost.json")

def field(obj, name):
    f = obj.getClass().getDeclaredField(name) if name in [x.getName() for x in obj.getClass().getDeclaredFields()] \
        else obj.getClass().getSuperclass().getDeclaredField(name)
    f.setAccessible(True)
    return f.get(obj)

objs = serialization.read_all(SRC)
ada, hdr = objs[0], Instances(jobject=objs[1])
atts = [{"name": hdr.attribute(i).name,
         "values": [hdr.attribute(i).value(j) for j in range(hdr.attribute(i).num_values)]}
        for i in range(hdr.num_attributes)]
cls_idx = hdr.class_index if hdr.class_index >= 0 else hdr.num_attributes - 1

# campi privati di AdaBoostM1 (Iterated/ParallelIteratedSingleClassifierEnhancer)
def get_any(o, name):
    c = o.getClass()
    while c is not None:
        try:
            f = c.getDeclaredField(name); f.setAccessible(True); return f.get(o)
        except Exception:
            c = c.getSuperclass()
    raise AttributeError(name)

betas = [float(b) for b in get_any(ada, "m_Betas")]
n_it = int(get_any(ada, "m_NumIterationsPerformed"))
stumps = []
for k in range(n_it):
    s = get_any(ada, "m_Classifiers")[k]
    dist = [[float(x) for x in row] for row in get_any(s, "m_Distribution")]
    stumps.append({"att_index": int(get_any(s, "m_AttIndex")), "split_value": int(float(get_any(s, "m_SplitPoint"))),
                   "distribution": dist, "beta": betas[k]})

out = {"source": os.path.basename(SRC), "algorithm": "weka.classifiers.meta.AdaBoostM1 + DecisionStump",
       "relation": hdr.relationname, "class_index": cls_idx, "attributes": atts, "stumps": stumps}
json.dump(out, open(DST, "w"), indent=1, ensure_ascii=False)
print(f"Esportato {n_it} stump → {DST}")
jvm.stop()
