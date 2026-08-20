from flask import Blueprint, render_template
from flask_jwt_extended import jwt_required

from commons.utils.decorators import internal_user_required
from controllers.chat.chat_controller import ChatController

chat = Blueprint('chat', __name__)


@chat.route('/', methods=['GET'])
def index():
    """Application web de dialogue (§4.4) — interface type DeepSeek, réservée aux utilisateurs internes."""
    return render_template('index.html')


@chat.route('/', methods=['POST'])
@jwt_required()
@internal_user_required()
def send_message_route():
    return ChatController.send_message()


@chat.route('/conversations', methods=['POST'])
@jwt_required()
@internal_user_required()
def new_conversation_route():
    return ChatController.new_conversation()


@chat.route('/conversations', methods=['GET'])
@jwt_required()
@internal_user_required()
def list_conversations_route():
    return ChatController.list_conversations()


@chat.route('/conversations/<int:conversation_id>/messages', methods=['GET'])
@jwt_required()
@internal_user_required()
def list_messages_route(conversation_id):
    return ChatController.list_messages(conversation_id)


@chat.route('/conversations/<int:conversation_id>', methods=['PUT'])
@jwt_required()
@internal_user_required()
def rename_conversation_route(conversation_id):
    return ChatController.rename_conversation(conversation_id)


@chat.route('/conversations/<int:conversation_id>', methods=['DELETE'])
@jwt_required()
@internal_user_required()
def delete_conversation_route(conversation_id):
    return ChatController.delete_conversation(conversation_id)


@chat.route('/dashboard', methods=['GET'])
@jwt_required()
@internal_user_required()
def dashboard_route():
    return ChatController.dashboard()


@chat.route('/dashboard/clients', methods=['GET'])
@jwt_required()
@internal_user_required()
def dashboard_clients_route():
    return ChatController.dashboard_clients()


@chat.route('/dashboard/extended', methods=['GET'])
@jwt_required()
@internal_user_required()
def dashboard_extended_route():
    return ChatController.dashboard_extended()


@chat.route('/pending', methods=['GET'])
@jwt_required()
@internal_user_required()
def pending_actions_route():
    return ChatController.pending_actions()
