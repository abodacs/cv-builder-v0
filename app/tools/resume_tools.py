import json
import logging
from typing import Any

import redis.asyncio as redis
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import BaseTool, tool
from pydantic import ValidationError

from app.core.config import Config
from app.core.schemas import Education, PersonalInfo, WorkExperience
from app.services.validation import DataValidator

# Instantiate the validator once for the module
validator = DataValidator()

logger = logging.getLogger(__name__)


async def get_redis_client() -> redis.Redis:
    """Get a Redis client for storing and retrieving data."""
    # In a real app, use proper connection pooling (e.g., redis.BlockingConnectionPool)
    # and potentially manage the client lifecycle better (e.g., dependency injection).
    # Store bytes for JSON
    return redis.Redis(
        host=Config.REDIS_HOST,
        port=Config.REDIS_PORT,
        db=Config.REDIS_DB,
        decode_responses=False,
    )


async def persist_section_data(thread_id: str, section: str, data: Any) -> None:
    """Saves validated section data to a Redis hash keyed by thread_id."""
    redis_key = f"cv_data:{thread_id}"
    # Serialize data to JSON string before storing in hash field
    json_data = json.dumps(data, ensure_ascii=False)
    try:
        r = await get_redis_client()
        # notype: ignore[union-attr]
        await r.hset(redis_key, section, json_data)
        # Optional: Set an expiration on the hash itself if it's newly created
        await r.expire(redis_key, Config.REDIS_TTL)  # Use configured TTL
        await r.close()  # Close single connection
        logger.info(
            f"Persisted data for section '{section}' to Redis hash '{redis_key}'."
        )
    except redis.RedisError as e:
        logger.error(
            f"Redis error persisting data for section '{section}' in '{redis_key}': {e}"
        )
        # Re-raise or handle as needed - maybe return an error status from the tool
        raise RuntimeError(
            f"Failed to save '{section}' data due to database error."
        ) from e
    except Exception as e:  # Catch unexpected errors during persistence
        logger.error(
            f"Unexpected error persisting data for section '{section}' in '{redis_key}': {e}",
            exc_info=True,
        )
        raise RuntimeError(
            f"Failed to save '{section}' data due to an unexpected error."
        ) from e


# --- Helper Function for Formatting Tool Responses ---


def format_tool_response(status: str, message: str) -> str:
    """Formats tool responses consistently as JSON strings."""
    response_data = {"status": status, "message": message}
    # Use ensure_ascii=False if messages might contain non-ASCII (e.g., Arabic)
    # Though current validation messages are English.
    return json.dumps(response_data, ensure_ascii=True)


# --- Tool Definitions ---


@tool
async def save_personal_info(
    personal_info: dict[str, Any], *, config: RunnableConfig
) -> str:
    """
    Validates and saves the personal information section.
    Expects a dictionary with keys like 'name', 'email', 'phone'.
    """
    section_name = "personal_info"
    thread_id = config.get("configurable", {}).get("thread_id")
    # user_token = config.get("configurable", {}).get("user_token" )  #   # Example: Get user token if needed

    if not thread_id:
        logger.error(f"Tool '{section_name}': Missing thread_id in config.")
        return format_tool_response(
            "error", "Internal error: Could not identify conversation session."
        )

    logger.info(f"Tool '{section_name}' [Thread: {thread_id}]: Validating and saving.")
    logger.debug(f"Tool '{section_name}' [Thread: {thread_id}]: Data: {personal_info}")

    try:
        # 1. Pydantic Validation (structure)
        validated_data = PersonalInfo(**personal_info).model_dump()
    except ValidationError as e:
        logger.warning(
            f"Tool '{section_name}' [Thread: {thread_id}]: Pydantic validation failed: {e}"
        )
        # Format Pydantic error for clarity
        error_details = "; ".join(
            [f"{err['loc'][0]}: {err['msg']}" for err in e.errors()]
        )
        return format_tool_response(
            "validation_error", f"Invalid data structure: {error_details}"
        )

    # 2. DataValidator Validation (format/presence)
    validation_message = validator.pre_validate_section_data(
        section_name, validated_data
    )

    if validation_message:
        logger.warning(
            f"Tool '{section_name}' [Thread: {thread_id}]: Validation failed: {validation_message}"
        )
        return format_tool_response("validation_error", validation_message)
    else:
        logger.info(
            f"Tool '{section_name}' [Thread: {thread_id}]: Validation successful."
        )
        try:
            # 3. Persist Data
            await persist_section_data(thread_id, section_name, validated_data)
            return format_tool_response("success", "Personal info saved successfully.")
        except Exception as e:
            logger.error(
                f"Tool '{section_name}' [Thread: {thread_id}]: Error during persistence: {e}",
                exc_info=True,
            )
            return format_tool_response(
                "error",
                "Sorry, an internal error occurred while saving. Please try again.",
            )


