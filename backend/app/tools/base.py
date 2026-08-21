import uuid
import logging
from abc import ABC, abstractmethod
from enum import Enum
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class ActionClass(str, Enum):
    READ_ONLY = "read_only"
    REVERSIBLE = "reversible"
    REQUIRES_APPROVAL = "requires_approval"
    BLOCKED = "blocked"


class ToolValidationError(Exception):
    pass


class ToolAuthorizationError(Exception):
    pass


class BaseTool(ABC):
    name: str
    description: str
    parameters: dict
    action_class: ActionClass

    def get_definition(self) -> dict:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }

    def validate_inputs(self, **kwargs) -> dict:
        schema_props = self.parameters.get("properties", {})
        required = self.parameters.get("required", [])
        validated = {}

        for param_name in required:
            if param_name not in kwargs or kwargs[param_name] is None:
                raise ToolValidationError(
                    f"Missing required parameter: {param_name}"
                )

        for param_name, param_schema in schema_props.items():
            if param_name in kwargs and kwargs[param_name] is not None:
                param_type = param_schema.get("type")
                value = kwargs[param_name]

                if param_type == "integer":
                    validated[param_name] = int(value)
                elif param_type == "number":
                    validated[param_name] = float(value)
                elif param_type == "string":
                    validated[param_name] = str(value)
                elif param_type == "boolean":
                    validated[param_name] = bool(value)
                elif param_type == "array":
                    validated[param_name] = list(value) if not isinstance(value, list) else value
                elif param_type == "object":
                    validated[param_name] = dict(value) if not isinstance(value, dict) else value
                else:
                    validated[param_name] = value

        for param_name in required:
            if param_name not in validated:
                validated[param_name] = kwargs[param_name]

        return validated

    def check_authorization(self, action_class: ActionClass | None = None) -> None:
        cls = action_class or self.action_class
        if cls == ActionClass.BLOCKED:
            raise ToolAuthorizationError(
                f"Tool '{self.name}' is blocked and cannot be executed"
            )

    @abstractmethod
    async def execute(
        self, db: AsyncSession, merchant_id: uuid.UUID, **kwargs
    ) -> dict:
        ...

    async def safe_execute(
        self, db: AsyncSession, merchant_id: uuid.UUID, **kwargs
    ) -> dict:
        try:
            self.check_authorization()
            validated = self.validate_inputs(**kwargs)
            logger.info(
                f"Executing tool '{self.name}' for merchant {merchant_id} "
                f"with params: {list(validated.keys())}"
            )
            result = await self.execute(db, merchant_id, **validated)
            logger.info(f"Tool '{self.name}' completed successfully")
            return {
                "success": True,
                "tool_name": self.name,
                "action_class": self.action_class.value,
                "data": result,
            }
        except ToolValidationError as e:
            logger.warning(f"Tool validation error for '{self.name}': {e}")
            return {
                "success": False,
                "tool_name": self.name,
                "error": f"Validation error: {str(e)}",
            }
        except ToolAuthorizationError as e:
            logger.warning(f"Tool authorization error for '{self.name}': {e}")
            return {
                "success": False,
                "tool_name": self.name,
                "error": f"Authorization error: {str(e)}",
            }
        except Exception as e:
            logger.exception(f"Tool execution error for '{self.name}': {e}")
            return {
                "success": False,
                "tool_name": self.name,
                "error": f"Execution error: {str(e)}",
            }
