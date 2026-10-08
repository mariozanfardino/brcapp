"""Accesso dati per Portale Paziente e Agenda staff."""
import re
from database.db import session_scope, read_scope
from database.models import (Patient, ClinicalRecord, PatientAccount, Appointment,
                             ClinicalDocument, LabResult, EmailLog, AuditLog)
from services.security import (hash_password, verify_password, is_locked,
                               register_failure, register_success, validate_password)
from services.timeutil import utcnow

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]{2,}$")
CATEGORY_LABEL = {"LAB": "Esami di laboratorio", "IMAGING": "Diagnostica per immagini",
                  "PATHOLOGY": "Anatomia patologica", "VISIT": "Visita / Consulenza",
                  "OTHER": "Altro"}
STATUS_LABEL = {"booked": "Confermato", "cancelled": "Annullato",
                "fulfilled": "Effettuato", "noshow": "Non presentato"}


class PortalError(Exception):
    pass


# ── Account paziente ──────────────────────────────────────────────────────────
def register_account(code: str, activation: str, email: str, password: str | None,
                     consent_privacy: bool, consent_email: bool, oauth: dict | None = None):
    """Registra l'account collegandolo alla cartella tramite codice paziente +
    codice di attivazione monouso rilasciato dalla struttura.
    Ritorna (account_id, needs_email_verification)."""
    from werkzeug.security import check_password_hash
    code = (code or "").strip().upper()
    email = (email or "").strip().lower()
    if not consent_privacy:
        raise PortalError("È necessario prendere visione dell'informativa privacy.")
    if not EMAIL_RE.match(email):
        raise PortalError("Indirizzo email non valido.")
    if not oauth:
        err = validate_password(password or "", email)
        if err:
            raise PortalError(err)
    with session_scope() as db:
        p = db.query(Patient).filter(Patient.code == code).first()
        # Messaggio unico: non rivela se il codice paziente esiste
        if not p or not p.patient_pin or not check_password_hash(p.patient_pin, (activation or "").strip()):
            raise PortalError("Codice paziente o codice di attivazione non validi.")
        if db.query(PatientAccount).filter(PatientAccount.patient_id == p.id).first():
            raise PortalError("Esiste già un account per questo paziente. Usa 'Accedi' o il recupero password.")
        if db.query(PatientAccount).filter(PatientAccount.email == email).first():
            raise PortalError("Questo indirizzo email è già registrato.")
        verified = bool(oauth and oauth.get("email_verified") and oauth.get("email") == email)
        acc = PatientAccount(
            patient_id=p.id, email=email,
            password_hash=hash_password(password) if password else None,
            email_verified=verified, verified_at=utcnow() if verified else None,
            oauth_provider=(oauth or {}).get("provider"), oauth_subject=(oauth or {}).get("sub"),
            consent_privacy_at=utcnow(), consent_email=bool(consent_email))
        db.add(acc)
        p.patient_pin = None              # codice di attivazione monouso
        p.patient_email = email
        db.flush()
        return acc.id, not verified


def authenticate(email: str, password: str):
    """Ritorna (account_id, patient_id) oppure solleva PortalError con messaggio generico.
    Nota: l'errore va sollevato DOPO il commit, altrimenti il rollback annullerebbe
    il conteggio dei tentativi falliti (e quindi il lockout)."""
    generic = "Email o password non corretti."
    email = (email or "").strip().lower()
    error, result = None, None
    with session_scope() as db:
        acc = db.query(PatientAccount).filter(PatientAccount.email == email).first()
        if not acc:
            verify_password(hash_password("dummy-timing"), password)   # tempo costante
            error = generic
        elif is_locked(acc):
            error = "Troppi tentativi falliti. Riprova tra qualche minuto."
        elif not verify_password(acc.password_hash, password):
            register_failure(acc)                                      # persistito dal commit
            error = ("Troppi tentativi falliti. Riprova tra qualche minuto."
                     if is_locked(acc) else generic)
        elif not acc.is_active:
            error = "Account disabilitato. Contatta la struttura."
        elif not acc.email_verified:
            error = "Devi prima confermare il tuo indirizzo email (controlla la posta)."
        else:
            register_success(acc)
            result = (acc.id, acc.patient_id)
    if error:
        raise PortalError(error)
    return result


