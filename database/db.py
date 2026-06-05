# database/db.py
import os, json, datetime
from contextlib import contextmanager
from typing import List, Optional, Dict, Any

from sqlalchemy import create_engine, event, func, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import NullPool

from database.models import Base, Patient, ClinicalRecord, ClassificationResult, User, UserGroup

_engine       = None
_SessionLocal = None

def _on_connect(dbapi_conn, _):
    cur = dbapi_conn.cursor()
    cur.execute("PRAGMA busy_timeout=5000")
    cur.execute("PRAGMA foreign_keys=ON")
    cur.close()

def setup(db_path: str):
    global _engine, _SessionLocal
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    _engine = create_engine(f"sqlite:///{db_path}", echo=False,
                            poolclass=NullPool,
                            connect_args={"check_same_thread": False})
    event.listen(_engine, "connect", _on_connect)
    Base.metadata.create_all(_engine)
    from database.migrations import run as run_migrations
    run_migrations(_engine)
    _SessionLocal = sessionmaker(bind=_engine, autoflush=False, autocommit=False)

@contextmanager
def session_scope():
    db: Session = _SessionLocal()
    try:
        yield db; db.commit()
    except Exception:
        db.rollback(); raise
    finally:
        db.close()

@contextmanager
def read_scope():
    db: Session = _SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ── Patient Repository ────────────────────────────────────────────────────────
class PatientRepository:

    @staticmethod
    def get_all(search: str = "") -> List[Dict]:
        with read_scope() as db:
            q = db.query(Patient)
            if search:
                q = q.filter(Patient.code.ilike(f"%{search}%"))
            rows = q.order_by(Patient.created_at.desc()).all()
            result = []
            for p in rows:
                d = p.to_dict()
                if p.classifications:
                    last = max(p.classifications, key=lambda x: x.run_at)
                    d["last_prediction"]      = last.predicted_class
                    d["last_confidence_bcs"]  = last.confidence_bcs
                    d["last_confidence_mast"] = last.confidence_mast
                else:
                    d["last_prediction"] = None
                result.append(d)
            return result

    @staticmethod
    def get_by_id(pid: int) -> Optional[Dict]:
        with read_scope() as db:
            p = db.query(Patient).filter(Patient.id == pid).first()
            return p.to_dict() if p else None

    @staticmethod
    def delete(pid: int):
        with session_scope() as db:
            p = db.query(Patient).filter(Patient.id == pid).first()
            if p: db.delete(p)

    @staticmethod
    def update(pid: int, data: Dict[str, Any]):
        with session_scope() as db:
            p = db.query(Patient).filter(Patient.id == pid).first()
            if not p: return
            if "notes" in data: p.notes = data["notes"]
            p.updated_at = datetime.datetime.utcnow()
            if p.clinical:
                for k, v in data.items():
                    if hasattr(p.clinical, k) and k not in ("id","patient_id"):
                        setattr(p.clinical, k, v)


# ── Classification Repository ─────────────────────────────────────────────────
class ClassificationRepository:

    @staticmethod
    def save(patient_id, predicted, conf_bcs, conf_mast, model_ver, input_snap, notes=""):
        with session_scope() as db:
            cr = ClassificationResult(
                patient_id=patient_id, predicted_class=predicted,
                confidence_bcs=conf_bcs, confidence_mast=conf_mast,
                model_version=model_ver,
                input_snapshot=json.dumps(input_snap),
                clinician_notes=notes,
            )
            db.add(cr); db.flush()
            return cr.to_dict()

    @staticmethod
    def get_all() -> List[Dict]:
        with read_scope() as db:
            rows = db.query(ClassificationResult)\
                     .order_by(ClassificationResult.run_at.desc()).all()
            return [r.to_dict() for r in rows]


# ── Statistics Repository ─────────────────────────────────────────────────────
class StatisticsRepository:

    @staticmethod
    def get_summary() -> Dict[str, Any]:
        with read_scope() as db:
            total_p = db.query(func.count(Patient.id)).scalar() or 0
            total_c = db.query(func.count(ClassificationResult.id)).scalar() or 0
            bcs     = db.query(func.count(ClassificationResult.id))                        .filter(ClassificationResult.predicted_class=="BCS").scalar() or 0
            mast    = db.query(func.count(ClassificationResult.id))                        .filter(ClassificationResult.predicted_class=="Mastectomy").scalar() or 0

            # BMI calcolato in Python (SQLite non ha POW standard)
            rows = db.query(ClinicalRecord.peso, ClinicalRecord.altezza)                     .filter(ClinicalRecord.peso != None,
                             ClinicalRecord.altezza != None,
                             ClinicalRecord.altezza > 0).limit(500).all()
            bmis = [p/((h/100)**2) for p,h in rows if h > 0]
            avg_bmi = round(sum(bmis)/len(bmis), 1) if bmis else 0

            # DISEASE dal campo clinico (chirurgia effettiva)
            bcs_real  = db.query(func.count(ClinicalRecord.id))                          .filter(ClinicalRecord.DISEASE == "BCS").scalar() or 0
            mast_real = db.query(func.count(ClinicalRecord.id))                          .filter(ClinicalRecord.DISEASE == "Mastectomy").scalar() or 0

            return {
                "total_patients":        total_p,
                "total_classifications": total_c,
                "bcs_count":             bcs or bcs_real,
                "mastectomy_count":      mast or mast_real,
                "avg_age":               0,
                "avg_bmi":               avg_bmi,
                "avg_tumor_size":        0,
            }

    @staticmethod
    def get_age_distribution() -> List:
        return []   # età non più nel dataset

    @staticmethod
    def get_bmi_distribution() -> List:
        with read_scope() as db:
            rows = db.query(ClinicalRecord.peso, ClinicalRecord.altezza).all()
            bmis = []
            for peso, altezza in rows:
                if peso and altezza and altezza > 0:
                    bmis.append(round(peso / ((altezza/100)**2), 1))
            return bmis

    @staticmethod
    def get_grade_distribution() -> Dict:
        with read_scope() as db:
            # biRadioClinico come proxy del grado
            rows = db.query(ClinicalRecord.biRadioClinico,
                            func.count(ClinicalRecord.id))\
                     .group_by(ClinicalRecord.biRadioClinico)\
                     .filter(ClinicalRecord.biRadioClinico != None).all()
            return {f"BI-RADS {int(r[0])}": r[1] for r in rows if r[0]}

    @staticmethod
    def get_prediction_trend() -> List[Dict]:
        with read_scope() as db:
            rows = db.query(
                func.strftime("%Y-%m", ClassificationResult.run_at).label("month"),
                ClassificationResult.predicted_class,
                func.count(ClassificationResult.id).label("cnt"),
            ).group_by("month", ClassificationResult.predicted_class)\
             .order_by("month").all()
            return [{"month": r[0], "class": r[1], "count": r[2]} for r in rows]

    @staticmethod
    def get_eating_vs_prediction() -> List[Dict]:
        with read_scope() as db:
            rows = db.query(ClinicalRecord.fumo,
                            ClassificationResult.predicted_class)\
                     .join(Patient, Patient.id == ClinicalRecord.patient_id)\
                     .join(ClassificationResult,
                           ClassificationResult.patient_id == Patient.id)\
                     .filter(ClinicalRecord.fumo != None).all()
            return [{"score": r[0], "class": r[1]} for r in rows]
