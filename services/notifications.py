"""Comunicazioni al paziente: verifica email, reset password, appuntamenti.

Minimizzazione (GDPR art. 5): le email NON contengono dati clinici
(né tipo di prestazione né referti) — solo data, ora e sede; i dettagli
sono consultabili nel portale dopo l'autenticazione."""
import logging
from datetime import timedelta, datetime, time
import config
from database.db import session_scope, read_scope
from database.models import Appointment, PatientAccount
from services.mailer import send_email
from services.security import make_token
from services.timeutil import fmt_long, utcnow, local_now, local_to_utc
from services.audit import audit

log = logging.getLogger("notifications")

# ── Template ──────────────────────────────────────────────────────────────────
def _html(title: str, greeting: str, body_html: str, cta: tuple | None = None) -> str:
    btn = ""
    if cta:
        btn = (f'<p style="margin:28px 0"><a href="{cta[1]}" style="background:{config.PINK};'
               f'color:#fff;padding:12px 22px;border-radius:8px;text-decoration:none;'
               f'font-weight:600;display:inline-block">{cta[0]}</a></p>')
    return f"""<!doctype html><html lang="it"><body style="margin:0;background:#F4F6F9;
font-family:Arial,Helvetica,sans-serif;color:#1A1A2E">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0"><tr><td align="center" style="padding:24px">
<table role="presentation" width="560" cellpadding="0" cellspacing="0" style="background:#fff;border-radius:12px;overflow:hidden">
<tr><td style="background:linear-gradient(135deg,{config.PINK},{config.PURPLE});background-color:{config.PURPLE};
padding:22px 28px;color:#fff;font-size:18px;font-weight:700">{config.FACILITY_NAME}</td></tr>
<tr><td style="padding:28px">
<h2 style="margin:0 0 14px;font-size:20px">{title}</h2>
<p style="margin:0 0 14px">{greeting}</p>{body_html}{btn}
<p style="font-size:12px;color:#6B7280;margin-top:28px;border-top:1px solid #eee;padding-top:14px">
Messaggio automatico, non rispondere. Per informazioni: {config.FACILITY_PHONE}.<br>
{config.FACILITY_NAME} — {config.FACILITY_ADDRESS}</p>
</td></tr></table></td></tr></table></body></html>"""

def _greeting(patient) -> str:
    name = (patient.first_name or "").strip()
    return f"Gentile {name}," if name else "Gentile paziente,"

def _appt_box(appt) -> str:
    return (f'<table cellpadding="0" cellspacing="0" style="background:#F8F9FA;border-radius:8px;'
            f'padding:14px 18px;margin:8px 0;width:100%"><tr><td style="padding:14px 18px">'
            f'<b>Data e ora:</b> {fmt_long(appt.start_at)}<br>'
            f'<b>Sede:</b> {appt.location or config.FACILITY_ADDRESS}</td></tr></table>')

# ── Calendario (RFC 5545) ─────────────────────────────────────────────────────
def build_ics(appt, method: str = "REQUEST") -> bytes:
    def z(dt): return dt.strftime("%Y%m%dT%H%M%SZ")
    end = appt.start_at + timedelta(minutes=appt.duration_min or 30)
    status = "CANCELLED" if method == "CANCEL" else "CONFIRMED"
    lines = [
        "BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//BrCapp//Portale Paziente//IT",
        f"METHOD:{method}", "CALSCALE:GREGORIAN", "BEGIN:VEVENT",
        f"UID:appt-{appt.id}@brcapp", f"DTSTAMP:{z(utcnow())}",
        f"DTSTART:{z(appt.start_at)}", f"DTEND:{z(end)}",
        f"SUMMARY:Appuntamento - {config.FACILITY_NAME}",
        f"LOCATION:{(appt.location or config.FACILITY_ADDRESS).replace(',', chr(92)+',')}",
        f"STATUS:{status}", f"SEQUENCE:{1 if method == 'CANCEL' else 0}",
        "BEGIN:VALARM", "TRIGGER:-PT2H", "ACTION:DISPLAY",
        "DESCRIPTION:Promemoria appuntamento", "END:VALARM",
        "END:VEVENT", "END:VCALENDAR",
    ]
    return ("\r\n".join(lines) + "\r\n").encode("utf-8")

