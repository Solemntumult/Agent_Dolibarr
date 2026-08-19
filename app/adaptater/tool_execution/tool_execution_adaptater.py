from commons.instances.instances import logger
from data.entities.config.entities_config import db
from data.entities.tool_execution.tool_execution import ToolExecution


class ToolExecutionAdaptater:

    @staticmethod
    def get_by_id(tool_execution_id):
        return ToolExecution.query.filter_by(id=tool_execution_id).first()

    @staticmethod
    def create_pending(tool_name, tool_sense, parameters, conversation_id=None, user_id=None) -> ToolExecution:
        try:
            tool_execution = ToolExecution(
                tool_name=tool_name,
                tool_sense=tool_sense,
                parameters=parameters,
                conversation_id=conversation_id,
                user_id=user_id,
                confirmation_status="pending",
            )
            db.session.add(tool_execution)
            db.session.commit()
            return tool_execution
        except Exception as e:
            logger.error(f"Error creating pending tool execution: {e}")
            db.session.rollback()
            raise e

    @staticmethod
    def mark_confirmed(tool_execution_id, confirmed_by_user_id) -> bool:
        from datetime import datetime, timezone
        try:
            tool_execution = ToolExecutionAdaptater.get_by_id(tool_execution_id)
            if not tool_execution:
                return False
            tool_execution.confirmation_status = "confirmed"
            tool_execution.confirmed_by_user_id = confirmed_by_user_id
            tool_execution.confirmed_at = datetime.now(timezone.utc)
            db.session.commit()
            return True
        except Exception as e:
            logger.error(f"Error confirming tool execution: {e}")
            db.session.rollback()
            return False
