"""Password, token firmati e protezione brute-force."""
import re
from datetime import timedelta
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
from werkzeug.security import generate_password_hash, check_password_hash
from config import SECRET_KEY, VERIFY_TOKEN_HOURS, RESET_TOKEN_MINUTES, MAX_FAILED_LOGINS, LOCKOUT_MINUTES
from services.timeutil import utcnow

_COMMON = {"password", "password1", "12345678", "123456789", "qwertyuiop",
           "iloveyou", "admin123", "benvenuto", "napoli1926", "1234567890"}

def validate_password(pw: str, email: str = "") -> str | None:
    """Policy allineata a NIST SP 800-63B: lunghezza, blocklist, niente dati personali.
    Ritorna un messaggio d'errore o None se valida."""
    if not pw or len(pw) < 10:
        return "La password deve contenere almeno 10 caratteri."
    if len(pw) > 128:
        return "La password è troppo lunga (max 128 caratteri)."
    if pw.lower() in _COMMON:
        return "Password troppo comune: scegline un'altra."
    local = (email or "").split("@")[0].lower()
    if local and len(local) >= 4 and local in pw.lower():
        return "La password non deve contenere il tuo indirizzo email."
    if not (re.search(r"[A-Za-z]", pw) and re.search(r"\d", pw)):
        return "La password deve contenere almeno una lettera e un numero."
    return None

def hash_password(pw: str) -> str:
    return generate_password_hash(pw)          # scrypt (default Werkzeug ≥ 3)

def verify_password(pw_hash: str | None, pw: str) -> bool:
    return bool(pw_hash) and check_password_hash(pw_hash, pw or "")

# ── Token firmati e con scadenza (verifica email / reset password) ────────────
def _ser(salt: str):
    return URLSafeTimedSerializer(SECRET_KEY, salt=salt)

def make_token(purpose: str, account_id: int, extra: str = "") -> str:
    return _ser(purpose).dumps({"aid": account_id, "x": extra})

def read_token(purpose: str, token: str) -> dict | None:
    max_age = VERIFY_TOKEN_HOURS * 3600 if purpose == "verify" else RESET_TOKEN_MINUTES * 60
    try:
        return _ser(purpose).loads(token, max_age=max_age)
    except (BadSignature, SignatureExpired):
        return None

# ── Lockout progressivo account ───────────────────────────────────────────────
def is_locked(account) -> bool:
    return bool(account.locked_until and account.locked_until > utcnow())

def register_failure(account):
    account.failed_logins = (account.failed_logins or 0) + 1
    if account.failed_logins >= MAX_FAILED_LOGINS:
        account.locked_until = utcnow() + timedelta(minutes=LOCKOUT_MINUTES)
        account.failed_logins = 0

def register_success(account):
    account.failed_logins = 0
    account.locked_until = None
    account.last_login = utcnow()

# Throttle in memoria per login staff (per username)
_staff_fail: dict[str, list] = {}
def staff_throttled(username: str) -> bool:
    rec = _staff_fail.get(username.lower())
    return bool(rec and rec[0] >= MAX_FAILED_LOGINS and rec[1] > utcnow())

def staff_failure(username: str):
    k = username.lower()
    n, until = _staff_fail.get(k, [0, utcnow()])
    n += 1
    _staff_fail[k] = [n, utcnow() + timedelta(minutes=LOCKOUT_MINUTES)] if n >= MAX_FAILED_LOGINS else [n, until]

def staff_success(username: str):
    _staff_fail.pop(username.lower(), None)
