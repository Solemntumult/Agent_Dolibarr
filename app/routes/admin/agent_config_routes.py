from flask import Blueprint
from flask_jwt_extended import jwt_required

from commons.utils.decorators import admin_required, internal_user_required
from controllers.admin.agent_config_controller import AgentConfigController

agent_config = Blueprint('agent_config', __name__)


@agent_config.route('/settings', methods=['GET'])
@jwt_required()
@internal_user_required()
@admin_required()
def get_settings_route():
    return AgentConfigController.get_settings()


@agent_config.route('/settings', methods=['PUT'])
@jwt_required()
@internal_user_required()
@admin_required()
def update_settings_route():
    return AgentConfigController.update_settings()


@agent_config.route('/audit', methods=['GET'])
@jwt_required()
@internal_user_required()
@admin_required()
def list_audit_route():
    return AgentConfigController.list_audit()


@agent_config.route('/tasks', methods=['GET'])
@jwt_required()
@internal_user_required()
@admin_required()
def list_tasks_route():
    return AgentConfigController.list_tasks()


@agent_config.route('/tasks/<int:task_id>/run', methods=['POST'])
@jwt_required()
@internal_user_required()
@admin_required()
def run_task_route(task_id):
    return AgentConfigController.run_task(task_id)
