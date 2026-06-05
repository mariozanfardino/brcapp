#!/usr/bin/env python3
"""
import_csv.py — Importa global_new.csv in BrCapp
Uso: python3 scripts/import_csv.py [--csv PATH] [--preview] [--reimport]
"""
import sys, os, argparse
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import pandas as pd
import database.db as db_module
from database.db import session_scope
from database.models import Patient, ClinicalRecord
from config import DB_PATH

CSV_DEFAULT = "/home/zanfardino/mnt/dev/BOSP/original_data/patients_attributes_list/global_new.csv"

NUMERIC_COLS = [
    "peso","altezza","struttura_ghiandolare",
    "rapporto_cuteDX","rapporto_cuteSX",
    "rapporto_areola_capezzolooDX","rapporto_areola_capezzoloSX",
    "stato_linfonodaleXX","stato_linfondaleXX",
    "biRadioClinico","citologia","citologia_codifica",
    "focalita","lato_intervento",
]
BINARY_COLS = [
    "fumo","gravidanza","allattamento","menopausa",
    "casi_vero_famiglia","familiarita_carcinoma_ovario",
    "intervento_chirurgico_bilaterale","ricostruzione",
]

def read_csv(path):
    """Legge il CSV provando tutti gli encoding e separatori."""
    encodings = ["utf-8", "latin-1", "iso-8859-1", "cp1252", "utf-8-sig"]
    separators = [",", ";", "\t", "|", " "]
    last_err = None
    for enc in encodings:
        for sep in separators:
            try:
                df = pd.read_csv(path, sep=sep, encoding=enc, nrows=5)
                if len(df.columns) <= 1:
                    continue  # separatore sbagliato
                # Lettura completa
                df = pd.read_csv(path, sep=sep, encoding=enc,
                                 on_bad_lines="skip", low_memory=False)
                print(f"  Encoding: {enc}  ·  Separatore: '{sep}'  ·  Colonne: {len(df.columns)}")
                return df, enc, sep
            except Exception as e:
                last_err = e
                continue
    raise ValueError(f"Impossibile leggere il CSV. Ultimo errore: {last_err}")

def sf(v):
    try: return float(v) if pd.notna(v) else None
    except: return None

def si(v):
    try: return int(float(v)) if pd.notna(v) else None
    except: return None

def run(csv_path, preview=False, skip_existing=True, silent=False):
    def log(msg):
        if not silent: print(msg)

    log(f"\n  Lettura: {csv_path}")
    df, enc, sep = read_csv(csv_path)
    log(f"  {len(df)} righe · {len(df.columns)} colonne · sep='{sep}'")
    log(f"  Colonne: {list(df.columns)}")

    if preview:
        print(df.head(5).to_string())
        return 0

    db_module.setup(DB_PATH)
    ok = skip = err = 0

    for idx, row in df.iterrows():
        id_col = next((c for c in ["id","ID","paziente_id","patient_id"] if c in df.columns), None)
        code   = f"PT-{int(row[id_col]):05d}" if id_col else f"PT-{idx+1:05d}"

        try:
            with session_scope() as db:
                ex = db.query(Patient).filter(Patient.code == code).first()
                if ex and skip_existing:
                    skip += 1; continue

                p = ex or Patient(code=code)
                if not ex: db.add(p)
                db.flush()

                if ex:
                    old = db.query(ClinicalRecord).filter(
                        ClinicalRecord.patient_id == p.id).first()
                    if old: db.delete(old)

                cr = ClinicalRecord(patient_id=p.id)
                for col in NUMERIC_COLS:
                    if col in df.columns and hasattr(cr, col):
                        setattr(cr, col, sf(row.get(col)))
                for col in BINARY_COLS:
                    if col in df.columns and hasattr(cr, col):
                        setattr(cr, col, si(row.get(col)))
                if "DISEASE" in df.columns:
                    cr.DISEASE = str(row["DISEASE"]) if pd.notna(row.get("DISEASE")) else None
                db.add(cr)
            ok += 1
            if ok % 500 == 0: log(f"    {ok} importati…")
        except Exception as e:
            print(f"    Errore riga {idx}: {e}"); err += 1

    log(f"\n  RISULTATO: {ok} importati · {skip} saltati · {err} errori\n")
    return ok


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv",     default=CSV_DEFAULT)
    ap.add_argument("--preview", action="store_true")
    ap.add_argument("--reimport",action="store_true")
    args = ap.parse_args()
    if not os.path.exists(args.csv):
        print(f"  File non trovato: {args.csv}"); sys.exit(1)
    run(args.csv, preview=args.preview, skip_existing=not args.reimport)
