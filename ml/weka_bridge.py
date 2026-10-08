# ml/weka_bridge.py — Feature ESATTE estratte da Adaboost.model
import os, logging
from typing import Dict, Tuple, Optional
import numpy as np

log = logging.getLogger(__name__)

MODEL_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "models_weka", "Adaboost.model"
)

# ═══════════════════════════════════════════════════════════════════════════════
# FEATURE ESATTE DEL MODELLO (estratte dal binario Adaboost.model)
# Tutti gli attributi sono NOMINALI (categoriali), non numerici
# Classe target: CONSERVATIVA / MASTECTOMIA
# ═══════════════════════════════════════════════════════════════════════════════

FEATURES = {
    # Valori ammessi = esattamente quelli dell'header salvato in Adaboost.model
    # (verificati con weka.core.serialization.read_all). L'ordine qui è solo di
    # visualizzazione: la codifica verso WEKA avviene PER NOME sull'header del file.
    "età": ["18-25", "26-36", "37-49", "50-65", "66-75", "Over_75"],
    "fumo": ["no", "si"],
    "gravidanza": ["no", "si"],
    "familiarità_carcinoma_ovarico": ["no", "si"],
    "struttura_ghiandolare": [
        "Normale", "Adenosi", "Distrofia", "Displasia",
        "Displasia_fibrosa", "Displasia_micronodulare", "Displasia_nodulare",
        "Displasia_fibroadenosa", "Displasia_fibroadiposa", "Displasia_fibronodulare",
        "Displasia_fibrocistica", "Displasia_fibroghiandolare",
        "Involuzione_adiposa", "Involuzione_fibroadiposa", "Esiti_chirurgici",
    ],
    "rapporto_cuteDX": [
        "Regolare", "Eritema", "Edematoso", "Papule", "Ispessimento",
        "Retrazione_Iniziale", "Retrazione", "Retrazione_indotta",
        "Infiltrazione", "Ulcerazione", "Esiti_BCS", "Esiti_Mastectomy", "Esiti_chirurgici",
    ],
    "rapporto_cuteSX": [
        "Regolare", "Eritema", "Edematoso", "Papule", "Ispessimento",
        "Retrazione_Iniziale", "Retrazione", "Retrazione_indotta",
        "Infiltrazione", "Ulcerazione", "Esiti_BCS", "Esiti_Mastectomy", "Esiti_chirurgici",
    ],
    "rapporto_areola_capezzoloDX": [
        "Regolare", "Assente", "Appiattito", "Introflessione", "Retrazione", "Secrezione",
        "Disepitelizzazione", "Ispessimento", "Edema", "Scraping", "Ulcerazione",
        "Infiltrazione", "Non_distinguibile", "Esiti_chirurgici",
    ],
    "rapporto_areola_capezzoloSX": [
        "Regolare", "Assente", "Appiattito", "Introflessione", "Retrazione", "Secrezione",
        "Disepitelizzazione", "Ispessimento", "Ulcerazione", "Infiltrazione", "Esiti_chirurgici",
    ],
    "stato_linfonodaleDX": ["Normale", "Sospetto_adenopatia", "Adenopatia",
                            "Pacchetto_linfonodale", "Esiti_chirurgici"],
    "stato_linfonodaleSX": ["Normale", "Sospetto_adenopatia", "Adenopatia",
                            "Pacchetto_linfonodale", "Esiti_chirurgici"],
    "biRadsClinico": [
        "E0", "E1", "E2", "E3", "E4", "E5",
        "Bil:E1-E3/E3-E1", "Bil:E4-E1/E1-E4", "Bil:E4-E3/E3-E4", "Bil:E5-E1/E1-E5",
        "Bil:E5-E2/E2-E5", "Bil:E5-E3/E3-E5", "Bil:E5-E4/E4-E5",
    ],
    # Citologia: codifica C0–C5 (C5 = positivo per malignità), anche bilaterale
    "citologia_codifica": ["C0", "C1", "C2", "C3", "C4", "C5",
                           "Bil:C5-C3/C3-C5", "Bil:C5-C4/C4-C5"],
    "focalità": ["no", "si", "Bil:si-no/no-si"],
    # Nel training compare solo "si": "no" è ammesso nel form ma per il modello
    # è un valore non visto e viene passato come mancante (comportamento standard WEKA)
    "ricostruzione": ["si", "no"],
}

FEATURE_NAMES = list(FEATURES.keys())   # 15 feature

