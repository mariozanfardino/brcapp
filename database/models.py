# database/models.py — Schema completo con tutte le sezioni del DB clinico
from sqlalchemy import Column, Integer, Float, String, Boolean, DateTime, Text, ForeignKey
from sqlalchemy.orm import declarative_base, relationship
from datetime import datetime

Base = declarative_base()


class Patient(Base):
    """Dati anagrafici (Vital Statistics)."""
    __tablename__ = "patients"
    id            = Column(Integer, primary_key=True, autoincrement=True)
    code          = Column(String(20), unique=True, nullable=False)
    # Anagrafica
    gender        = Column(String(10),  nullable=True, default="F")
    nazionalita   = Column(String(50),  nullable=True, default="Italiana")
    birth_date    = Column(String(10),  nullable=True)   # YYYY-MM-DD
    age_range     = Column(String(10),  nullable=True)   # 18-25 ... Over_75
    blood_type    = Column(String(5),   nullable=True)
    rh_positive   = Column(Boolean,     nullable=True)
    # Metadati app
    created_at    = Column(DateTime, default=datetime.utcnow)
    updated_at    = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    notes         = Column(Text, nullable=True)
    patient_pin   = Column(String(256), nullable=True)
    patient_email = Column(String(120), nullable=True)
    initials      = Column(String(20),  nullable=True)

    clinical        = relationship("ClinicalRecord", back_populates="patient",
                                   uselist=False, cascade="all, delete")
    classifications = relationship("ClassificationResult", back_populates="patient",
                                   cascade="all, delete")

    def to_dict(self):
        d = {"id":self.id,"code":self.code,"gender":self.gender or "F",
             "nazionalita":self.nazionalita or "Italiana",
             "birth_date":self.birth_date or "","age_range":self.age_range or "",
             "blood_type":self.blood_type or "","rh_positive":self.rh_positive,
             "created_at":self.created_at.strftime("%Y-%m-%d") if self.created_at else "",
             "notes":self.notes or "","initials":self.initials or ""}
        if self.clinical:
            d.update(self.clinical.to_dict())
        if self.classifications:
            last = max(self.classifications, key=lambda x: x.run_at)
            d["last_prediction"]     = last.predicted_class
            d["confidence_bcs"]      = last.confidence_bcs
            d["confidence_mast"]     = last.confidence_mast
        else:
            d["last_prediction"] = None
        return d


