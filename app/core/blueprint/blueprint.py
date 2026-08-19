from flask import Flask
from routes.auth.auth_routes import auth
from routes.chat.chat_routes import chat
from routes.confirmation.confirmation_routes import confirmation
from routes.email.email_routes import email
from routes.admin.agent_config_routes import agent_config
from routes.document.document_routes import document_bp


def initialize_blueprint_route(app: Flask):
    app.register_blueprint(auth, url_prefix='/api/auth')
    app.register_blueprint(chat, url_prefix='/api/chat')
    app.register_blueprint(confirmation, url_prefix='/api/confirmation')
    app.register_blueprint(document_bp, url_prefix='/api/documents')
    app.register_blueprint(email, url_prefix='/api/email')
    app.register_blueprint(agent_config, url_prefix='/api/admin/agent_config')

