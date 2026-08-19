from flask import request

from adaptater.agent_config.agent_config_adaptater import AgentConfigAdaptater
from adaptater.audit.audit_log_adaptater import AuditLogAdaptater
from commons.helpers.custom_response import CustomResponse
from commons.instances.instances import logger
from data.entities.scheduled_task.scheduled_task import ScheduledTask
from services.scheduler.scheduler_service import SchedulerService


class AgentConfigController:

    @staticmethod
    def get_settings():
        """GET /api/admin/agent_config/settings — configuration actuelle de l'agent."""
        try:
            return CustomResponse.send_response(
                message="OK", success=True, status_code=200,
                data=AgentConfigAdaptater.get_all(),
            )
        except Exception as e:
            logger.error(f"Error in AgentConfigController.get_settings: {e}")
            return CustomResponse.send_serveur_error(error=e, success=False, status_code=500)

    @staticmethod
    def update_settings():
        """PUT /api/admin/agent_config/settings — met à jour la configuration (admin)."""
        try:
            from flask import g
            data = request.get_json() or {}
            settings = data.get("settings") or data
            updated = AgentConfigAdaptater.update_many(settings)
            AuditLogAdaptater.create(
                action="config_agent_modifiee",
                target_type="agent_settings",
                details={"settings": settings},
                user_id=getattr(g, "current_user", None).id if getattr(g, "current_user", None) else None,
                ip_address=request.remote_addr,
                success=True,
            )
            return CustomResponse.send_response(
                message=f"{updated} paramètre(s) mis à jour.", success=True, status_code=200,
                data=AgentConfigAdaptater.get_all(),
            )
        except Exception as e:
            logger.error(f"Error in AgentConfigController.update_settings: {e}")
            return CustomResponse.send_serveur_error(error=e, success=False, status_code=500)

    @staticmethod
    def list_audit():
        """GET /api/admin/agent_config/audit — journal d'audit des actions (qui, quoi, quand, résultat — §5.5)."""
        try:
            from flask import request as flask_request
            limit = flask_request.args.get("limit", 100)
            action = flask_request.args.get("action")
            logs = AuditLogAdaptater.list(limit=limit, action=action)
            return CustomResponse.send_response(message="OK", success=True, status_code=200, data=logs)
        except Exception as e:
            logger.error(f"Error in AgentConfigController.list_audit: {e}")
            return CustomResponse.send_serveur_error(error=e, success=False, status_code=500)

    @staticmethod
    def list_tasks():
        """GET /api/admin/agent_config/tasks — tâches planifiées (§4.6)."""
        try:
            tasks = [t.to_dict() for t in ScheduledTask.query.order_by(ScheduledTask.task_type.asc()).all()]
            return CustomResponse.send_response(message="OK", success=True, status_code=200, data=tasks)
        except Exception as e:
            logger.error(f"Error in AgentConfigController.list_tasks: {e}")
            return CustomResponse.send_serveur_error(error=e, success=False, status_code=500)

    @staticmethod
    def run_task(task_id):
        """POST /api/admin/agent_config/tasks/<id>/run — exécute une tâche immédiatement (admin)."""
        try:
            task = ScheduledTask.query.filter_by(id=task_id).first()
            if not task:
                return CustomResponse.send_response(
                    message="Tâche introuvable.", success=False, status_code=404
                )
            result = SchedulerService.run_task_now(task_id)
            return CustomResponse.send_response(
                message="Tâche exécutée.", success=result.get("success", False),
                status_code=200 if result.get("success") else 500,
                data=result,
            )
        except Exception as e:
            logger.error(f"Error in AgentConfigController.run_task: {e}")
            return CustomResponse.send_serveur_error(error=e, success=False, status_code=500)