def find_account_by_email(email: str):
    with read_scope() as db:
        acc = db.query(PatientAccount).filter(
            PatientAccount.email == (email or "").strip().lower()).first()
        return (acc.id, acc.email_verified) if acc else (None, False)


def reset_password(account_id: int, fingerprint: str, new_password: str):
    with session_scope() as db:
        acc = db.get(PatientAccount, account_id)
        if not acc or (acc.password_hash or "")[-12:] != fingerprint:
            raise PortalError("Link non più valido. Richiedi un nuovo reset.")
        err = validate_password(new_password, acc.email)
        if err:
            raise PortalError(err)
        acc.password_hash = hash_password(new_password)
        acc.failed_logins, acc.locked_until = 0, None
        if not acc.email_verified:                 # il link è arrivato su quella casella
            acc.email_verified, acc.verified_at = True, utcnow()


def set_email_consent(account_id: int, value: bool):
    with session_scope() as db:
        acc = db.get(PatientAccount, account_id)
        if acc:
            acc.consent_email = bool(value)


# ── Lettura portale ───────────────────────────────────────────────────────────
def profile(account_id: int, patient_id: int) -> dict:
    with read_scope() as db:
        p = db.get(Patient, patient_id)
        acc = db.get(PatientAccount, account_id)
        cr = db.query(ClinicalRecord).filter(ClinicalRecord.patient_id == patient_id).first()
        return {
            "code": p.code, "first_name": p.first_name or "", "last_name": p.last_name or "",
            "gender": p.gender or "", "birth_date": p.birth_date or "", "birth_place": p.birth_place or "",
            "fiscal_code": p.fiscal_code or "", "nazionalita": p.nazionalita or "",
            "blood": f"{p.blood_type or '—'} {'Rh+' if p.rh_positive else 'Rh-'}" if p.blood_type else "—",
            "phone": p.phone or "", "address": p.address or "",
            "email": acc.email, "consent_email": acc.consent_email,
            "consent_privacy_at": acc.consent_privacy_at, "last_login": acc.last_login,
            "auth_provider": acc.oauth_provider,
            "peso": cr.peso if cr else None, "altezza": cr.altezza if cr else None,
            "bmi": cr.bmi if cr else None,
        }


def documents(patient_id: int, released_only: bool = True) -> list:
    with read_scope() as db:
        q = db.query(ClinicalDocument).filter(ClinicalDocument.patient_id == patient_id)
        if released_only:
            q = q.filter(ClinicalDocument.released_to_patient == True)
        out = []
        for d in q.order_by(ClinicalDocument.issued_at.desc()).all():
            out.append({"id": d.id, "category": d.category,
                        "category_label": CATEGORY_LABEL.get(d.category, d.category),
                        "title": d.title, "issued_at": d.issued_at, "author": d.author or "",
                        "department": d.department or "", "body": d.body or "",
                        "status": d.status, "released": d.released_to_patient,
                        "results": [{"analyte": r.analyte, "value": r.value, "unit": r.unit or "",
                                     "ref_range": r.ref_range or "", "flag": r.flag or "N"}
                                    for r in d.results]})
        return out


def appointments(patient_id: int | None = None, upcoming_only: bool = False) -> list:
    with read_scope() as db:
        q = db.query(Appointment)
        if patient_id:
            q = q.filter(Appointment.patient_id == patient_id)
        if upcoming_only:
            q = q.filter(Appointment.start_at >= utcnow(), Appointment.status == "booked")
        rows = q.order_by(Appointment.start_at.asc() if upcoming_only else Appointment.start_at.desc()).all()
        out = []
        for a in rows:
            acc = db.query(PatientAccount).filter(PatientAccount.patient_id == a.patient_id).first()
            out.append({"id": a.id, "patient_id": a.patient_id, "patient_code": a.patient.code,
                        "start_at": a.start_at, "duration_min": a.duration_min,
                        "type": a.appointment_type, "location": a.location or "",
                        "clinician": a.clinician or "", "instructions": a.patient_instructions or "",
                        "status": a.status, "status_label": STATUS_LABEL.get(a.status, a.status),
                        "confirmation_sent_at": a.confirmation_sent_at,
                        "reminder_sent_at": a.reminder_sent_at,
                        "notifiable": bool(acc and acc.email_verified and acc.consent_email)})
        return out


