"""Job periodico per i promemoria (APScheduler, in-process).
Su hosting che sospende il processo (es. Render free) usare in aggiunta un cron
esterno su POST /tasks/reminders con header X-Cron-Token."""
import logging
from apscheduler.schedulers.background import BackgroundScheduler
import config

log = logging.getLogger("scheduler")
_scheduler = None

def start():
    global _scheduler
    if _scheduler or not config.SCHEDULER_ENABLED:
        return
    from services.notifications import send_due_reminders
    _scheduler = BackgroundScheduler(timezone=config.TIMEZONE, daemon=True)
    _scheduler.add_job(send_due_reminders, "interval", minutes=config.SCHEDULER_INTERVAL_MIN,
                       id="reminders", max_instances=1, coalesce=True)
    _scheduler.add_job(send_due_reminders, "date", id="reminders-boot")   # un giro all'avvio
    _scheduler.start()
    log.info(f"Scheduler promemoria attivo (ogni {config.SCHEDULER_INTERVAL_MIN} min)")
