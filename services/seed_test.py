"""Pazienti di TEST per il Portale (idempotente: non duplica se già presenti).

PT-TEST1  Maria Rossi   — account attivo e verificato, cartella clinica completa,
                          appuntamenti passati/futuri (uno DOMANI per testare il promemoria)
PT-TEST2  Anna Esposito — NON registrata: serve per testare la registrazione
                          (codice di attivazione fisso 482913)
"""
import os
from datetime import datetime, timedelta, time
from werkzeug.security import generate_password_hash
from database.db import session_scope
from database.models import (Patient, ClinicalRecord, ClassificationResult, PatientAccount,
                             Appointment, ClinicalDocument, LabResult)
from services.security import hash_password
from services.timeutil import utcnow, local_now, local_to_utc

TEST_EMAIL    = os.environ.get("BRCAPP_TEST_PATIENT_EMAIL", "maria.rossi.test@example.com")
TEST_PASSWORD = "Portale!2026"
TEST2_ACTIVATION = "482913"

def _local(days: int, hh: int, mm: int = 0) -> datetime:
    d = (local_now() + timedelta(days=days)).date()
    return local_to_utc(datetime.combine(d, time(hh, mm)))

def seed_test_patients():
    with session_scope() as db:
        if db.query(Patient).filter(Patient.code == "PT-TEST1").first():
            return
        # ── PT-TEST1 ──────────────────────────────────────────────────────────
        p = Patient(code="PT-TEST1", first_name="Maria", last_name="Rossi", gender="F",
                    nazionalita="Italiana", birth_date="1971-03-14", birth_place="Napoli (NA)",
                    fiscal_code="RSSMRA71C54F839K", age_range="50-65", blood_type="A",
                    rh_positive=True, phone="+39 333 000 1122",
                    address="Via Toledo 100, 80134 Napoli", initials="M.R.",
                    patient_email=TEST_EMAIL, created_at=utcnow() - timedelta(days=60))
        db.add(p); db.flush()

        db.add(ClinicalRecord(
            patient_id=p.id, peso=64.0, altezza=163.0, bmi=24.1, waist=78.0, hips=99.0, whr=0.79,
            fumo="no", alcohol="no", gravidanza="si", familiarita_carcinoma_ovarico="no",
            previous_cancer="no", previous_breast_cancer="no", previous_chemotherapy="no",
            previous_radiotherapy="no", breast_surgeries="no", autoimmune_diseases="no",
            diabetes="no", keloids="no", familial_breast_cancer="si", brca_mutation="no",
            bra_size="3C", ptosis_degree="Grado I", skin_tropism="Normale",
            struttura_ghiandolare="Displasia_fibroadenosa",
            preoperative_chemotherapy="no", injury_type="Nodulo",
            cancer_site="Quadrante supero-esterno", tumor_size_mm=14.0, injuries_number=1,
            focalita="no", rapporto_cuteDX="Regolare", rapporto_cuteSX="Regolare",
            rapporto_areola_capezzoloDX="Regolare", rapporto_areola_capezzoloSX="Regolare",
            event="Sinistro", dubious_injuries="no", main_cancer_site="Quadrante supero-esterno",
            tumor_in_situ="no", histotype="Carcinoma duttale infiltrante", grading="G2",
            clinical_stage="I", er_status="Positivo", pgr_status="Positivo", ki67=18.0,
            cerbb2="Negativo", classification_pre="Luminale A",
            stato_linfonodaleDX="Normale", stato_linfonodaleSX="Normale",
            biRadsClinico="E4", citologia_codifica="C5", ricostruzione="no"))
        from ml.weka_bridge import run_classification
        f1 = {"età": "50-65", "fumo": "no", "gravidanza": "si", "familiarità_carcinoma_ovarico": "no",
              "struttura_ghiandolare": "Displasia_fibroadenosa", "rapporto_cuteDX": "Regolare",
              "rapporto_cuteSX": "Regolare", "rapporto_areola_capezzoloDX": "Regolare",
              "rapporto_areola_capezzoloSX": "Regolare", "stato_linfonodaleDX": "Normale",
              "stato_linfonodaleSX": "Normale", "biRadsClinico": "E4", "citologia_codifica": "C5",
              "focalità": "no", "ricostruzione": "no"}
        lab, pc, pm, ver = run_classification(f1)
        db.add(ClassificationResult(patient_id=p.id, run_at=utcnow() - timedelta(days=20),
                                    model_version=ver, predicted_class=lab,
                                    confidence_bcs=pc, confidence_mast=pm,
                                    input_snapshot=__import__("json").dumps(f1, ensure_ascii=False)))

        db.add(PatientAccount(patient_id=p.id, email=TEST_EMAIL,
                              password_hash=hash_password(TEST_PASSWORD),
                              email_verified=True, verified_at=utcnow() - timedelta(days=30),
                              consent_privacy_at=utcnow() - timedelta(days=30), consent_email=True))

        # ── Cartella clinica ─────────────────────────────────────────────────
        def doc(cat, title, days_ago, author, dept, body, results=(), released=True, status="final"):
            d = ClinicalDocument(patient_id=p.id, category=cat, title=title,
                                 issued_at=utcnow() - timedelta(days=days_ago), author=author,
                                 department=dept, body=body, status=status,
                                 released_to_patient=released,
                                 released_at=(utcnow() - timedelta(days=days_ago)) if released else None,
                                 created_by="seed")
            for r in results:
                d.results.append(LabResult(analyte=r[0], value=r[1], unit=r[2], ref_range=r[3], flag=r[4]))
            db.add(d)

        doc("VISIT", "Prima visita senologica", 45, "Dott.ssa L. Bianchi", "Breast Unit",
            "Paziente di 55 anni, familiarità per carcinoma mammario (madre). Alla palpazione "
            "nodulo duro-elastico di circa 1,5 cm al QSE della mammella sinistra, mobile sui piani "
            "profondi. Cute e complesso areola-capezzolo regolari. Cavi ascellari liberi.\n"
            "Si richiedono mammografia bilaterale ed ecografia mammaria.")
        doc("IMAGING", "Mammografia bilaterale", 40, "Dott. G. Ferrara", "Radiologia Senologica",
            "Mammelle a struttura fibroadiposa (ACR B). A sinistra, al QSE, opacità nodulare a "
            "margini spiculati di 14 mm con microcalcificazioni associate. Mammella destra nei limiti.\n"
            "Conclusioni: BI-RADS 4 sinistra, BI-RADS 1 destra. Indicato approfondimento bioptico.")
        doc("IMAGING", "Ecografia mammaria e ascellare bilaterale", 40, "Dott. G. Ferrara",
            "Radiologia Senologica",
            "A sinistra, ore 2, formazione ipoecogena irregolare di 13 × 11 mm, con cono d'ombra "
            "posteriore. Linfonodi ascellari bilateralmente di aspetto reattivo, ilo conservato.\n"
            "Conclusioni: U4. Si esegue agobiopsia ecoguidata.")
        doc("LAB", "Emocromo completo", 38, "Laboratorio Analisi", "Patologia Clinica",
            "Esame eseguito su sangue venoso.",
            [("Emoglobina", "12.9", "g/dL", "12.0 – 16.0", "N"),
             ("Globuli bianchi", "6.8", "10³/µL", "4.0 – 10.0", "N"),
             ("Neutrofili", "62", "%", "40 – 75", "N"),
             ("Linfociti", "29", "%", "20 – 45", "N"),
             ("Piastrine", "248", "10³/µL", "150 – 400", "N"),
             ("Glicemia", "104", "mg/dL", "70 – 100", "H"),
             ("Creatinina", "0.78", "mg/dL", "0.50 – 1.10", "N"),
             ("Colesterolo totale", "214", "mg/dL", "< 200", "H")])
        doc("LAB", "Marcatori tumorali", 38, "Laboratorio Analisi", "Patologia Clinica",
            "Valori nei limiti di riferimento.",
            [("CA 15-3", "21.4", "U/mL", "< 31.3", "N"),
             ("CEA", "1.9", "ng/mL", "< 5.0", "N")])
        doc("PATHOLOGY", "Esame istologico su agobiopsia (core biopsy)", 30, "Dott. R. Esposito",
            "Anatomia Patologica",
            "Mammella sinistra, QSE, agobiopsia ecoguidata (3 frustoli).\n"
            "Diagnosi: carcinoma duttale infiltrante (NST), grado istologico G2.\n"
            "Immunoistochimica: ER 90% (positivo), PgR 70% (positivo), Ki-67 18%, "
            "HER2 score 1+ (negativo). Sottotipo surrogato: Luminale A-like.")
        doc("VISIT", "Discussione multidisciplinare (GOM)", 20, "Gruppo Oncologico Multidisciplinare",
            "Breast Unit",
            "Caso discusso in riunione multidisciplinare. Indicazione a intervento chirurgico "
            "conservativo (quadrantectomia) con biopsia del linfonodo sentinella, "
            "seguito da radioterapia. Valutazione oncologica post-operatoria.")
        # Referto non ancora rilasciato: NON deve comparire nel portale
        doc("LAB", "Esami pre-operatori (in validazione)", 2, "Laboratorio Analisi",
            "Patologia Clinica", "Referto in corso di validazione.",
            [("PT INR", "1.02", "", "0.80 – 1.20", "N")], released=False, status="preliminary")

        # ── Appuntamenti ──────────────────────────────────────────────────────
        def appt(start, typ, loc, doctor, instr, status="booked", conf=True):
            db.add(Appointment(patient_id=p.id, start_at=start, duration_min=30,
                               appointment_type=typ, location=loc, clinician=doctor,
                               patient_instructions=instr, status=status, created_by="seed",
                               confirmation_sent_at=utcnow() - timedelta(days=5) if conf else None))
        appt(_local(-41, 9, 30), "Mammografia bilaterale", "Radiologia Senologica — Piano 1",
             "Dott. G. Ferrara", None, "fulfilled")
        appt(_local(-30, 11, 0), "Agobiopsia ecoguidata", "Radiologia Senologica — Piano 1",
             "Dott. G. Ferrara", None, "fulfilled")
        appt(_local(-10, 15, 0), "Visita anestesiologica", "Ambulatorio Pre-ricovero",
             "Dott. P. Romano", None, "cancelled")
        # DOMANI → riceverà il promemoria automatico
        appt(_local(1, 10, 30), "Visita chirurgica pre-operatoria", "Breast Unit — Ambulatorio 3",
             "Dott.ssa L. Bianchi",
             "Portare documento d'identità, tessera sanitaria e tutti i referti in originale.")
        appt(_local(9, 8, 0), "Intervento chirurgico (ricovero)", "Reparto Chirurgia Senologica — Piano 4",
             "Dott.ssa L. Bianchi",
             "Presentarsi a digiuno dalla mezzanotte. Non applicare creme sul torace.")

        # ── PT-TEST2: non registrata (per provare la registrazione) ─────────
        p2 = Patient(code="PT-TEST2", first_name="Anna", last_name="Esposito", gender="F",
                     nazionalita="Italiana", birth_date="1980-07-02", birth_place="Pozzuoli (NA)",
                     fiscal_code="SPSNNA80L42G964T", age_range="37-49", blood_type="0",
                     rh_positive=False, initials="A.E.",
                     patient_pin=generate_password_hash(TEST2_ACTIVATION))
        db.add(p2); db.flush()
        db.add(ClinicalRecord(patient_id=p2.id, fumo="si", gravidanza="no",
                              familiarita_carcinoma_ovarico="no", struttura_ghiandolare="Normale",
                              rapporto_cuteDX="Regolare", rapporto_cuteSX="Regolare",
                              rapporto_areola_capezzoloDX="Regolare", rapporto_areola_capezzoloSX="Regolare",
                              stato_linfonodaleDX="Normale", stato_linfonodaleSX="Normale",
                              biRadsClinico="E3", citologia_codifica="C2", focalita="no",
                              ricostruzione="no"))
        db.add(Appointment(patient_id=p2.id, start_at=_local(6, 9, 0), duration_min=20,
                           appointment_type="Ecografia mammaria di controllo",
                           location="Radiologia Senologica — Piano 1", clinician="Dott. G. Ferrara",
                           created_by="seed"))
    print(f"  🧪  Pazienti di test creati: PT-TEST1 ({TEST_EMAIL} / {TEST_PASSWORD}) · "
          f"PT-TEST2 (attivazione {TEST2_ACTIVATION})")