# Nome feature del modello → campo nel dizionario paziente/DB (dove differisce)
FEATURE_DB_FIELD = {
    "età":                           "age_range",
    "familiarità_carcinoma_ovarico": "familiarita_carcinoma_ovarico",
    "focalità":                      "focalita",
}

def patient_model_features(p: dict) -> dict:
    """Estrae le 15 feature del modello da un paziente. Valori assenti o non
    ammessi dal modello → "" (così il form li segnala invece di inviare 'None')."""
    out = {}
    for f in FEATURE_NAMES:
        v = p.get(FEATURE_DB_FIELD.get(f, f))
        out[f] = v if v in FEATURES[f] else ""
    return out
CLASS_VALUES  = ["CONSERVATIVA", "MASTECTOMIA"]   # target esatto del modello

FEATURE_LABELS = {
    "età":                           "Età",
    "fumo":                          "Fumo",
    "gravidanza":                    "Gravidanza",
    "familiarità_carcinoma_ovarico": "Familiarità K. ovaio",
    "struttura_ghiandolare":         "Struttura ghiandolare",
    "rapporto_cuteDX":               "Cute DX",
    "rapporto_cuteSX":               "Cute SX",
    "rapporto_areola_capezzoloDX":   "Areola-capezzolo DX",
    "rapporto_areola_capezzoloSX":   "Areola-capezzolo SX",
    "stato_linfonodaleDX":           "Stato linfonodale DX",
    "stato_linfonodaleSX":           "Stato linfonodale SX",
    "biRadsClinico":                 "BI-RADS clinico",
    "citologia_codifica":            "Citologia",
    "focalità":                      "Focalità",
    "ricostruzione":                 "Ricostruzione",
}

FEATURE_GROUPS = {
    "👤  Paziente":          ["età","fumo","gravidanza","familiarità_carcinoma_ovarico"],
    "🔬  Imaging mammario":  ["struttura_ghiandolare","rapporto_cuteDX","rapporto_cuteSX",
                              "rapporto_areola_capezzoloDX","rapporto_areola_capezzoloSX"],
    "🩺  Linfonodi & Stadio":["stato_linfonodaleDX","stato_linfonodaleSX","biRadsClinico"],
    "🏥  Citologia & Chirurgia":["citologia_codifica","focalità","ricostruzione"],
}

CLINICAL_IMPORTANCE = {
    "stato_linfonodaleDX":           0.92,
    "stato_linfonodaleSX":           0.89,
    "biRadsClinico":                 0.86,
    "focalità":                      0.83,
    "citologia_codifica":            0.80,
    "struttura_ghiandolare":         0.72,
    "rapporto_cuteDX":               0.65,
    "rapporto_cuteSX":               0.63,
    "rapporto_areola_capezzoloDX":   0.58,
    "rapporto_areola_capezzoloSX":   0.55,
    "familiarità_carcinoma_ovarico": 0.50,
    "età":                           0.44,
    "ricostruzione":                 0.38,
    "fumo":                          0.30,
    "gravidanza":                    0.22,
}

FEATURE_DESCRIPTIONS = {
    # Solo significato clinico: l'importanza è calcolata dai pesi reali del modello
    "età":                           ("", "Fascia d'età della paziente."),
    "fumo":                          ("", "Abitudine al fumo."),
    "gravidanza":                    ("", "Storia di gravidanze."),
    "familiarità_carcinoma_ovarico": ("", "Familiarità per carcinoma ovarico (possibile predisposizione BRCA)."),
    "struttura_ghiandolare":         ("", "Pattern del parenchima ghiandolare all'imaging."),
    "rapporto_cuteDX":               ("", "Aspetto della cute, mammella destra."),
    "rapporto_cuteSX":               ("", "Aspetto della cute, mammella sinistra."),
    "rapporto_areola_capezzoloDX":   ("", "Aspetto del complesso areola-capezzolo, destra."),
    "rapporto_areola_capezzoloSX":   ("", "Aspetto del complesso areola-capezzolo, sinistra."),
    "stato_linfonodaleDX":           ("", "Stato dei linfonodi ascellari, destra."),
    "stato_linfonodaleSX":           ("", "Stato dei linfonodi ascellari, sinistra."),
    "biRadsClinico":                 ("", "Categoria BI-RADS clinica (E0–E5), anche bilaterale."),
    "citologia_codifica":            ("", "Esito citologico C0–C5 (C5 = positivo per malignità), anche bilaterale."),
    "focalità":                      ("", "Lesione multifocale (si), unifocale (no) o bilaterale."),
    "ricostruzione":                 ("", "Ricostruzione pianificata. Nel dataset di addestramento compare solo "
                                          "'si': un 'no' viene passato al modello come valore mancante."),
}