# ── Destinatario idoneo ───────────────────────────────────────────────────────
def _recipient(db, patient_id):
    """Account del paziente se può ricevere comunicazioni sugli appuntamenti."""
    acc = db.query(PatientAccount).filter(PatientAccount.patient_id == patient_id).first()
    if not acc:
        return None, "nessun account portale"
    if not (acc.is_active and acc.email_verified):
        return None, "email non verificata"
    if not acc.consent_email:
        return None, "consenso email non prestato"
    return acc, None

# ── Account ───────────────────────────────────────────────────────────────────
def send_verification(account_id: int) -> str:
    with read_scope() as db:
        acc = db.get(PatientAccount, account_id)
        to, greet = acc.email, _greeting(acc.patient)
    link = f"{config.BASE_URL}/auth/verify/{make_token('verify', account_id)}"
    text = (f"{greet}\n\nper attivare il tuo accesso al Portale Paziente conferma l'indirizzo email:\n"
            f"{link}\n\nIl link scade tra {config.VERIFY_TOKEN_HOURS} ore. "
            "Se non hai richiesto la registrazione ignora questo messaggio.")
    html = _html("Conferma il tuo indirizzo email", greet,
                 "<p>Per attivare l'accesso al <b>Portale Paziente</b> conferma il tuo indirizzo email.</p>"
                 f"<p style='font-size:13px;color:#6B7280'>Il link scade tra {config.VERIFY_TOKEN_HOURS} ore. "
                 "Se non hai richiesto la registrazione, ignora questo messaggio.</p>",
                 ("Conferma email", link))
    return send_email(to, "Conferma il tuo indirizzo email", text, html, "verify", account_id)

def send_password_reset(account_id: int) -> str:
    with read_scope() as db:
        acc = db.get(PatientAccount, account_id)
        to, greet, ph = acc.email, _greeting(acc.patient), (acc.password_hash or "")[-12:]
    # Il token incorpora l'impronta dell'hash attuale: diventa monouso dopo il cambio password
    link = f"{config.BASE_URL}/patient/reset?token={make_token('reset', account_id, ph)}"
    text = (f"{greet}\n\nabbiamo ricevuto una richiesta di reimpostazione della password.\n"
            f"{link}\n\nIl link scade tra {config.RESET_TOKEN_MINUTES} minuti. "
            "Se non sei stato tu, ignora questo messaggio: la password resterà invariata.")
    html = _html("Reimposta la password", greet,
                 "<p>Abbiamo ricevuto una richiesta di reimpostazione della password del Portale Paziente.</p>"
                 f"<p style='font-size:13px;color:#6B7280'>Il link scade tra {config.RESET_TOKEN_MINUTES} minuti. "
                 "Se non sei stato tu, ignora questo messaggio.</p>",
                 ("Reimposta password", link))
    return send_email(to, "Reimpostazione password", text, html, "reset", account_id)

# ── Appuntamenti ──────────────────────────────────────────────────────────────
def send_appointment_confirmation(appt_id: int) -> str:
    """Email di conferma alla presa dell'appuntamento. Ritorna esito leggibile."""
    with session_scope() as db:
        appt = db.get(Appointment, appt_id)
        acc, why = _recipient(db, appt.patient_id)
        if not acc:
            return f"non inviata ({why})"
        greet = _greeting(appt.patient)
        text = (f"{greet}\n\nti confermiamo il seguente appuntamento:\n"
                f"Data e ora: {fmt_long(appt.start_at)}\nSede: {appt.location or config.FACILITY_ADDRESS}\n\n"
                f"I dettagli e le eventuali istruzioni sono disponibili nel Portale Paziente: {config.BASE_URL}/patient/login\n"
                f"Se non puoi presentarti avvisaci al {config.FACILITY_PHONE}.")
        html = _html("Appuntamento confermato", greet,
                     "<p>Ti confermiamo il seguente appuntamento:</p>" + _appt_box(appt) +
                     "<p>Dettagli e istruzioni sono disponibili nel Portale Paziente. "
                     "In allegato trovi l'evento da aggiungere al tuo calendario.</p>"
                     f"<p>Se non puoi presentarti, avvisaci al <b>{config.FACILITY_PHONE}</b>.</p>",
                     ("Apri il Portale Paziente", f"{config.BASE_URL}/patient/login"))
        status = send_email(acc.email, "Conferma appuntamento", text, html, "appt_confirm", appt.id,
                            [("appuntamento.ics", build_ics(appt), "text/calendar")])
        if status in ("sent", "outbox"):
            appt.confirmation_sent_at = utcnow()
    audit("appt_confirmation_email", "system", resource="appointment", resource_id=appt_id, detail=status)
    return status

