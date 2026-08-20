from datetime import datetime, timezone
from data.entities.config.entities_config import db
from data.entities.email.inbound_email import InboundEmail
from commons.instances.instances import logger


class InboundEmailAdaptater:

    @staticmethod
    def create(
        sender: str,
        subject: str = None,
        body_raw: str = None,
        body_clean: str = None,
        uid: str = None,
        sender_name: str = None,
        recipient: str = None,
        security_allowed: bool = True,
        security_suspicious: bool = False,
        security_reason: str = None,
        agent_summary: str = None,
        detected_intent: str = None,
        suggested_reply: str = None,
        suggested_action_type: str = None,
        suggested_action_params: dict = None,
        suggested_action_label: str = None,
        status: str = 'pending_review',
        conversation_id: int = None,
        received_at: datetime = None,
    ) -> InboundEmail:
        try:
            email_obj = InboundEmail(
                uid=uid,
                sender=sender,
                sender_name=sender_name,
                recipient=recipient,
                subject=subject,
                body_raw=body_raw,
                body_clean=body_clean,
                security_allowed=security_allowed,
                security_suspicious=security_suspicious,
                security_reason=security_reason,
                agent_summary=agent_summary,
                detected_intent=detected_intent,
                suggested_reply=suggested_reply,
                suggested_action_type=suggested_action_type,
                suggested_action_params=suggested_action_params,
                suggested_action_label=suggested_action_label,
                status=status,
                conversation_id=conversation_id,
                received_at=received_at or datetime.now(timezone.utc),
            )
            db.session.add(email_obj)
            db.session.commit()
            return email_obj
        except Exception as e:
            db.session.rollback()
            logger.error(f"InboundEmailAdaptater.create error: {e}")
            raise e

    @staticmethod
    def get_by_id(email_id: int) -> InboundEmail:
        return InboundEmail.query.filter_by(id=email_id).first()

    @staticmethod
    def get_by_uid(uid: str) -> InboundEmail:
        if not uid:
            return None
        return InboundEmail.query.filter_by(uid=str(uid)).first()

    @staticmethod
    def list_emails(status: str = None, limit: int = 100, offset: int = 0) -> list:
        query = InboundEmail.query
        if status and status != 'all':
            if status == 'pending':
                query = query.filter_by(status='pending_review')
            elif status == 'processed':
                query = query.filter(InboundEmail.status.in_(['replied', 'action_executed']))
            elif status == 'suspicious':
                query = query.filter((InboundEmail.security_suspicious == True) | (InboundEmail.status == 'suspicious') | (InboundEmail.security_allowed == False))
            elif status == 'rejected':
                query = query.filter_by(status='rejected')
            else:
                query = query.filter_by(status=status)
        return query.order_by(InboundEmail.received_at.desc(), InboundEmail.id.desc()).offset(offset).limit(limit).all()

    @staticmethod
    def count_by_status() -> dict:
        total = InboundEmail.query.count()
        pending = InboundEmail.query.filter_by(status='pending_review').count()
        replied = InboundEmail.query.filter_by(status='replied').count()
        action_executed = InboundEmail.query.filter_by(status='action_executed').count()
        rejected = InboundEmail.query.filter_by(status='rejected').count()
        suspicious = InboundEmail.query.filter(
            (InboundEmail.security_suspicious == True) | (InboundEmail.security_allowed == False)
        ).count()
        return {
            "total": total,
            "pending": pending,
            "replied": replied,
            "action_executed": action_executed,
            "processed": replied + action_executed,
            "rejected": rejected,
            "suspicious": suspicious,
        }

    @staticmethod
    def update_reply(email_id: int, reply_body: str, reply_subject: str = None) -> InboundEmail:
        email_obj = InboundEmail.query.filter_by(id=email_id).first()
        if not email_obj:
            return None
        email_obj.suggested_reply = reply_body
        if reply_subject:
            email_obj.reply_sent_subject = reply_subject
        email_obj.updated_at = datetime.now(timezone.utc)
        db.session.commit()
        return email_obj

    @staticmethod
    def mark_replied(email_id: int, sent_body: str, sent_subject: str = None) -> InboundEmail:
        email_obj = InboundEmail.query.filter_by(id=email_id).first()
        if not email_obj:
            return None
        email_obj.status = 'replied'
        email_obj.reply_sent_at = datetime.now(timezone.utc)
        email_obj.reply_sent_body = sent_body
        if sent_subject:
            email_obj.reply_sent_subject = sent_subject
        email_obj.updated_at = datetime.now(timezone.utc)
        db.session.commit()
        return email_obj

    @staticmethod
    def mark_action_executed(email_id: int, result: dict, notes: str = None) -> InboundEmail:
        email_obj = InboundEmail.query.filter_by(id=email_id).first()
        if not email_obj:
            return None
        email_obj.status = 'action_executed'
        email_obj.executed_action_result = result
        if notes:
            email_obj.user_notes = notes
        email_obj.updated_at = datetime.now(timezone.utc)
        db.session.commit()
        return email_obj

    @staticmethod
    def mark_rejected(email_id: int, reason: str = None) -> InboundEmail:
        email_obj = InboundEmail.query.filter_by(id=email_id).first()
        if not email_obj:
            return None
        email_obj.status = 'rejected'
        if reason:
            email_obj.user_notes = reason
        email_obj.updated_at = datetime.now(timezone.utc)
        db.session.commit()
        return email_obj