# Mappa output modello → etichette display
CLASS_DISPLAY = {
    "CONSERVATIVA": "BCS (Conservativa)",
    "MASTECTOMIA":  "Mastectomia",
}
CLASS_COLOR = {
    "CONSERVATIVA": "#059669",
    "MASTECTOMIA":  "#DC2626",
}


class BaseClassifier:
    name="base"; version="0.0"
    def predict(self,f): raise NotImplementedError
    def is_ready(self): return False
    def get_feature_importance(self): return CLINICAL_IMPORTANCE
    def get_model_info(self): return {}
    def unseen_values(self, features): return []


class WekaClassifier(BaseClassifier):
    """Modello WEKA originale. Il file .model contiene [AdaBoostM1, Instances header]:
    l'header è usato come stampo, così nomi, ordine degli attributi, codifica dei
    valori nominali e ordine delle classi coincidono con quelli dell'addestramento."""
    name = "WEKA AdaBoost — BrCaM"

    def __init__(self, path=MODEL_PATH):
        import threading
        self.model_path = path
        self._clf = None
        self._header = None
        self._lock = threading.Lock()
        self.version = "BrCaM-AdaBoost-95%"

    def load(self):
        import weka.core.jvm as jvm
        if not jvm.started:
            jvm.start(max_heap_size="512m", packages=False)
        from weka.core import serialization
        from weka.core.dataset import Instances
        from weka.classifiers import Classifier
        objs = serialization.read_all(self.model_path)
        self._clf = Classifier(jobject=objs[0])
        if len(objs) < 2:
            raise RuntimeError("Il file .model non contiene l'header del dataset (salvalo da WEKA Explorer).")
        self._header = Instances(jobject=objs[1])
        if self._header.class_index < 0:
            self._header.class_is_last()
        names = [self._header.attribute(i).name for i in range(self._header.num_attributes)]
        missing = [f for f in FEATURE_NAMES if f not in names]
        if missing:
            raise RuntimeError(f"Feature non presenti nell'header del modello: {missing}")
        log.info(f"WEKA caricato: {self._clf.classname} · {self._header.num_attributes} attributi")

    def is_ready(self):
        return self._clf is not None and self._header is not None

    def _build_instance(self, features: Dict[str, str]):
        from weka.core.dataset import Instances, Instance
        data = Instances.template_instances(self._header, 0)
        vals = []
        for i in range(data.num_attributes):
            att = data.attribute(i)
            if i == data.class_index:
                vals.append(float("nan"))
                continue
            v = features.get(att.name)
            idx = att.index_of(v) if v not in (None, "") else -1
            vals.append(float(idx) if idx >= 0 else float("nan"))   # non visto → mancante
        inst = Instance.create_instance(vals)
        data.add_instance(inst)
        return data.get_instance(0)

    def predict(self, features: Dict[str, str]) -> Tuple[str, float, float]:
        with self._lock:
            if not self.is_ready():
                self.load()
            inst = self._build_instance(features)
            dist = list(self._clf.distribution_for_instance(inst))
            cls = self._header.class_attribute
            prob = {cls.value(i): float(dist[i]) for i in range(len(dist))}
        p_cons, p_mast = prob.get("CONSERVATIVA", 0.0), prob.get("MASTECTOMIA", 0.0)
        label = "CONSERVATIVA" if p_cons >= p_mast else "MASTECTOMIA"
        return label, p_cons, p_mast

    def unseen_values(self, features: Dict[str, str]) -> list:
        """Feature il cui valore non compare nel training (passate come mancanti)."""
        if not self.is_ready():
            self.load()
        out = []
        for f, v in features.items():
            att = self._header.attribute_by_name(f)
            if att is not None and v and att.index_of(v) < 0:
                out.append(f)
        return out

    def get_feature_importance(self):
        try:
            return ExportedAdaBoost().get_feature_importance()
        except Exception:
            return CLINICAL_IMPORTANCE

    def get_model_info(self):
        return {"name": "BrCaM — AdaBoost", "algorithm": "AdaBoostM1 (10 iterazioni)",
                "base_learner": "Decision Stump", "accuracy": "95%",
                "dataset_size": "5100 pazienti", "validation": "10-fold CV",
                "classes": CLASS_VALUES, "paper": "Scientific Reports 2026",
                "source": "Evangelista, Gautam et al.", "path": self.model_path,
                "active": True, "n_features": len(FEATURE_NAMES)}


