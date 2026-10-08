"""Invio email via SMTP (STARTTLS/SSL). Senza SMTP configurato i messaggi vanno
nella outbox su disco (.eml) — utile in sviluppo e per test senza inviare nulla."""
import os, smtplib, ssl, logging
from email.message import EmailMessage
from email.utils import make_msgid, formatdate
import config
from database.db import session_scope
from database.models import EmailLog

log = logging.getLogger("mailer")

def smtp_configured() -> bool:
    return bool(config.SMTP_HOST)

def send_email(to: str, subject: str, text: str, html: str, kind: str,
               related_id: int = None, attachments: list = None) -> str:
    """Ritorna lo stato: 'sent' | 'outbox' | 'failed'. Non solleva eccezioni."""
    msg = EmailMessage()
    msg["From"], msg["To"], msg["Subject"] = config.MAIL_FROM, to, subject
    msg["Date"] = formatdate(localtime=True)
    msg["Message-ID"] = make_msgid(domain="brcapp")
    msg["Auto-Submitted"] = "auto-generated"        # RFC 3834: niente auto-risposte
    if config.MAIL_REPLY_TO:
        msg["Reply-To"] = config.MAIL_REPLY_TO
    msg.set_content(text)
    msg.add_alternative(html, subtype="html")
    for fname, data, mime in (attachments or []):
        maintype, subtype = mime.split("/", 1)
        msg.add_attachment(data, maintype=maintype, subtype=subtype, filename=fname)

    status, error = "outbox", None
    if smtp_configured():
        try:
            if config.SMTP_USE_SSL:
                srv = smtplib.SMTP_SSL(config.SMTP_HOST, config.SMTP_PORT, timeout=20,
                                       context=ssl.create_default_context())
            else:
                srv = smtplib.SMTP(config.SMTP_HOST, config.SMTP_PORT, timeout=20)
                if config.SMTP_STARTTLS:
                    srv.starttls(context=ssl.create_default_context())
            with srv:
                if config.SMTP_USER:
                    srv.login(config.SMTP_USER, config.SMTP_PASSWORD or "")
                srv.send_message(msg)
            status = "sent"
        except Exception as e:
            status, error = "failed", f"{type(e).__name__}: {e}"
            log.error(f"Invio email fallito a {to}: {error}")
    else:
        try:
            os.makedirs(config.OUTBOX_DIR, exist_ok=True)
            fn = os.path.join(config.OUTBOX_DIR,
                              f"{kind}_{related_id or 'x'}_{msg['Message-ID'].strip('<>').split('@')[0]}.eml")
            with open(fn, "wb") as f:
                f.write(bytes(msg))
            log.info(f"[OUTBOX] {kind} → {to} | {subject} | {fn}")
        except Exception as e:
            status, error = "failed", str(e)

    with session_scope() as db:
        db.add(EmailLog(to_addr=to, subject=subject, kind=kind,
                        related_id=related_id, status=status, error=error))
    return status
