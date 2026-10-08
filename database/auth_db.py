# database/auth_db.py — Repository per utenti e gruppi
import datetime
from typing import Optional, Dict, List
from werkzeug.security import generate_password_hash, check_password_hash
from database.db import session_scope, read_scope
from database.models import User, UserGroup

# ── Permessi per ruolo ────────────────────────────────────────────────────────
ROLE_PERMISSIONS = {
    "admin": {
        "pages":    ["/", "/patients", "/classification", "/statistics", "/admin/users", "/admin/pins", "/xai", "/search", "/agenda"],
        "can_classify":     True,
        "can_edit_patients":True,
        "can_manage_users": True,
        "label": "Amministratore",
        "color": "#DC2626",
    },
    "clinician": {
        "pages":    ["/", "/patients", "/classification", "/statistics", "/xai", "/search", "/agenda"],
        "can_classify":     True,
        "can_edit_patients":True,
        "can_manage_users": False,
        "label": "Clinico",
        "color": "#D63384",
    },
    "viewer": {
        "pages":    ["/", "/patients", "/statistics", "/xai", "/search"],
        "can_classify":     False,
        "can_edit_patients":False,
        "can_manage_users": False,
        "label": "Osservatore",
        "color": "#6B7280",
    },
}

def get_permissions(role: str) -> Dict:
    return ROLE_PERMISSIONS.get(role, ROLE_PERMISSIONS["viewer"])


# ── User Repository ───────────────────────────────────────────────────────────
class UserRepository:

    @staticmethod
    def create(username: str, password: str, display_name: str = "",
               email: str = "", group_id: int = None) -> Dict:
        with session_scope() as db:
            u = User(
                username=username.strip().lower(),
                display_name=display_name or username,
                email=email,
                password_hash=generate_password_hash(password),
                group_id=group_id,
                is_active=True,
            )
            db.add(u); db.flush()
            uid = u.id
        return UserRepository.get_by_id(uid)

    @staticmethod
    def authenticate(username: str, password: str) -> Optional[Dict]:
        with session_scope() as db:
            u = db.query(User).filter(
                User.username == username.strip().lower(),
                User.is_active == True
            ).first()
            if not u or not check_password_hash(u.password_hash, password):
                return None
            u.last_login = datetime.datetime.utcnow()
            role = u.group.role if u.group else "viewer"
            return {
                "id": u.id, "username": u.username,
                "display_name": u.display_name or u.username,
                "role": role,
                "group": u.group.name if u.group else "—",
                "permissions": get_permissions(role),
            }

    @staticmethod
    def get_by_id(uid: int) -> Optional[Dict]:
        with read_scope() as db:
            u = db.query(User).filter(User.id == uid).first()
            return u.to_dict() if u else None

    @staticmethod
    def get_all() -> List[Dict]:
        with read_scope() as db:
            return [u.to_dict() for u in
                    db.query(User).order_by(User.username).all()]

    @staticmethod
    def update(uid: int, data: Dict):
        with session_scope() as db:
            u = db.query(User).filter(User.id == uid).first()
            if not u: return
            for f in ["display_name","email","group_id","is_active"]:
                if f in data: setattr(u, f, data[f])
            if data.get("password"):
                u.password_hash = generate_password_hash(data["password"])

    @staticmethod
    def delete(uid: int):
        with session_scope() as db:
            u = db.query(User).filter(User.id == uid).first()
            if u: db.delete(u)


# ── Group Repository ──────────────────────────────────────────────────────────
class GroupRepository:

    @staticmethod
    def create(name: str, role: str, description: str = "") -> Dict:
        with session_scope() as db:
            g = UserGroup(name=name.strip(), role=role, description=description)
            db.add(g); db.flush(); gid = g.id
        return GroupRepository.get_by_id(gid)

    @staticmethod
    def get_by_id(gid: int) -> Optional[Dict]:
        with read_scope() as db:
            g = db.query(UserGroup).filter(UserGroup.id == gid).first()
            return g.to_dict() if g else None

    @staticmethod
    def get_all() -> List[Dict]:
        with read_scope() as db:
            return [g.to_dict() for g in
                    db.query(UserGroup).order_by(UserGroup.name).all()]

    @staticmethod
    def update(gid: int, data: Dict):
        with session_scope() as db:
            g = db.query(UserGroup).filter(UserGroup.id == gid).first()
            if not g: return
            for f in ["name","role","description"]:
                if f in data: setattr(g, f, data[f])

    @staticmethod
    def delete(gid: int):
        with session_scope() as db:
            g = db.query(UserGroup).filter(UserGroup.id == gid).first()
            if g: db.delete(g)


# ── Seed default users ────────────────────────────────────────────────────────
def seed_default_users():
    """Crea admin/clinician/viewer di default se il DB è vuoto."""
    with read_scope() as db:
        if db.query(User).count() > 0:
            return

    # Gruppi
    admin_g    = GroupRepository.create("Amministratori", "admin",    "Accesso completo")
    clinician_g= GroupRepository.create("Clinici",        "clinician","Accesso clinico")
    viewer_g   = GroupRepository.create("Osservatori",    "viewer",   "Sola lettura")

    # Utenti default
    UserRepository.create("admin",    "admin123",    "Amministratore", group_id=admin_g["id"])
    UserRepository.create("dott_rossi","clinico123", "Dott. Rossi",    group_id=clinician_g["id"])
    UserRepository.create("viewer",   "viewer123",   "Osservatore",    group_id=viewer_g["id"])

    print("  ✓ Utenti default creati: admin/admin123 · dott_rossi/clinico123 · viewer/viewer123")


# ── Patient Auth ──────────────────────────────────────────────────────────────
import random, string as _string
from database.models import Patient, ClinicalRecord, ClassificationResult

def generate_pin(length=6) -> str:
    """Codice di attivazione portale: CSPRNG, monouso (consumato alla registrazione)."""
    import secrets
    return "".join(secrets.choice(_string.digits) for _ in range(length))

class PatientAuthRepository:

    @staticmethod
    def set_pin(patient_id: int, pin: str):
        from werkzeug.security import generate_password_hash
        with session_scope() as db:
            p = db.query(Patient).filter(Patient.id == patient_id).first()
            if p:
                p.patient_pin = generate_password_hash(pin)

    @staticmethod
    def get_all_with_pin_status() -> list:
        with read_scope() as db:
            rows = db.query(Patient).order_by(Patient.code).all()
            return [{"id":p.id,"code":p.code,"initials":getattr(p,"initials","") or "",
                     "has_pin": bool(p.patient_pin),
                     "email": p.patient_email or ""} for p in rows]
