"""Ordonnanceur des tâches planifiées (cahier des charges §3.3, §4.6).

Les tâches sont enregistrées en base (table scheduled_tasks) avec une expression
cron ; l'ordonnanceur APScheduler les exécute dans le contexte applicatif Flask.
Chaque exécution met à jour le journal d'exécution de la tâche (succès/échec).
"""
import traceback

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from commons.config.config import Config
from commons.instances.instances import logger
from data.entities.config.entities_config import db
from data.entities.scheduled_task.scheduled_task import ScheduledTask
from data.entities.agent_settings.agent_settings import AgentSettings

# Tâches par défaut (créées au premier démarrage si aucune n'existe)
DEFAULT_TASKS = [
    {
        "task_type": "unpaid_reminder",
        "cron_expression": "0 8 * * *",  # chaque jour à 08h00
        "config": {},
        "description": "Relance automatique des factures impayées (J+7, J+15, J+30)",
    },
    {
        "task_type": "stock_alert",
        "cron_expression": "0 7 * * *",  # chaque jour à 07h00
        "config": {},
        "description": "Alerte lorsque le stock d'un produit passe sous le seuil configuré",
    },
    {
        "task_type": "periodic_report",
        "cron_expression": "0 7 * * 1",  # chaque lundi à 07h00
        "config": {},
        "description": "Rapport hebdomadaire d'activité envoyé par courriel",
    },
    {
        "task_type": "incoming_email",
        "cron_expression": "*/10 * * * *",  # toutes les 10 minutes
        "config": {},
        "description": "Traitement de la boîte e-mail entrante de l'agent",
    },
    {
        "task_type": "vector_sync",
        "cron_expression": "0 */6 * * *",  # toutes les 6 heures
        "config": {},
        "description": "Synchronisation de l'index vectoriel Dolibarr (clients, produits)",
    },
]

_USE_CASES = {
    "unpaid_reminder": "uses_cases.unpaid_invoice_reminder_use_case",
    "stock_alert": "uses_cases.stock_alert_use_case",
    "periodic_report": "uses_cases.periodic_report_use_case",
    "incoming_email": "uses_cases.incoming_email_use_case",
    "vector_sync": "uses_cases.vector_sync_use_case",
}


class SchedulerService:

    _scheduler = None

    # ------------------------------------------------------------------ helpers
    @staticmethod
    def _ensure_default_tasks():
        """Crée les tâches par défaut si la table est vide, puis les tâches manquantes."""
        try:
            if ScheduledTask.query.count() == 0:
                for task in DEFAULT_TASKS:
                    db.session.add(ScheduledTask(
                        task_type=task["task_type"],
                        cron_expression=task["cron_expression"],
                        config=task.get("config", {}),
                        is_active=True,
                    ))
                db.session.commit()
                logger.info("Tâches planifiées par défaut créées.")
            else:
                existing = {t.task_type for t in ScheduledTask.query.all()}
                added = 0
                for task in DEFAULT_TASKS:
                    if task["task_type"] not in existing:
                        db.session.add(ScheduledTask(
                            task_type=task["task_type"],
                            cron_expression=task["cron_expression"],
                            config=task.get("config", {}),
                            is_active=True,
                        ))
                        added += 1
                if added:
                    db.session.commit()
                    logger.info(f"{added} tâche(s) planifiée(s) manquante(s) ajoutée(s).")
        except Exception as e:
            logger.error(f"SchedulerService._ensure_default_tasks failed: {e}")
            db.session.rollback()

    @staticmethod
    def _import_use_case(task_type: str):
        import importlib
        module = importlib.import_module(_USE_CASES[task_type])
        return getattr(module, "UseCase")  # chaque use case expose UseCase.execute()

    # ------------------------------------------------------------------ API
    @staticmethod
    def start(app):
        """Démarre l'ordonnanceur (au démarrage de l'application, après le seeding)."""
        try:
            SchedulerService.stop()
            with app.app_context():
                SchedulerService._ensure_default_tasks()

            scheduler = BackgroundScheduler(daemon=True)
            with app.app_context():
                tasks = ScheduledTask.query.filter_by(is_active=True).all()
                for task in tasks:
                    SchedulerService._schedule(scheduler, app, task)
            scheduler.start()
            SchedulerService._scheduler = scheduler
            logger.info("Ordonnanceur démarré.")
        except Exception as e:
            logger.error(f"SchedulerService.start failed: {e}")
            logger.error(traceback.format_exc())

    @staticmethod
    def _schedule(scheduler, app, task: ScheduledTask):
        try:
            if task.task_type not in _USE_CASES:
                logger.warning(f"Type de tâche inconnu: {task.task_type}")
                return

            def job_wrapper():
                with app.app_context():
                    SchedulerService._run_task(task.id)

            trigger = CronTrigger.from_crontab(task.cron_expression)
            scheduler.add_job(
                job_wrapper,
                trigger=trigger,
                id=f"task_{task.id}",
                replace_existing=True,
                max_instances=1,
                coalesce=True,
            )
            logger.info(f"Tâche planifiée: {task.task_type} ({task.cron_expression})")
        except Exception as e:
            logger.error(f"SchedulerService._schedule({task.task_type}) failed: {e}")

    @staticmethod
    def _run_task(task_id: int) -> dict:
        """Exécute une tâche et met à jour son journal d'exécution."""
        from datetime import datetime, timezone
        task = ScheduledTask.query.filter_by(id=task_id).first()
        if not task:
            return {"success": False, "summary": "Tâche introuvable"}
        try:
            use_case_class = SchedulerService._import_use_case(task.task_type)
            result = use_case_class.execute(task)
            summary = result.get("summary") if isinstance(result, dict) else str(result)
            task.last_run_at = datetime.now(timezone.utc)
            task.last_run_success = True
            task.last_run_summary = str(summary)
            db.session.commit()
            logger.info(f"Tâche {task.task_type} exécutée avec succès: {summary}")
            return {"success": True, "summary": summary}
        except Exception as e:
            task.last_run_at = datetime.now(timezone.utc)
            task.last_run_success = False
            task.last_run_summary = str(e)[:500]
            db.session.commit()
            logger.error(f"Tâche {task.task_type} en échec: {e}")
            logger.error(traceback.format_exc())
            return {"success": False, "summary": str(e)}

    @staticmethod
    def run_task_now(task_id: int) -> dict:
        """Exécution manuelle d'une tâche (route admin)."""
        return SchedulerService._run_task(task_id)

    @staticmethod
    def reload(app):
        """Recharge la planification (après modification d'une tâche)."""
        SchedulerService.start(app)

    @staticmethod
    def stop():
        if SchedulerService._scheduler:
            try:
                SchedulerService._scheduler.shutdown(wait=False)
            except Exception:
                pass
            SchedulerService._scheduler = None