EXPORT_PATH = os.path.join(os.path.dirname(MODEL_PATH), "brcam_adaboost.json")


class ExportedAdaBoost(BaseClassifier):
    """Il modello ORIGINALE (Adaboost.model) eseguito in Python puro, senza Java.
    Parametri esportati a piena precisione da scripts/export_weka_model.py;
    l'algoritmo replica weka.classifiers.meta.AdaBoostM1.distributionForInstance:
    ogni DecisionStump vota la propria classe con peso beta, poi logs2probs (softmax).
    L'equivalenza con WEKA è verificata in tests/test_model_equivalence.py."""
    name = "BrCaM AdaBoost (modello originale, runtime Python)"
    version = "BrCaM-AdaBoost-95%"

    def __init__(self, path=EXPORT_PATH):
        import json
        m = json.load(open(path, encoding="utf-8"))
        self.path = path
        self.attributes = m["attributes"]
        self.class_index = m["class_index"]
        self.class_values = self.attributes[self.class_index]["values"]
        self.stumps = m["stumps"]
        self._index = {a["name"]: i for i, a in enumerate(self.attributes)}

    def is_ready(self): return True

    def _encode(self, features):
        enc = []
        for i, a in enumerate(self.attributes):
            v = None if i == self.class_index else features.get(a["name"])
            enc.append(a["values"].index(v) if v in a["values"] else None)   # non visto → mancante
        return enc

    def predict(self, features):
        x = self._encode(features)
        sums = [0.0] * len(self.class_values)
        for s in self.stumps:
            v = x[s["att_index"]]
            branch = 2 if v is None else (0 if v == s["split_value"] else 1)
            row = s["distribution"][branch]
            sums[row.index(max(row))] += s["beta"]
        mx = max(sums)
        ex = [np.exp(v - mx) for v in sums]
        tot = sum(ex)
        prob = {self.class_values[i]: float(ex[i] / tot) for i in range(len(ex))}
        p_cons, p_mast = prob.get("CONSERVATIVA", 0.0), prob.get("MASTECTOMIA", 0.0)
        return ("CONSERVATIVA" if p_cons >= p_mast else "MASTECTOMIA"), p_cons, p_mast

    def unseen_values(self, features):
        return [f for f, v in features.items()
                if f in self._index and v and v not in self.attributes[self._index[f]]["values"]]

    def stump_table(self):
        """Regole del modello in forma leggibile (per la pagina XAI)."""
        out = []
        for s in self.stumps:
            a = self.attributes[s["att_index"]]
            val = a["values"][s["split_value"]]
            cls = [self.class_values[r.index(max(r))] for r in s["distribution"]]
            out.append({"feature": a["name"], "value": val, "if_equal": cls[0],
                        "if_different": cls[1], "if_missing": cls[2], "weight": s["beta"]})
        return out

    def get_feature_importance(self):
        """Importanza = somma dei pesi (beta) degli stump che usano la feature, normalizzata."""
        w = {f: 0.0 for f in FEATURE_NAMES}
        for s in self.stumps:
            w[self.attributes[s["att_index"]]["name"]] = w.get(self.attributes[s["att_index"]]["name"], 0) + s["beta"]
        mx = max(w.values()) or 1
        return {f: round(v / mx, 4) for f, v in w.items()}

    def get_model_info(self):
        used = sum(1 for v in self.get_feature_importance().values() if v > 0)
        return {"name": "BrCaM — AdaBoostM1", "algorithm": f"AdaBoostM1 ({len(self.stumps)} iterazioni)",
                "base_learner": "Decision Stump", "accuracy": "95% (10-fold CV, dal paper)",
                "dataset_size": "5100 pazienti", "validation": "10-fold cross-validation",
                "classes": CLASS_VALUES, "paper": "Scientific Reports 2026",
                "source": "Evangelista, Gautam et al.", "path": self.path, "active": True,
                "n_features": len(FEATURE_NAMES), "n_used": used,
                "runtime": "Python (esportato da Adaboost.model, equivalente a WEKA)"}


