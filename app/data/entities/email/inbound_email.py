from datetime import datetime, timezone
from data.entities.config.entities_config import db


class InboundEmail(db.Model):
    """Trace chaque e-mail entrant reçu via IMAP ou injecté pour traitement (§4.5).
    Stocke le contenu brut/nettoyé, le statut de sécurité (liste blanche + prompt guard),
    l'analyse réalisée par l'agent IA, la réponse suggérée, l'action Dolibarr proposée,
    et l'état de validation humaine (Human-in-the-Loop).
    """

    __tablename__ = 'inbound_emails'

    id = db.Column(db.Integer, primary_key=True)
    uid = db.Column(db.String(100), nullable=True, index=True)  # UID IMAP ou identifiant unique
    sender = db.Column(db.String(255), nullable=False, index=True)
    sender_name = db.Column(db.String(255), nullable=True)
    recipient = db.Column(db.String(255), nullable=True)
    subject = db.Column(db.String(500), nullable=True)
    body_raw = db.Column(db.Text, nullable=True)
    body_clean = db.Column(db.Text, nullable=True)
    received_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    # Sécurité (§4.5, §5.1)
    security_allowed = db.Column(db.Boolean, default=True, nullable=False)
    security_suspicious = db.Column(db.Boolean, default=False, nullable=False)
    security_reason = db.Column(db.String(255), nullable=True)

    # Analyse de l'agent IA
    agent_summary = db.Column(db.Text, nullable=True)
    detected_intent = db.Column(db.String(100), nullable=True)  # quote_request, invoice_inquiry, stock_query, etc.
    suggested_reply = db.Column(db.Text, nullable=True)
    suggested_action_type = db.Column(db.String(100), nullable=True)  # send_reply, create_quote, create_invoice, etc.
    suggested_action_params = db.Column(db.JSON, nullable=True)
    suggested_action_label = db.Column(db.String(255), nullable=True)

    # Workflow de validation humaine (§3.2, §4.5)
    # Statuts : pending_review | replied | action_executed | rejected | ignored | suspicious
    status = db.Column(db.String(50), default='pending_review', nullable=False, index=True)
    user_notes = db.Column(db.Text, nullable=True)
    
    reply_sent_at = db.Column(db.DateTime(timezone=True), nullable=True)
    reply_sent_subject = db.Column(db.String(500), nullable=True)
    reply_sent_body = db.Column(db.Text, nullable=True)
    executed_action_result = db.Column(db.JSON, nullable=True)

    conversation_id = db.Column(db.Integer, db.ForeignKey('conversations.id'), nullable=True)

    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    def to_dict(self):
        return {
            "id": self.id,
            "uid": self.uid,
            "sender": self.sender,
            "sender_name": self.sender_name,
            "recipient": self.recipient,
            "subject": self.subject or "(Sans objet)",
            "body_raw": self.body_raw,
            "body_clean": self.body_clean,
            "received_at": self.received_at.isoformat() if self.received_at else None,
            "security_allowed": self.security_allowed,
            "security_suspicious": self.security_suspicious,
            "security_reason": self.security_reason,
            "agent_summary": self.agent_summary,
            "detected_intent": self.detected_intent,
            "suggested_reply": self.suggested_reply,
            "suggested_action_type": self.suggested_action_type,
            "suggested_action_params": self.suggested_action_params,
            "suggested_action_label": self.suggested_action_label,
            "status": self.status,
            "user_notes": self.user_notes,
            "reply_sent_at": self.reply_sent_at.isoformat() if self.reply_sent_at else None,
            "reply_sent_subject": self.reply_sent_subject,
            "reply_sent_body": self.reply_sent_body,
            "executed_action_result": self.executed_action_result,
            "conversation_id": self.conversation_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
