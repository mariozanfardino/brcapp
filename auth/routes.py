"""Route Flask: OAuth 2.0/OIDC, logout, verifica email, .ics, task cron, health."""
import hmac, logging
from flask import Blueprint, redirect, request, session, abort, Response, jsonify, url_for
from authlib.integrations.flask_client import OAuth
import config
from database.db import session_scope, read_scope
from database.models import User, PatientAccount, Appointment
from database.auth_db import get_permissions
from auth.session import login_staff, login_patient, logout as do_logout
from services.audit import audit
from services.security import read_token
from services.timeutil import utcnow

log = logging.getLogger("auth")
bp = Blueprint("brcapp_auth", __name__)
oauth = OAuth()

def init_oauth(server):
    oauth.init_app(server)
    for name, p in config.enabled_providers().items():
        oauth.register(
            name=name,
            client_id=p["client_id"],
            client_secret=p["client_secret"],
            server_metadata_url=p["server_metadata_url"],
            # Authorization Code Flow + PKCE (S256); state e nonce gestiti da Authlib
            client_kwargs={"scope": "openid email profile", "code_challenge_method": "S256"},
        )
        log.info(f"OAuth provider attivo: {name}")
    server.register_blueprint(bp)

def _staff_payload(u: User) -> dict:
    role = u.group.role if u.group else "viewer"
    return {"id": u.id, "username": u.username, "display_name": u.display_name or u.username,
            "role": role, "permissions": get_permissions(role)}

# ── OAuth ─────────────────────────────────────────────────────────────────────
@bp.route("/auth/oauth/<provider>/<audience>")
def oauth_start(provider, audience):
    if provider not in config.enabled_providers() or audience not in ("staff", "patient"):
        abort(404)
    session["oauth_audience"] = audience
    redirect_uri = f"{config.BASE_URL}/auth/callback/{provider}"
    return oauth.create_client(provider).authorize_redirect(redirect_uri)

@bp.route("/auth/callback/<provider>")
def oauth_callback(provider):
    if provider not in config.enabled_providers():
        abort(404)
    audience = session.pop("oauth_audience", "staff")
    fail = "/login" if audience == "staff" else "/patient/login"
    try:
        token = oauth.create_client(provider).authorize_access_token()   # verifica state, PKCE, id_token, nonce
    except Exception as e:
        log.warning(f"OAuth {provider} fallito: {e}")
        audit("oauth_failed", "anon", detail=f"{provider}: {type(e).__name__}")
        return redirect(f"{fail}?error=oauth")
    info = token.get("userinfo") or {}
    sub = str(info.get("sub") or "")
    email = (info.get("email") or info.get("preferred_username") or "").strip().lower()
    # Google espone email_verified; Entra ID/IdP aziendali garantiscono l'email del tenant
    email_verified = bool(info.get("email_verified", provider != "google"))
    if not sub:
        return redirect(f"{fail}?error=oauth")

    if audience == "staff":
        # Nessun auto-provisioning: l'account staff deve esistere (creato dall'admin)
        with session_scope() as db:
            u = db.query(User).filter(User.oauth_provider == provider, User.oauth_subject == sub).first()
            if not u and email and email_verified:
                u = db.query(User).filter(User.email.ilike(email)).first()
                if u and not u.oauth_subject:
                    u.oauth_provider, u.oauth_subject = provider, sub      # collegamento al primo accesso
            if not u or not u.is_active:
                audit("staff_oauth_denied", "anon", detail=f"{provider}:{email}")
                return redirect("/login?error=oauth_unknown")
            u.last_login = utcnow()
            payload = _staff_payload(u)
        login_staff(payload, method=f"oauth:{provider}")
        audit("staff_login", "staff", payload["id"], detail=f"oauth:{provider}")
        return redirect("/")

    # Paziente
    with session_scope() as db:
        acc = db.query(PatientAccount).filter(PatientAccount.oauth_provider == provider,
                                              PatientAccount.oauth_subject == sub).first()
        if not acc and email and email_verified:
            acc = db.query(PatientAccount).filter(PatientAccount.email == email).first()
            if acc and not acc.oauth_subject:
                acc.oauth_provider, acc.oauth_subject = provider, sub
        if acc:
            if not acc.is_active:
                return redirect("/patient/login?error=disabled")
            if not acc.email_verified and email_verified and acc.email == email:
                acc.email_verified, acc.verified_at = True, utcnow()
            if not acc.email_verified:
                return redirect("/patient/login?error=unverified")
            acc.last_login, acc.failed_logins, acc.locked_until = utcnow(), 0, None
            aid, pid = acc.id, acc.patient_id
        else:
            aid = None
    if aid:
        login_patient(aid, pid, method=f"oauth:{provider}")
        audit("patient_login", "patient", aid, detail=f"oauth:{provider}")
        return redirect("/patient/portal")
    # Primo accesso: serve collegare l'identità alla cartella con codice paziente + attivazione
    session["pending_oauth"] = {"provider": provider, "sub": sub, "email": email,
                                "email_verified": email_verified,
                                "given_name": info.get("given_name", ""),
                                "family_name": info.get("family_name", "")}
    return redirect("/patient/register?oauth=1")

