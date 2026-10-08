"""Configurazione BrCapp — tutti i segreti arrivano da variabili d'ambiente (12-factor)."""
import os, secrets, logging

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def _env(name, default=None):
    v = os.environ.get(name)
    return v if v not in (None, "") else default

def _bool(name, default=False):
    return str(_env(name, str(default))).lower() in ("1", "true", "yes", "on")

# ── App ───────────────────────────────────────────────────────────────────────
APP_NAME    = "BrCapp"
APP_VERSION = "2.0.0"
BASE_URL    = _env("BRCAPP_BASE_URL", "http://127.0.0.1:8050").rstrip("/")
TIMEZONE    = _env("BRCAPP_TIMEZONE", "Europe/Rome")
DB_PATH     = _env("BRCAPP_DB_PATH",
                   os.path.join(os.path.expanduser("~"), ".local", "share", "brcapp", "breastcare.db"))

# Chiave di firma sessioni/token. In produzione DEVE essere impostata:
# se manca ne viene generata una effimera (le sessioni decadono ad ogni riavvio).
SECRET_KEY = _env("BRCAPP_SECRET_KEY")
if not SECRET_KEY:
    SECRET_KEY = secrets.token_urlsafe(48)
    logging.getLogger(__name__).warning(
        "BRCAPP_SECRET_KEY non impostata: uso una chiave effimera (solo sviluppo).")

SESSION_HOURS        = int(_env("BRCAPP_SESSION_HOURS", "8"))
COOKIE_SECURE        = BASE_URL.startswith("https://")
MAX_FAILED_LOGINS    = 5
LOCKOUT_MINUTES      = 15
VERIFY_TOKEN_HOURS   = 48
RESET_TOKEN_MINUTES  = 60

# ── OAuth 2.0 / OpenID Connect ────────────────────────────────────────────────
# Un provider è attivo solo se client_id e client_secret sono configurati.
OAUTH_PROVIDERS = {
    "google": {
        "label": "Google",
        "client_id": _env("GOOGLE_CLIENT_ID"),
        "client_secret": _env("GOOGLE_CLIENT_SECRET"),
        "server_metadata_url": "https://accounts.google.com/.well-known/openid-configuration",
    },
    "microsoft": {
        "label": "Microsoft",
        "client_id": _env("MICROSOFT_CLIENT_ID"),
        "client_secret": _env("MICROSOFT_CLIENT_SECRET"),
        "server_metadata_url": "https://login.microsoftonline.com/"
                               f"{_env('MICROSOFT_TENANT_ID', 'common')}/v2.0/.well-known/openid-configuration",
    },
    # Provider OIDC generico: Keycloak aziendale, gateway SPID/CIE, ecc.
    "oidc": {
        "label": _env("OIDC_LABEL", "SSO Aziendale"),
        "client_id": _env("OIDC_CLIENT_ID"),
        "client_secret": _env("OIDC_CLIENT_SECRET"),
        "server_metadata_url": (_env("OIDC_ISSUER", "").rstrip("/") + "/.well-known/openid-configuration")
                               if _env("OIDC_ISSUER") else None,
    },
}

def enabled_providers():
    return {k: v for k, v in OAUTH_PROVIDERS.items()
            if v["client_id"] and v["client_secret"] and v["server_metadata_url"]}

# ── Email (SMTP) ──────────────────────────────────────────────────────────────
# Senza SMTP_HOST le email non partono: vengono salvate nella outbox (log + DB)
SMTP_HOST     = _env("SMTP_HOST")
SMTP_PORT     = int(_env("SMTP_PORT", "587"))
SMTP_USER     = _env("SMTP_USER")
SMTP_PASSWORD = _env("SMTP_PASSWORD")
SMTP_USE_SSL  = _bool("SMTP_USE_SSL", False)   # True = SMTPS implicito (porta 465)
SMTP_STARTTLS = _bool("SMTP_STARTTLS", True)   # STARTTLS su 587 (False solo per server di test)
MAIL_FROM     = _env("MAIL_FROM", "BrCapp <no-reply@brcapp.local>")
MAIL_REPLY_TO = _env("MAIL_REPLY_TO")
OUTBOX_DIR    = _env("BRCAPP_OUTBOX_DIR", os.path.join(os.path.dirname(DB_PATH), "outbox"))

# ── Promemoria ────────────────────────────────────────────────────────────────
REMINDER_FROM_HOUR      = int(_env("REMINDER_FROM_HOUR", "8"))   # ora locale minima d'invio
SCHEDULER_ENABLED       = _bool("BRCAPP_SCHEDULER", True)
SCHEDULER_INTERVAL_MIN  = int(_env("BRCAPP_SCHEDULER_MINUTES", "30"))
CRON_TOKEN              = _env("BRCAPP_CRON_TOKEN")              # per /tasks/reminders

# ── Struttura (mostrata in email/portale) ─────────────────────────────────────
FACILITY_NAME    = _env("FACILITY_NAME", "Breast Unit — BrCapp")
FACILITY_ADDRESS = _env("FACILITY_ADDRESS", "Via G. Ferraris 144, 80143 Napoli")
FACILITY_PHONE   = _env("FACILITY_PHONE", "+39 081 000 0000")

# ── Modello ───────────────────────────────────────────────────────────────────
WEKA_MODEL_DIR = os.path.join(BASE_DIR, "models_weka")
JAVA_HEAP      = "512m"
LOGO_PATH      = os.path.join(BASE_DIR, "assets", "logo.png")

# ── Palette ───────────────────────────────────────────────────────────────────
PINK, PURPLE, PINK_L, PURP_L = "#D63384", "#4A235A", "#F8D7E8", "#EDE7F6"
