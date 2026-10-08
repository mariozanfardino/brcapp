"""Sessione lato server (cookie firmato Flask, HttpOnly) — fonte di verità
per l'autenticazione. Lo stato non è più affidato a dcc.Store nel browser."""
from datetime import timedelta
from flask import session
import config
from services.timeutil import utcnow

def _start(kind: str, payload: dict):
    session.clear()                      # rotazione: niente session fixation
    session.permanent = True
    session["kind"] = kind
    session["auth_at"] = utcnow().isoformat()
    session.update(payload)

def login_staff(user: dict, method: str = "password"):
    _start("staff", {"staff": user, "auth_method": method})

def login_patient(account_id: int, patient_id: int, method: str = "password"):
    _start("patient", {"patient_account_id": account_id,
                       "patient_id": patient_id, "auth_method": method})

def current_staff() -> dict | None:
    return session.get("staff") if session.get("kind") == "staff" else None

def current_patient() -> tuple[int, int] | None:
    if session.get("kind") != "patient":
        return None
    return session.get("patient_account_id"), session.get("patient_id")

def logout() -> str:
    kind = session.get("kind")
    session.clear()
    return kind

def configure(server):
    server.secret_key = config.SECRET_KEY
    server.config.update(
        SESSION_COOKIE_NAME="brcapp_session",
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",          # Lax: necessario per il redirect OAuth
        SESSION_COOKIE_SECURE=config.COOKIE_SECURE,
        PERMANENT_SESSION_LIFETIME=timedelta(hours=config.SESSION_HOURS),
    )