# ── Operazioni staff ──────────────────────────────────────────────────────────
def create_appointment(patient_id, start_utc, duration, appt_type, location, clinician,
                       instructions, created_by) -> int:
    if start_utc <= utcnow():
        raise PortalError("La data dell'appuntamento deve essere futura.")
    with session_scope() as db:
        if not db.get(Patient, patient_id):
            raise PortalError("Paziente non trovato.")
        a = Appointment(patient_id=patient_id, start_at=start_utc, duration_min=int(duration or 30),
                        appointment_type=appt_type, location=location, clinician=clinician,
                        patient_instructions=instructions, created_by=created_by)
        db.add(a); db.flush()
        return a.id


def cancel_appointment(appt_id: int) -> bool:
    with session_scope() as db:
        a = db.get(Appointment, appt_id)
        if not a or a.status != "booked":
            return False
        a.status, a.cancelled_at = "cancelled", utcnow()
        return True


def parse_lab_lines(text: str) -> list:
    """Righe formato: analita ; valore ; unità ; range ; flag(H/L/N opz.)"""
    out = []
    for line in (text or "").splitlines():
        parts = [x.strip() for x in line.split(";")]
        if len(parts) < 2 or not parts[0]:
            continue
        parts += [""] * (5 - len(parts))
        flag = parts[4].upper() if parts[4].upper() in ("H", "L", "N") else "N"
        out.append({"analyte": parts[0], "value": parts[1], "unit": parts[2],
                    "ref_range": parts[3], "flag": flag})
    return out


def create_document(patient_id, category, title, issued_utc, author, department, body,
                    status, released, lab_rows, created_by) -> int:
    with session_scope() as db:
        d = ClinicalDocument(patient_id=patient_id, category=category, title=title,
                             issued_at=issued_utc, author=author, department=department, body=body,
                             status=status, released_to_patient=bool(released),
                             released_at=utcnow() if released else None, created_by=created_by)
        for r in lab_rows:
            d.results.append(LabResult(**r))
        db.add(d); db.flush()
        return d.id


def set_document_release(doc_id: int, released: bool):
    with session_scope() as db:
        d = db.get(ClinicalDocument, doc_id)
        if d:
            d.released_to_patient = released
            d.released_at = utcnow() if released else None


def patient_options() -> list:
    with read_scope() as db:
        accs = {a.patient_id: a for a in db.query(PatientAccount).all()}
        out = []
        for p in db.query(Patient).order_by(Patient.code).all():
            a = accs.get(p.id)
            tag = " · portale ✓" if (a and a.email_verified) else (" · portale (da verificare)" if a else "")
            out.append({"label": f"{p.code}{tag}", "value": p.id})
        return out


def email_log(limit: int = 100) -> list:
    with read_scope() as db:
        return [{"created_at": e.created_at, "to": e.to_addr, "subject": e.subject,
                 "kind": e.kind, "related_id": e.related_id, "status": e.status, "error": e.error or ""}
                for e in db.query(EmailLog).order_by(EmailLog.id.desc()).limit(limit).all()]


def audit_log(limit: int = 100) -> list:
    with read_scope() as db:
        return [{"ts": a.ts, "actor": f"{a.actor_type}:{a.actor_id or '-'}", "action": a.action,
                 "resource": f"{a.resource or ''} {a.resource_id or ''}".strip(), "ip": a.ip or "",
                 "detail": a.detail or ""}
                for a in db.query(AuditLog).order_by(AuditLog.id.desc()).limit(limit).all()]