class ClinicalRecord(Base):
    """
    Dati clinici completi organizzati per sezione.
    Le 15 feature del modello (FEATURE_NAMES in weka_bridge.py) sono
    sottoinsieme di questi campi — NON modificarle.
    """
    __tablename__ = "clinical_records"
    id         = Column(Integer, primary_key=True, autoincrement=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False)

    # ── SEZIONE A: Anamnesi / Clinical History ─────────────────────────────
    peso                    = Column(Float,   nullable=True)
    altezza                 = Column(Float,   nullable=True)
    bmi                     = Column(Float,   nullable=True)
    waist                   = Column(Float,   nullable=True)
    hips                    = Column(Float,   nullable=True)
    whr                     = Column(Float,   nullable=True)
    fumo                    = Column(String(5),  nullable=True)   # si/no (modello)
    alcohol                 = Column(String(5),  nullable=True)
    gravidanza              = Column(String(5),  nullable=True)   # si/no (modello)
    familiarita_carcinoma_ovarico = Column(String(5), nullable=True)  # modello
    previous_cancer         = Column(String(5),  nullable=True)
    previous_breast_cancer  = Column(String(5),  nullable=True)
    previous_chemotherapy   = Column(String(5),  nullable=True)
    previous_radiotherapy   = Column(String(5),  nullable=True)
    breast_surgeries        = Column(String(5),  nullable=True)
    autoimmune_diseases     = Column(String(5),  nullable=True)
    diabetes                = Column(String(5),  nullable=True)
    keloids                 = Column(String(5),  nullable=True)
    familial_breast_cancer  = Column(String(5),  nullable=True)
    brca_mutation           = Column(String(5),  nullable=True)
    bra_size                = Column(String(10), nullable=True)
    ptosis_degree           = Column(String(30), nullable=True)
    skin_tropism            = Column(String(30), nullable=True)
    struttura_ghiandolare   = Column(String(60), nullable=True)   # modello

    # ── SEZIONE B: Dati Clinici / Clinical Data ────────────────────────────
    preoperative_chemotherapy = Column(String(5),  nullable=True)
    injury_type             = Column(String(50), nullable=True)
    cancer_site             = Column(String(30), nullable=True)
    tumor_size_mm           = Column(Float,      nullable=True)
    injuries_number         = Column(Integer,    nullable=True)
    focalita                = Column(String(5),  nullable=True)   # modello (si/no)
    rapporto_cuteDX         = Column(String(40), nullable=True)   # modello
    rapporto_cuteSX         = Column(String(40), nullable=True)   # modello
    rapporto_areola_capezzoloDX = Column(String(40), nullable=True)  # modello
    rapporto_areola_capezzoloSX = Column(String(40), nullable=True)  # modello
    event                   = Column(String(50), nullable=True)
    dubious_injuries        = Column(String(5),  nullable=True)
    main_cancer_site        = Column(String(50), nullable=True)
    tumor_in_situ           = Column(String(5),  nullable=True)

    # ── SEZIONE C: Valutazione specifica K. mammella ───────────────────────
    histotype               = Column(String(50), nullable=True)
    grading                 = Column(String(5),  nullable=True)
    clinical_stage          = Column(String(10), nullable=True)
    er_status               = Column(String(10), nullable=True)
    pgr_status              = Column(String(10), nullable=True)
    ki67                    = Column(Float,      nullable=True)
    cerbb2                  = Column(String(10), nullable=True)
    classification_pre      = Column(String(30), nullable=True)
    stato_linfonodaleDX     = Column(String(40), nullable=True)   # modello
    stato_linfonodaleSX     = Column(String(40), nullable=True)   # modello
    biRadsClinico           = Column(String(30), nullable=True)   # modello
    citologia_codifica      = Column(String(5),  nullable=True)   # modello (si/no)
    ricostruzione           = Column(String(5),  nullable=True)   # modello (si/no)

    # ── SEZIONE D: Diagnosi Pre/Post intervento ────────────────────────────
    t_operation_type        = Column(String(20), nullable=True)
    n_operation_type        = Column(String(20), nullable=True)
    histotype_post          = Column(String(50), nullable=True)
    grading_post            = Column(String(5),  nullable=True)
    clinical_stage_post     = Column(String(10), nullable=True)
    er_post                 = Column(String(10), nullable=True)
    pgr_post                = Column(String(10), nullable=True)
    ki67_post               = Column(Float,      nullable=True)
    cerbb2_post             = Column(String(10), nullable=True)
    classification_post     = Column(String(30), nullable=True)
    nodal_status_post       = Column(String(40), nullable=True)
    surgical_progress       = Column(String(50), nullable=True)
    cosmetic_result         = Column(String(50), nullable=True)

    # ── Target ────────────────────────────────────────────────────────────
    DISEASE = Column(String(20), nullable=True)  # CONSERVATIVA / MASTECTOMIA

    patient = relationship("Patient", back_populates="clinical")

    def to_dict(self):
        return {c.key: getattr(self, c.key)
                for c in self.__table__.columns
                if c.key not in ("id","patient_id")}

    def model_features(self) -> dict:
        """Restituisce solo le 15 feature per il modello WEKA."""
        return {
            "età":                           self.patient.age_range or "",
            "fumo":                          self.fumo or "",
            "gravidanza":                    self.gravidanza or "",
            "familiarità_carcinoma_ovarico": self.familiarita_carcinoma_ovarico or "",
            "struttura_ghiandolare":         self.struttura_ghiandolare or "",
            "rapporto_cuteDX":               self.rapporto_cuteDX or "",
            "rapporto_cuteSX":               self.rapporto_cuteSX or "",
            "rapporto_areola_capezzoloDX":   self.rapporto_areola_capezzoloDX or "",
            "rapporto_areola_capezzoloSX":   self.rapporto_areola_capezzoloSX or "",
            "stato_linfonodaleDX":           self.stato_linfonodaleDX or "",
            "stato_linfonodaleSX":           self.stato_linfonodaleSX or "",
            "biRadsClinico":                 self.biRadsClinico or "",
            "citologia_codifica":            self.citologia_codifica or "",
            "focalità":                      self.focalita or "",
            "ricostruzione":                 self.ricostruzione or "",
        }


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
        return {"id":self.id,
                "patient_code":self.patient.code if self.patient else "",
                "run_at":self.run_at.strftime("%Y-%m-%d %H:%M") if self.run_at else "",
                "predicted_class":self.predicted_class,
                "confidence_bcs":round(self.confidence_bcs*100,1) if self.confidence_bcs else None,
                "confidence_mast":round(self.confidence_mast*100,1) if self.confidence_mast else None,
                "model_version":self.model_version or "N/A"}


class UserGroup(Base):
    __tablename__ = "user_groups"
    id=Column(Integer,primary_key=True,autoincrement=True)
    name=Column(String(60),unique=True,nullable=False)
    role=Column(String(20),nullable=False,default="viewer")
    description=Column(String(200),nullable=True)
    created_at=Column(DateTime,default=datetime.utcnow)
    users=relationship("User",back_populates="group",cascade="all, delete")
    def to_dict(self):
        return {"id":self.id,"name":self.name,"role":self.role,
                "description":self.description or "","user_count":len(self.users)}

class User(Base):
    __tablename__ = "users"
    id=Column(Integer,primary_key=True,autoincrement=True)
    username=Column(String(60),unique=True,nullable=False)
    display_name=Column(String(100),nullable=True)
    email=Column(String(120),nullable=True)
    password_hash=Column(String(256),nullable=False)
    group_id=Column(Integer,ForeignKey("user_groups.id"),nullable=True)
    is_active=Column(Boolean,default=True)
    created_at=Column(DateTime,default=datetime.utcnow)
    last_login=Column(DateTime,nullable=True)
    group=relationship("UserGroup",back_populates="users")
    def to_dict(self):
        return {"id":self.id,"username":self.username,
                "display_name":self.display_name or self.username,
                "email":self.email or "","group_name":self.group.name if self.group else "—",
                "group_role":self.group.role if self.group else "viewer",
                "is_active":self.is_active,
                "created_at":self.created_at.strftime("%Y-%m-%d") if self.created_at else "",
                "last_login":self.last_login.strftime("%Y-%m-%d %H:%M") if self.last_login else "Mai"}