@tool
async def save_work_experience(
    work_experience: list[dict[str, Any]], *, config: RunnableConfig
) -> str:
    """
    Validates and saves the work experience section (list of experiences).
    Each item should have 'company' and 'title'.
    """
    section_name = "work_experience"
    thread_id = config.get("configurable", {}).get("thread_id")
    if not thread_id:
        return format_tool_response(
            "error", "Internal error: Could not identify conversation session."
        )

    logger.info(f"Tool '{section_name}' [Thread: {thread_id}]: Validating and saving.")
    logger.debug(
        f"Tool '{section_name}' [Thread: {thread_id}]: Data Count: {len(work_experience)}"
    )

    if not isinstance(work_experience, list):
        return format_tool_response(
            "validation_error", "Invalid input type: Work experience must be a list."
        )

    validated_list = []
    try:
        # 1. Pydantic Validation (structure per item)
        for item in work_experience:
            validated_data = WorkExperience(**item).model_dump()
            validated_list.append(validated_data)
    except ValidationError as e:
        logger.warning(
            f"Tool '{section_name}' [Thread: {thread_id}]: Pydantic validation failed for an item: {e}"
        )
        error_details = "; ".join(
            [f"{err['loc'][0]}: {err['msg']}" for err in e.errors()]
        )
        return format_tool_response(
            "validation_error", f"Invalid data in one of the entries: {error_details}"
        )

    # 2. DataValidator Validation (list content/rules)
    validation_message = validator.pre_validate_section_data(
        section_name, validated_list
    )

    if validation_message:
        logger.warning(
            f"Tool '{section_name}' [Thread: {thread_id}]: Validation failed: {validation_message}"
        )
        return format_tool_response("validation_error", validation_message)
    else:
        logger.info(
            f"Tool '{section_name}' [Thread: {thread_id}]: Validation successful."
        )
        try:
            # 3. Persist Data (the whole validated list)
            await persist_section_data(thread_id, section_name, validated_list)
            return format_tool_response(
                "success", "Work experience saved successfully."
            )
        except Exception as e:
            logger.error(
                f"Tool '{section_name}' [Thread: {thread_id}]: Error during persistence: {e}",
                exc_info=True,
            )
            return format_tool_response(
                "error",
                "Sorry, an internal error occurred while saving. Please try again.",
            )


@tool
async def save_education(
    education: list[dict[str, Any]], *, config: RunnableConfig
) -> str:
    """
    Validates and saves the education section (list of education entries).
    Each item should have 'school' and 'degree'.
    """
    section_name = "education"
    thread_id = config.get("configurable", {}).get("thread_id")
    if not thread_id:
        return format_tool_response(
            "error", "Internal error: Could not identify conversation session."
        )

    logger.info(f"Tool '{section_name}' [Thread: {thread_id}]: Validating and saving.")
    logger.debug(
        f"Tool '{section_name}' [Thread: {thread_id}]: Data Count: {len(education)}"
    )

    if not isinstance(education, list):
        return format_tool_response(
            "validation_error", "Invalid input type: Education must be a list."
        )

    validated_list = []
    try:
        # 1. Pydantic Validation (structure per item)
        for item in education:
            validated_data = Education(**item).model_dump()
            validated_list.append(validated_data)
    except ValidationError as e:
        logger.warning(
            f"Tool '{section_name}' [Thread: {thread_id}]: Pydantic validation failed for an item: {e}"
        )
        error_details = "; ".join(
            [f"{err['loc'][0]}: {err['msg']}" for err in e.errors()]
        )
        return format_tool_response(
            "validation_error", f"Invalid data in one of the entries: {error_details}"
        )

    # 2. DataValidator Validation
    validation_message = validator.pre_validate_section_data(
        section_name, validated_list
    )

    if validation_message:
        logger.warning(
            f"Tool '{section_name}' [Thread: {thread_id}]: Validation failed: {validation_message}"
        )
        return format_tool_response("validation_error", validation_message)
    else:
        logger.info(
            f"Tool '{section_name}' [Thread: {thread_id}]: Validation successful."
        )
        try:
            # 3. Persist Data
            await persist_section_data(thread_id, section_name, validated_list)
            return format_tool_response("success", "Education saved successfully.")
        except Exception as e:
            logger.error(
                f"Tool '{section_name}' [Thread: {thread_id}]: Error during persistence: {e}",
                exc_info=True,
            )
            return format_tool_response(
                "error",
                "Sorry, an internal error occurred while saving. Please try again.",
            )


@tool
async def save_skills(skills: list[str], *, config: RunnableConfig) -> str:
    """
    Validates and saves the skills section (list of skills).
    Expects a list of non-empty strings.
    """
    section_name = "skills"
    thread_id = config.get("configurable", {}).get("thread_id")
    if not thread_id:
        return format_tool_response(
            "error", "Internal error: Could not identify conversation session."
        )

    logger.info(f"Tool '{section_name}' [Thread: {thread_id}]: Validating and saving.")
    logger.debug(f"Tool '{section_name}' [Thread: {thread_id}]: Data: {skills}")

    if not isinstance(skills, list):
        return format_tool_response(
            "validation_error", "Invalid input type: Skills must be a list."
        )

    # 1. Pydantic/Basic validation happens within DataValidator for lists of strings

    # 2. DataValidator Validation
    validation_message = validator.pre_validate_section_data(section_name, skills)

    if validation_message:
        logger.warning(
            f"Tool '{section_name}' [Thread: {thread_id}]: Validation failed: {validation_message}"
        )
        return format_tool_response("validation_error", validation_message)
    else:
        # Filter out empty strings just in case, although validator should catch it
        validated_skills = [s for s in skills if isinstance(s, str) and s.strip()]
        logger.info(
            f"Tool '{section_name}' [Thread: {thread_id}]: Validation successful."
        )
        try:
            # 3. Persist Data
            await persist_section_data(thread_id, section_name, validated_skills)
            return format_tool_response("success", "Skills saved successfully.")
        except Exception as e:
            logger.error(
                f"Tool '{section_name}' [Thread: {thread_id}]: Error during persistence: {e}",
                exc_info=True,
            )
            return format_tool_response(
                "error",
                "Sorry, an internal error occurred while saving. Please try again.",
            )


resume_tools: list[BaseTool] = [
    save_personal_info,
    save_work_experience,
    save_education,
    save_skills,
]