# ── Logout ────────────────────────────────────────────────────────────────────
@bp.route("/auth/logout")
def logout():
    who = session.get("staff", {}).get("id") or session.get("patient_account_id")
    kind = do_logout()
    audit("logout", kind or "anon", who)
    return redirect("/patient/login?logout=1" if kind == "patient" else "/login?logout=1")

# ── Verifica email ────────────────────────────────────────────────────────────
@bp.route("/auth/verify/<token>")
def verify_email(token):
    data = read_token("verify", token)
    if not data:
        return redirect("/patient/login?error=token")
    with session_scope() as db:
        acc = db.get(PatientAccount, int(data["aid"]))
        if not acc:
            return redirect("/patient/login?error=token")
        if not acc.email_verified:
            acc.email_verified, acc.verified_at = True, utcnow()
    audit("email_verified", "patient", data["aid"])
    return redirect("/patient/login?verified=1")

# ── File calendario dell'appuntamento (solo proprietario) ────────────────────
@bp.route("/portal-files/appointment/<int:appt_id>.ics")
def appointment_ics(appt_id):
    from services.notifications import build_ics
    if session.get("kind") != "patient":
        abort(401)
    with read_scope() as db:
        appt = db.get(Appointment, appt_id)
        if not appt or appt.patient_id != session.get("patient_id"):
            abort(404)                           # 404 e non 403: non rivela l'esistenza
        data = build_ics(appt, "CANCEL" if appt.status == "cancelled" else "REQUEST")
    return Response(data, mimetype="text/calendar",
                    headers={"Content-Disposition": f"attachment; filename=appuntamento-{appt_id}.ics"})

# ── Task promemoria per cron esterno ──────────────────────────────────────────
@bp.route("/tasks/reminders", methods=["POST"])
def task_reminders():
    from services.notifications import send_due_reminders
    tok = request.headers.get("X-Cron-Token", "")
    if not config.CRON_TOKEN or not hmac.compare_digest(tok, config.CRON_TOKEN):
        abort(403)
    return jsonify(send_due_reminders())

@bp.route("/healthz")
def healthz():
    return jsonify(status="ok", version=config.APP_VERSION)

# ── Header di sicurezza su tutte le risposte ─────────────────────────────────
@bp.after_app_request
def security_headers(resp):
    resp.headers.setdefault("X-Content-Type-Options", "nosniff")
    resp.headers.setdefault("X-Frame-Options", "DENY")
    resp.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    if config.COOKIE_SECURE:
        resp.headers.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
    if request.path.startswith(("/patient", "/portal-files", "/_dash-update-component")):
        resp.headers["Cache-Control"] = "no-store"          # dati sanitari: niente cache
    return resp
