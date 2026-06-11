import logging
from sqlalchemy import text
log = logging.getLogger(__name__)

MIGRATIONS = [
    # patients
    ("patients","gender","TEXT"),("patients","nazionalita","TEXT"),
    ("patients","birth_date","TEXT"),("patients","age_range","TEXT"),
    ("patients","blood_type","TEXT"),("patients","rh_positive","INTEGER"),
    ("patients","initials","TEXT"),("patients","patient_pin","TEXT"),
    ("patients","patient_email","TEXT"),
    # user_groups
    ("user_groups","description","TEXT"),
    # clinical_records — anamnesi
    ("clinical_records","peso","REAL"),("clinical_records","altezza","REAL"),
    ("clinical_records","bmi","REAL"),("clinical_records","waist","REAL"),
    ("clinical_records","hips","REAL"),("clinical_records","whr","REAL"),
    ("clinical_records","fumo","TEXT"),("clinical_records","alcohol","TEXT"),
    ("clinical_records","gravidanza","TEXT"),
    ("clinical_records","familiarita_carcinoma_ovarico","TEXT"),
    ("clinical_records","previous_cancer","TEXT"),
    ("clinical_records","previous_breast_cancer","TEXT"),
    ("clinical_records","previous_chemotherapy","TEXT"),
    ("clinical_records","previous_radiotherapy","TEXT"),
    ("clinical_records","breast_surgeries","TEXT"),
    ("clinical_records","autoimmune_diseases","TEXT"),
    ("clinical_records","diabetes","TEXT"),("clinical_records","keloids","TEXT"),
    ("clinical_records","familial_breast_cancer","TEXT"),
    ("clinical_records","brca_mutation","TEXT"),
    ("clinical_records","bra_size","TEXT"),("clinical_records","ptosis_degree","TEXT"),
    ("clinical_records","skin_tropism","TEXT"),
    ("clinical_records","struttura_ghiandolare","TEXT"),
    # clinical data
    ("clinical_records","preoperative_chemotherapy","TEXT"),
    ("clinical_records","injury_type","TEXT"),("clinical_records","cancer_site","TEXT"),
    ("clinical_records","tumor_size_mm","REAL"),
    ("clinical_records","injuries_number","INTEGER"),
    ("clinical_records","focalita","TEXT"),
    ("clinical_records","rapporto_cuteDX","TEXT"),("clinical_records","rapporto_cuteSX","TEXT"),
    ("clinical_records","rapporto_areola_capezzoloDX","TEXT"),
    ("clinical_records","rapporto_areola_capezzoloSX","TEXT"),
    ("clinical_records","event","TEXT"),("clinical_records","dubious_injuries","TEXT"),
    ("clinical_records","main_cancer_site","TEXT"),("clinical_records","tumor_in_situ","TEXT"),
    # breast cancer eval
    ("clinical_records","histotype","TEXT"),("clinical_records","grading","TEXT"),
    ("clinical_records","clinical_stage","TEXT"),("clinical_records","er_status","TEXT"),
    ("clinical_records","pgr_status","TEXT"),("clinical_records","ki67","REAL"),
    ("clinical_records","cerbb2","TEXT"),("clinical_records","classification_pre","TEXT"),
    ("clinical_records","stato_linfonodaleDX","TEXT"),
    ("clinical_records","stato_linfonodaleSX","TEXT"),
    ("clinical_records","biRadsClinico","TEXT"),
    ("clinical_records","citologia_codifica","TEXT"),
    ("clinical_records","ricostruzione","TEXT"),
    # pre/post
    ("clinical_records","t_operation_type","TEXT"),("clinical_records","n_operation_type","TEXT"),
    ("clinical_records","histotype_post","TEXT"),("clinical_records","grading_post","TEXT"),
    ("clinical_records","clinical_stage_post","TEXT"),("clinical_records","er_post","TEXT"),
    ("clinical_records","pgr_post","TEXT"),("clinical_records","ki67_post","REAL"),
    ("clinical_records","cerbb2_post","TEXT"),("clinical_records","classification_post","TEXT"),
    ("clinical_records","nodal_status_post","TEXT"),
    ("clinical_records","surgical_progress","TEXT"),("clinical_records","cosmetic_result","TEXT"),
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
            except Exception as e:
                log.debug(f"Skip {table}.{column}: {e}")
        conn.commit()
