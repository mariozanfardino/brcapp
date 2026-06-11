# database/migrations.py — colonne esatte da global_new.csv
import logging
from sqlalchemy import text
log = logging.getLogger(__name__)

MIGRATIONS = [
    # patients
    ("patients","initials","TEXT"),
    ("patients","patient_pin","TEXT"),
    ("patients","patient_email","TEXT"),
    # user_groups
    ("user_groups","description","TEXT"),
    # clinical_records — 22 feature + DISEASE
    ("clinical_records","peso","REAL"),
    ("clinical_records","altezza","REAL"),
    ("clinical_records","fumo","REAL"),
    ("clinical_records","gravidanza","REAL"),
    ("clinical_records","allattamento","REAL"),
    ("clinical_records","menopausa","REAL"),
    ("clinical_records","casi_vero_famiglia","REAL"),
    ("clinical_records","familiarita_carcinoma_ovario","REAL"),
    ("clinical_records","struttura_ghiandolare","REAL"),
    ("clinical_records","rapporto_cuteDX","REAL"),
    ("clinical_records","rapporto_cuteSX","REAL"),
    ("clinical_records","rapporto_areola_capezzolooDX","REAL"),
    ("clinical_records","rapporto_areola_capezzoloSX","REAL"),
    ("clinical_records","stato_linfonodaleXX","REAL"),
    ("clinical_records","stato_linfondaleXX","REAL"),
    ("clinical_records","biRadioClinico","REAL"),
    ("clinical_records","citologia","REAL"),
    ("clinical_records","citologia_codifica","REAL"),
    ("clinical_records","focalita","REAL"),
    ("clinical_records","lato_intervento","REAL"),
    ("clinical_records","intervento_chirurgico_bilaterale","REAL"),
    ("clinical_records","ricostruzione","REAL"),
    ("clinical_records","DISEASE","TEXT"),
]

def run(engine):
    with engine.connect() as conn:
        from database.models import Base
        Base.metadata.create_all(engine)
        for table, column, col_type in MIGRATIONS:
            try:
                rows = conn.execute(text(f"PRAGMA table_info({table})")).fetchall()
                if column not in [r[1] for r in rows]:
                    conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {col_type}"))
                    log.info(f"Migrazione: {table}.{column}")
            except Exception as e:
                log.debug(f"Skip {table}.{column}: {e}")
        conn.commit()