def send_appointment_cancellation(appt_id: int) -> str:
    with session_scope() as db:
        appt = db.get(Appointment, appt_id)
        acc, why = _recipient(db, appt.patient_id)
        if not acc:
            return f"non inviata ({why})"
        greet = _greeting(appt.patient)
        text = (f"{greet}\n\nl'appuntamento del {fmt_long(appt.start_at)} è stato annullato.\n"
                f"Per riprogrammarlo contattaci al {config.FACILITY_PHONE}.")
        html = _html("Appuntamento annullato", greet,
                     "<p>Il seguente appuntamento è stato <b>annullato</b>:</p>" + _appt_box(appt) +
                     f"<p>Per riprogrammarlo contattaci al <b>{config.FACILITY_PHONE}</b>.</p>")
        return send_email(acc.email, "Appuntamento annullato", text, html, "appt_cancel", appt.id,
                          [("annullamento.ics", build_ics(appt, "CANCEL"), "text/calendar")])

def send_due_reminders(force: bool = False) -> dict:
    """Promemoria per gli appuntamenti di DOMANI (data locale). Idempotente:
    ogni appuntamento riceve al massimo un promemoria (reminder_sent_at)."""
    now_l = local_now()
    if not force and now_l.hour < config.REMINDER_FROM_HOUR:
        return {"skipped": "fuori fascia oraria", "sent": 0}
    tomorrow = (now_l + timedelta(days=1)).date()
    lo = local_to_utc(datetime.combine(tomorrow, time.min))
    hi = local_to_utc(datetime.combine(tomorrow + timedelta(days=1), time.min))

    with read_scope() as db:
        ids = [a.id for a in db.query(Appointment).filter(
            Appointment.status == "booked", Appointment.reminder_sent_at.is_(None),
            Appointment.start_at >= lo, Appointment.start_at < hi).all()]

    result = {"candidates": len(ids), "sent": 0, "outbox": 0, "failed": 0, "skipped": 0}
    for aid in ids:
        with session_scope() as db:
            appt = db.get(Appointment, aid)
            if appt.reminder_sent_at or appt.status != "booked":
                continue
            acc, why = _recipient(db, appt.patient_id)
            if not acc:
                result["skipped"] += 1
                continue
            greet = _greeting(appt.patient)
            text = (f"{greet}\n\nti ricordiamo l'appuntamento di domani:\n"
                    f"Data e ora: {fmt_long(appt.start_at)}\nSede: {appt.location or config.FACILITY_ADDRESS}\n\n"
                    f"Se non puoi presentarti avvisaci al {config.FACILITY_PHONE}.")
            html = _html("Promemoria: appuntamento domani", greet,
                         "<p>Ti ricordiamo l'appuntamento di <b>domani</b>:</p>" + _appt_box(appt) +
                         "<p>Ricorda di portare un documento d'identità, la tessera sanitaria "
                         "e gli eventuali referti precedenti.</p>"
                         f"<p>Se non puoi presentarti, avvisaci al <b>{config.FACILITY_PHONE}</b>.</p>",
                         ("Dettagli nel Portale", f"{config.BASE_URL}/patient/login"))
            status = send_email(acc.email, "Promemoria appuntamento di domani", text, html,
                                "appt_reminder", appt.id,
                                [("appuntamento.ics", build_ics(appt), "text/calendar")])
            result[status] = result.get(status, 0) + 1
            if status in ("sent", "outbox"):
                appt.reminder_sent_at = utcnow()
    if ids:
        audit("reminders_run", "system", detail=str(result))
    log.info(f"Promemoria: {result}")
    return result