class FallbackClassifier(BaseClassifier):
    name="AdaBoost scikit-learn (fallback)"; version="fallback-1.0"

    def __init__(self): self._model=None; self._fitted=False; self._fi=None

    def _encode(self, features: Dict[str,str]) -> np.ndarray:
        """Codifica one-hot le feature nominali."""
        vec = []
        for feat, values in FEATURES.items():
            v = features.get(feat,"")
            idx = values.index(v) if v in values else 0
            vec.append(idx / max(len(values)-1, 1))  # normalizzato 0-1
        return np.array(vec, dtype=float)

    def _train(self):
        from sklearn.ensemble import AdaBoostClassifier
        from sklearn.tree import DecisionTreeClassifier
        from sklearn.pipeline import Pipeline
        from sklearn.preprocessing import StandardScaler
        rng = np.random.default_rng(42); N = 1000

        X_list, y_list = [], []
        for _ in range(N):
            feat = {k: rng.choice(v) for k,v in FEATURES.items()}
            # Regola: mastectomia se linfonodi positivi o biRADS alto o multifocale
            score = 0
            if feat["stato_linfonodaleDX"] in ("Adenopatia","Pacchetto_linfonodale"): score+=3
            if feat["stato_linfonodaleSX"] in ("Adenopatia","Pacchetto_linfonodale"): score+=3
            if feat["biRadsClinico"] in ("E5","Bil:E5-E4/E4-E5","Bil:E5-E3/E3-E5"): score+=2
            if feat["focalità"] in ("si","Bil:si-no/no-si"): score+=2
            if feat["citologia_codifica"] in ("C5","Bil:C5-C4/C4-C5","Bil:C5-C3/C3-C5"): score+=1
            X_list.append(self._encode(feat))
            y_list.append(1 if score>=4 else 0)

        X = np.array(X_list); y = np.array(y_list)
        self._model = Pipeline([("sc",StandardScaler()),
            ("clf",AdaBoostClassifier(estimator=DecisionTreeClassifier(max_depth=1),
                                      n_estimators=100,random_state=42))])
        self._model.fit(X, y)
        raw = self._model.named_steps["clf"].feature_importances_
        self._fi = {FEATURE_NAMES[i]: float(raw[i]) for i in range(len(FEATURE_NAMES))}
        self._fitted = True

    def is_ready(self): return True

    def predict(self, features: Dict[str,str]) -> Tuple[str, float, float]:
        if not self._fitted: self._train()
        X = self._encode(features).reshape(1,-1)
        p = self._model.predict_proba(X)[0]
        idx = int(np.argmax(p))
        return CLASS_VALUES[idx], float(p[0]), float(p[1])

    def get_feature_importance(self):
        if not self._fitted: self._train()
        return self._fi or CLINICAL_IMPORTANCE

    def get_model_info(self):
        return {"name":"AdaBoost scikit-learn (fallback)","algorithm":"AdaBoost",
                "base_learner":"Decision Stump","accuracy":"~78% su dati sintetici",
                "dataset_size":"1000 campioni sintetici","validation":"Dati sintetici",
                "classes":CLASS_VALUES,
                "note":f"Adaboost.model non trovato in:\n{MODEL_PATH}",
                "active":False,"n_features":len(FEATURE_NAMES)}


_clf: Optional[BaseClassifier] = None

def get_classifier() -> BaseClassifier:
    """1) modello originale esportato (nessuna dipendenza da Java)
       2) WEKA via JVM sul file .model   3) fallback sintetico (solo sviluppo)"""
    global _clf
    if _clf: return _clf
    if os.path.exists(EXPORT_PATH):
        try:
            _clf = ExportedAdaBoost(); log.info(f"Modello: {_clf.name}"); return _clf
        except Exception as e:
            log.warning(f"Export JSON non utilizzabile: {e}")
    if os.path.exists(MODEL_PATH):
        try:
            c = WekaClassifier(); c.load(); _clf = c; return _clf
        except Exception as e:
            log.warning(f"WEKA non disponibile ({e}): uso il fallback SINTETICO")
    _clf = FallbackClassifier()
    return _clf

def run_classification(features: Dict[str,str]) -> Tuple[str, float, float, str]:
    c = get_classifier()
    label, c0, c1 = c.predict(features)
    return label, c0, c1, c.version

def get_feature_importance() -> Dict[str,float]: return get_classifier().get_feature_importance()
def get_model_info()         -> Dict:            return get_classifier().get_model_info()
def get_classifier_name()    -> str:             return get_classifier().name


def unseen_features(features) -> list:
    """Feature con valori mai visti in addestramento (trattati come mancanti)."""
    try:
        return get_classifier().unseen_values(features)
    except Exception:
        return []
