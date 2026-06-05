# database/models.py
from sqlalchemy import (Column, Integer, Float, String, Boolean,
                        DateTime, Text, ForeignKey)
from sqlalchemy.orm import declarative_base, relationship
from datetime import datetime
import enum

Base = declarative_base()

# ── Paziente ──────────────────────────────────────────────────────────────────
class Patient(Base):
    __tablename__ = "patients"
    id           = Column(Integer, primary_key=True, autoincrement=True)
    code         = Column(String(20), unique=True, nullable=False)
    initials     = Column(String(20), nullable=True)   # opzionale
    age          = Column(Integer,    nullable=True)   # opzionale (non nel CSV)
    bmi          = Column(Float,      nullable=True)   # opzionale
    created_at   = Column(DateTime, default=datetime.utcnow)
    updated_at   = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    notes        = Column(Text, nullable=True)
    patient_pin  = Column(String(256), nullable=True)
    patient_email= Column(String(120), nullable=True)

    clinical     = relationship("ClinicalRecord", back_populates="patient",
                                uselist=False, cascade="all, delete")
    classifications = relationship("ClassificationResult", back_populates="patient",
                                   cascade="all, delete")

    def to_dict(self):
        d = {
            "id":       self.id,
            "code":     self.code,
            "initials": self.initials or "",
            "age":      self.age,
            "bmi":      self.bmi,
            "created_at": self.created_at.strftime("%Y-%m-%d") if self.created_at else "",
        }
        if self.clinical:
            d.update(self.clinical.to_dict())
        return d


# ── Dati clinici reali (colonne CSV global_new.csv) ───────────────────────────
class ClinicalRecord(Base):
    __tablename__ = "clinical_records"
    id         = Column(Integer, primary_key=True, autoincrement=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False)

    # Antropometrici
    peso    = Column(Float, nullable=True)      # kg
    altezza = Column(Float, nullable=True)      # cm
    # BMI calcolato
    @property
    def bmi(self):
        if self.peso and self.altezza and self.altezza > 0:
            return round(self.peso / ((self.altezza/100)**2), 1)
        return None

    # Anamnesi
    fumo                       = Column(Integer, nullable=True)  # 0/1
    gravidanza                 = Column(Integer, nullable=True)
    allattamento               = Column(Integer, nullable=True)
    menopausa                  = Column(Integer, nullable=True)
    casi_vero_famiglia         = Column(Integer, nullable=True)
    familiarita_carcinoma_ovario = Column(Integer, nullable=True)

    # Imaging / clinica
    struttura_ghiandolare       = Column(Float, nullable=True)
    rapporto_cuteDX             = Column(Float, nullable=True)
    rapporto_cuteSX             = Column(Float, nullable=True)
    rapporto_areola_capezzolooDX= Column(Float, nullable=True)
    rapporto_areola_capezzoloSX = Column(Float, nullable=True)
    stato_linfonodaleXX         = Column(Float, nullable=True)   # DX
    stato_linfondaleXX          = Column(Float, nullable=True)   # SX
    biRadioClinico              = Column(Float, nullable=True)   # BI-RADS
    citologia                   = Column(Float, nullable=True)
    citologia_codifica          = Column(Float, nullable=True)

    # Chirurgia
    focalita                        = Column(Float, nullable=True)
    lato_intervento                 = Column(Float, nullable=True)
    intervento_chirurgico_bilaterale= Column(Float, nullable=True)
    ricostruzione                   = Column(Float, nullable=True)

    # Target
    DISEASE = Column(String(20), nullable=True)  # BCS / Mastectomy / altro

    patient = relationship("Patient", back_populates="clinical")

    def to_dict(self):
        return {c.key: getattr(self, c.key)
                for c in self.__table__.columns
                if c.key not in ("id","patient_id")}


# ── Risultato classificazione ─────────────────────────────────────────────────
class ClassificationResult(Base):
    __tablename__ = "classification_results"
    id              = Column(Integer, primary_key=True, autoincrement=True)
    patient_id      = Column(Integer, ForeignKey("patients.id"), nullable=False)
    run_at          = Column(DateTime, default=datetime.utcnow)
    model_version   = Column(String(50), nullable=True)
    predicted_class = Column(String(20), nullable=False)
    confidence_bcs  = Column(Float, nullable=True)
    confidence_mast = Column(Float, nullable=True)
    input_snapshot  = Column(Text, nullable=True)
    clinician_notes = Column(Text, nullable=True)

    patient = relationship("Patient", back_populates="classifications")

    def to_dict(self):
        return {
            "id": self.id,
            "patient_code": self.patient.code if self.patient else "",
            "run_at": self.run_at.strftime("%Y-%m-%d %H:%M") if self.run_at else "",
            "predicted_class": self.predicted_class,
            "confidence_bcs":  round(self.confidence_bcs*100,1) if self.confidence_bcs else None,
            "confidence_mast": round(self.confidence_mast*100,1) if self.confidence_mast else None,
            "model_version":   self.model_version or "N/A",
        }


# ── Auth ──────────────────────────────────────────────────────────────────────
class UserGroup(Base):
    __tablename__ = "user_groups"
    id          = Column(Integer, primary_key=True, autoincrement=True)
    name        = Column(String(60), unique=True, nullable=False)
    role        = Column(String(20), nullable=False, default="viewer")
    description = Column(String(200), nullable=True)
    created_at  = Column(DateTime, default=datetime.utcnow)
    users       = relationship("User", back_populates="group", cascade="all, delete")
    def to_dict(self):
        return {"id":self.id,"name":self.name,"role":self.role,
                "description":self.description or "","user_count":len(self.users)}

class User(Base):
    __tablename__ = "users"
    id            = Column(Integer, primary_key=True, autoincrement=True)
    username      = Column(String(60), unique=True, nullable=False)
    display_name  = Column(String(100), nullable=True)
    email         = Column(String(120), nullable=True)
    password_hash = Column(String(256), nullable=False)
    group_id      = Column(Integer, ForeignKey("user_groups.id"), nullable=True)
    is_active     = Column(Boolean, default=True)
    created_at    = Column(DateTime, default=datetime.utcnow)
    last_login    = Column(DateTime, nullable=True)
    group         = relationship("UserGroup", back_populates="users")
    def to_dict(self):
        return {"id":self.id,"username":self.username,
                "display_name":self.display_name or self.username,
                "email":self.email or "","group_name":self.group.name if self.group else "—",
                "group_role":self.group.role if self.group else "viewer",
                "is_active":self.is_active,
                "created_at":self.created_at.strftime("%Y-%m-%d") if self.created_at else "",
                "last_login":self.last_login.strftime("%Y-%m-%d %H:%M") if self.last_login else "Mai"}
