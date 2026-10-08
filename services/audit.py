"""Audit trail (accessi e operazioni su dati sanitari)."""
import logging
from flask import has_request_context, request
from database.db import session_scope
from database.models import AuditLog

log = logging.getLogger("audit")

def audit(action: str, actor_type: str = "system", actor_id=None,
          resource: str = None, resource_id=None, detail: str = None):
    ip = None
    if has_request_context():
        ip = (request.headers.get("X-Forwarded-For", request.remote_addr) or "").split(",")[0].strip()
    try:
        with session_scope() as db:
            db.add(AuditLog(actor_type=actor_type, actor_id=str(actor_id) if actor_id else None,
                            action=action, resource=resource,
                            resource_id=str(resource_id) if resource_id else None,
                            ip=ip, detail=detail))
    except Exception as e:      # l'audit non deve mai bloccare il flusso utente
        log.error(f"Audit non registrato ({action}): {e}")
