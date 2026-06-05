# database/migrations.py
import logging
from sqlalchemy import text

log = logging.getLogger(__name__)

# (tabella, colonna, tipo SQL)
MIGRATIONS = [
    ("patients","patient_pin","TEXT"),
    ("patients","patient_email","TEXT"),
    ("patients","initials","TEXT"),
    ("patients","age","INTEGER"),
    ("patients","bmi","REAL"),
    ("user_groups","description","TEXT"),
    # Nuove colonne clinical_records per dati reali CSV
    ("clinical_records","peso","REAL"),
    ("clinical_records","altezza","REAL"),
    ("clinical_records","fumo","INTEGER"),
    ("clinical_records","gravidanza","INTEGER"),
    ("clinical_records","allattamento","INTEGER"),
    ("clinical_records","menopausa","INTEGER"),
    ("clinical_records","casi_vero_famiglia","INTEGER"),
    ("clinical_records","familiarita_carcinoma_ovario","INTEGER"),
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
    ("clinical_records","intervento_chirurgico_bilaterale","INTEGER"),
    ("clinical_records","ricostruzione","INTEGER"),
    ("clinical_records","DISEASE","TEXT"),
]

def run(engine):
    with engine.connect() as conn:
        # Crea tabelle se non esistono
        from database.models import Base
        Base.metadata.create_all(engine)

        for table, column, col_type in MIGRATIONS:
            try:
                rows = conn.execute(text(f"PRAGMA table_info({table})")).fetchall()
                existing = [r[1] for r in rows]
                if column not in existing:
                    conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {col_type}"))
                    log.info(f"Migrazione: {table}.{column}")
            except Exception as e:
                log.warning(f"Migrazione skip {table}.{column}: {e}")
        conn.commit()
    log.info("Migrazioni OK")
