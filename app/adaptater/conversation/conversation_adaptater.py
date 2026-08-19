"""Adaptateur conversations / messages — base interne (§4.7 : historique des conversations)."""
from commons.instances.instances import logger
from data.entities.config.entities_config import db
from data.entities.conversation.conversation import Conversation
from data.entities.message.message import Message


class ConversationAdaptater:

    @staticmethod
    def create(user_id: int = None, channel: str = "web", title: str = None) -> Conversation:
        try:
            conversation = Conversation(
                user_id=user_id,
                channel=channel or "web",
                title=title or "Nouvelle conversation",
            )
            db.session.add(conversation)
            db.session.commit()
            return conversation
        except Exception as e:
            logger.error(f"ConversationAdaptater.create failed: {e}")
            db.session.rollback()
            raise e

    @staticmethod
    def get_by_id(conversation_id: int):
        return Conversation.query.filter_by(id=conversation_id).first()

    @staticmethod
    def list_by_user(user_id: int, limit: int = 50) -> list:
        try:
            conversations = (
                Conversation.query
                .filter_by(user_id=user_id, is_archived=False)
                .order_by(Conversation.updated_at.desc())
                .limit(limit)
                .all()
            )
            return [conv.to_dict() for conv in conversations]
        except Exception as e:
            logger.error(f"ConversationAdaptater.list_by_user failed: {e}")
            return []

    @staticmethod
    def get_or_create_last(user_id: int, conversation_id: int = None) -> Conversation:
        """Retourne la conversation demandée, ou crée une nouvelle si non fournie."""
        if conversation_id:
            conversation = ConversationAdaptater.get_by_id(conversation_id)
            if conversation and conversation.user_id == user_id:
                return conversation
        return ConversationAdaptater.create(user_id=user_id)

    @staticmethod
    def add_message(conversation_id: int, role: str, content: str,
                    model_tier_used: str = None, tokens_input: int = None,
                    tokens_output: int = None) -> Message:
        try:
            message = Message(
                conversation_id=conversation_id,
                role=role,
                content=content,
                model_tier_used=model_tier_used,
                tokens_input=tokens_input,
                tokens_output=tokens_output,
            )
            db.session.add(message)
            conversation = ConversationAdaptater.get_by_id(conversation_id)
            if conversation and (not conversation.title or conversation.title == "Nouvelle conversation"):
                conversation.title = content[:60]
            db.session.commit()
            return message
        except Exception as e:
            logger.error(f"ConversationAdaptater.add_message failed: {e}")
            db.session.rollback()
            raise e

    @staticmethod
    def update_title(conversation_id: int, title: str) -> bool:
        """Renomme une conversation (libellé affiché dans la liste)."""
        try:
            conversation = ConversationAdaptater.get_by_id(conversation_id)
            if not conversation:
                return False
            title = (title or "").strip()
            if not title:
                return False
            conversation.title = title[:120]
            db.session.commit()
            return True
        except Exception as e:
            logger.error(f"ConversationAdaptater.update_title({conversation_id}) failed: {e}")
            db.session.rollback()
            return False

    @staticmethod
    def delete(conversation_id: int) -> bool:
        """Supprime définitivement une conversation et ses messages."""
        try:
            conversation = ConversationAdaptater.get_by_id(conversation_id)
            if not conversation:
                return False
            Message.query.filter_by(conversation_id=conversation_id).delete()
            db.session.delete(conversation)
            db.session.commit()
            return True
        except Exception as e:
            logger.error(f"ConversationAdaptater.delete({conversation_id}) failed: {e}")
            db.session.rollback()
            return False

    @staticmethod
    def get_messages(conversation_id: int, limit: int = 100) -> list:
        try:
            messages = (
                Message.query
                .filter_by(conversation_id=conversation_id)
                .order_by(Message.created_at.asc())
                .limit(limit)
                .all()
            )
            return [m.to_dict() for m in messages]
        except Exception as e:
            logger.error(f"ConversationAdaptater.get_messages failed: {e}")
            return []

    @staticmethod
    def get_history_for_llm(conversation_id: int, limit: int = 20) -> list:
        """Historique au format OpenAI (rôles user/assistant) pour le contexte LLM."""
        messages = ConversationAdaptater.get_messages(conversation_id, limit=limit)
        history = []
        for m in messages:
            if m["role"] in ("user", "assistant"):
                history.append({"role": m["role"], "content": m["content"]})
        return history
