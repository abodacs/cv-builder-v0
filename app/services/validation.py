import asyncio
import logging
import re
from dataclasses import dataclass
from typing import Any

from openai import AsyncOpenAI
from tenacity import retry, stop_after_attempt, wait_exponential_jitter

from app.core.config import Config
from app.core.constants import PROMPTS

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class ValidationRule:
    """Defines validation criteria for a CV section."""

    # Fields required within this section's data structure
    # Can be empty if validation focuses on content rather than specific named fields
    required_fields: list[str]
    # Regex patterns for specific fields within this section
    format_rules: dict[str, str]
    # Prompt template instructing the LLM on how to validate this section
    prompt_template: str
    # Optional: Whether the section itself is required in the CV
    section_required: bool = True  # Most sections are required for a complete CV


class DataValidator:
    """
    Validates CV data sections using predefined rules and an AI model.
    Covers all sections defined in PROMPTS.
    """

    def __init__(self) -> None:
        # Ensure Config has OPENAI_API_KEY and OPENAI_MODEL defined
        if not hasattr(Config, "OPENAI_API_KEY") or not Config.OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY not configured in Config")
        if not hasattr(Config, "OPENAI_MODEL") or not Config.OPENAI_MODEL:
            raise ValueError("OPENAI_MODEL not configured in Config")
        # Initialize the OpenAI client with the API key and base URL
        print("API Key:", Config.OPENAI_API_KEY)
        print("Base URL:", Config.OPENAI_API_BASE_URL)
        self.client = AsyncOpenAI(
            api_key=Config.OPENAI_API_KEY, base_url=Config.OPENAI_API_BASE_URL
        )
        # Define validation rules for each section found in PROMPTS['en']
        # Using 'en' as the reference for section names
        self._validation_rules: dict[str, ValidationRule] = {
            "personal_info": ValidationRule(
                # Address is often optional
                required_fields=["name", "email", "phone"],
                format_rules={
                    # Basic email format check
                    "email": r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$",
                    # Basic phone format check (allows +, digits, spaces, hyphens, min 8 digits)
                    "phone": r"^\+?[\d\s-]{8,}$",
                    # More specific rules could be added (e.g., for LinkedIn URL if field exists)
                },
                prompt_template="""
                Validate the Personal Information section of a CV based on these criteria:
                1. Name: Should be a plausible full name, correctly capitalized.
                2. Email: Must be present and in a valid email format (e.g., user@domain.com).
                3. Phone: Must be present and look like a valid phone number (ideally with country code).
                4. Address (if provided): Should be a plausible address structure.
                5. Completeness: Check if mandatory fields (name, email, phone) are present and non-empty.

                Respond ONLY in this strict format:
                VALID/INVALID: [Brief reason for overall status (e.g., VALID, INVALID: Missing email, INVALID: Invalid phone format)]
                Issues: [Bulleted list of specific problems found, e.g., "- Missing required field: email", "- Invalid format for phone number", "- Name appears unrealistic"]
                Suggestions: [Bulleted list of specific improvements, e.g., "- Provide a valid email address", "- Add country code to phone number", "- Capitalize name correctly"]

                Data to validate:
                """,
                section_required=True,
            ),
            "education": ValidationRule(
                required_fields=[],  # Often a list; specific fields are within list items
                # Format rules (e.g., date) would apply to list items, harder to pre-validate here
                format_rules={},
                prompt_template="""
                Validate the Education section of a CV based on these criteria:
                1. Clarity & Completeness: Each entry should clearly state the institution, degree/qualification, and dates (or expected date) of attendance/graduation. Field of study is important.
                2. Formatting: Information should be well-organized (e.g., reverse chronological order is common). Dates should be consistent.
                3. Relevance: Ensure the content describes educational background.
                4. Plausibility: Check for realistic institution names, degrees, and timelines.

                Respond ONLY in this strict format:
                VALID/INVALID: [Brief reason for overall status (e.g., VALID, INVALID: Missing crucial details, INVALID: Unclear format)]
                Issues: [Bulleted list of specific problems found, e.g., "- Missing institution name in one entry", "- Dates are ambiguous (e.g., '2020')", "- Unclear degree mentioned"]
                Suggestions: [Bulleted list of specific improvements, e.g., "- Add graduation year for each degree", "- Specify field of study", "- Consider listing in reverse chronological order"]

                Data to validate:
                """,
                section_required=True,
            ),
            "work_experience": ValidationRule(
                required_fields=[],  # Often a list; specific fields are within list items
                # Format rules (e.g., date) would apply to list items
                format_rules={},
                prompt_template="""
                Validate the Work Experience section of a CV based on these criteria:
                1. Clarity & Completeness: Each entry should clearly state the company, job title, and dates of employment. Responsibilities or achievements are crucial.
                2. Action Verbs & Impact: Descriptions should ideally start with action verbs and quantify achievements where possible.
                3. Formatting: Information should be well-organized (e.g., reverse chronological order is standard). Dates should be clear and consistent.
                4. Relevance: Ensure the content describes professional work history.
                5. Plausibility: Check for realistic company names, job titles, and timelines.

                Respond ONLY in this strict format:
                VALID/INVALID: [Brief reason for overall status (e.g., VALID, INVALID: Missing job descriptions, INVALID: Inconsistent dates)]
                Issues: [Bulleted list of specific problems found, e.g., "- Missing dates for the first job listed", "- Job descriptions are too vague", "- Inconsistent date format used"]
                Suggestions: [Bulleted list of specific improvements, e.g., "- Add specific responsibilities/achievements for each role", "- Use action verbs to start bullet points", "- Ensure all entries have clear start/end dates (or 'Present')", "- List in reverse chronological order"]

                Data to validate:
                """,
                section_required=True,
            ),
            "skills": ValidationRule(
                required_fields=[],  # Often a list or comma-separated string
                format_rules={},
                prompt_template="""
                Validate the Skills section of a CV based on these criteria:
                1. Clarity: Skills should be clearly listed and understandable. Avoid jargon where possible unless industry-standard.
                2. Organization: Skills might be grouped (e.g., Technical Skills, Soft Skills, Languages). Check if the organization makes sense.
                3. Relevance: Skills listed should generally be relevant to professional contexts.
                4. Conciseness: Should be a list or groups of skills, not lengthy paragraphs.

                Respond ONLY in this strict format:
                VALID/INVALID: [Brief reason for overall status (e.g., VALID, INVALID: Too vague, INVALID: Poorly organized)]
                Issues: [Bulleted list of specific problems found, e.g., "- Skills list is just one long paragraph", "- Some listed items are not actual skills (e.g., 'Hard worker')", "- Vague terms like 'Computer skills' used"]
                Suggestions: [Bulleted list of specific improvements, e.g., "- Group skills into categories (e.g., Programming Languages, Software, Soft Skills)", "- Be specific (e.g., instead of 'Computer skills', list 'Microsoft Office Suite, Google Workspace')", "- List skills concisely, perhaps using bullet points"]

                Data to validate:
                """,
                section_required=True,
            ),
            "finalize": ValidationRule(
                required_fields=[],
                format_rules={},
                # Finalize doesn't usually contain data itself, but we might use this
                # step to trigger a final overview validation if needed.
                # The prompt below assumes it might check the *presence* or *readiness* state.
                # Alternatively, this could be removed if 'finalize' is purely a workflow step.
                prompt_template="""
                Validate the final readiness state for CV generation.
                1. Completeness Check: Primarily, this step implies other sections should be filled. (This check might be better done *before* calling this validator).
                2. Placeholder Check: Ensure no obvious placeholders like "[Your Name Here]" remain in the *overall* data (though this validator only sees the 'finalize' section data, which is usually empty or a simple status).

                *Note: Validation for 'finalize' is limited as it typically holds no user content.* Assume the data provided is just a confirmation or status indicator.

                Respond ONLY in this strict format:
                VALID/INVALID: [VALID if data seems like a standard final step confirmation, INVALID otherwise]
                Issues: [Bulleted list of specific problems found, if any]
                Suggestions: [Bulleted list of specific improvements, if any]

                Data to validate:
                """,
                # Finalize step itself isn't data-critical like others
                section_required=False,
            ),
        }
        # Dynamically add any missing section keys from PROMPTS['en'] with a default rule
        # This ensures if PROMPTS adds a new section, the validator won't crash immediately
        # although the default rule might not be very effective.
        default_prompt = """
        Validate the content provided for this section. Check for:
        1. Clarity and understandability.
        2. Completeness based on common expectations for this type of CV section.
        3. Any obvious errors or placeholders.

        Respond ONLY in this strict format:
        VALID/INVALID: [Brief reason for overall status]
        Issues: [Bulleted list of specific problems found]
        Suggestions: [Bulleted list of specific improvements]

        Data to validate:
        """
        for section_key in PROMPTS.get("en", {}):
            if section_key not in self._validation_rules:
                logger.warning(
                    f"Section '{section_key}' found in PROMPTS but not explicitly defined in DataValidator rules. Adding a default rule."
                )
                self._validation_rules[section_key] = ValidationRule(
                    required_fields=[],
                    format_rules={},
                    prompt_template=default_prompt,
                    section_required=False,  # Default to not required
                )

    def pre_validate_section_data(
        self, section: str, data: dict[str, Any] | list[Any] | str | None
    ) -> str | None:
        """
        Perform preliminary validation checks on data for a specific section.
        Suitable for use within tools before proceeding.

        Args:
            section: The section name (e.g., 'personal_info').
            data: The data structure for that section (dict, list, str, None).

        Returns:
            An error message string if validation fails, None otherwise.
        """
        if section not in self._validation_rules:
            logger.error(f"Attempted to pre-validate unknown section: {section}")
            # Return user-friendly error for the tool to pass back
            return f"Internal configuration error: Cannot validate unknown section '{section}'."

        rule = self._validation_rules[section]

        # 1. Check for missing required section if data is empty/None
        if not data and rule.section_required:
            # Explicitly check for empty lists/dicts too
            if (isinstance(data, list | dict) and not data) or data is None:
                return f"Missing required data for section: {section}"
        elif not data:
            return None  # Optional section is missing/empty, OK.

        # 2. Field-specific checks (if data is a dictionary)
        if isinstance(data, dict):
            errors = []
            # Check required fields are present and non-empty strings if applicable
            missing_or_empty = []
            for f in rule.required_fields:
                val = data.get(f)
                if val is None or (isinstance(val, str) and not val.strip()):
                    missing_or_empty.append(f)
            if missing_or_empty:
                errors.append(
                    f"Missing or empty required fields: {', '.join(missing_or_empty)}"
                )

            # Check format rules for present, non-empty fields
            format_errors = []
            for field, pattern in rule.format_rules.items():
                value = data.get(field)
                if (
                    isinstance(value, str)
                    and value.strip()
                    and not self._validate_format(field, value, pattern)
                ):
                    # Provide more specific error messages
                    if field == "email":
                        format_errors.append(
                            f"The format for '{field}' seems incorrect. Please use a valid email address (e.g., name@example.com)."
                        )
                    elif field == "phone":
                        format_errors.append(
                            f"The format for '{field}' seems incorrect. Please provide a valid phone number (e.g., including area/country code)."
                        )
                    else:
                        format_errors.append(f"Invalid format for field '{field}'.")

            if format_errors:
                errors.extend(format_errors)

            return "; ".join(errors) if errors else None

        # 3. Basic list checks (if data is a list, e.g., education, experience, skills)
        elif isinstance(data, list):
            if rule.section_required and not data:
                return f"Section '{section}' requires at least one entry, but the list is empty."

            # Check structure/content of list items
            item_errors = []
            for i, item in enumerate(data):
                item_num = i + 1
                if section in ["education", "work_experience"]:
                    if not isinstance(item, dict):
                        item_errors.append(
                            f"Entry {item_num} in '{section}' is not structured correctly."
                        )
                    # Add check for a key that should usually exist, like 'title' or 'school' depending on Pydantic models
                    elif section == "education" and not item.get("school"):
                        item_errors.append(
                            f"Entry {item_num} in '{section}' is missing the 'school' name."
                        )
                    elif section == "work_experience" and not item.get("company"):
                        item_errors.append(
                            f"Entry {item_num} in '{section}' is missing the 'company' name."
                        )
                    # Check if *some* detail exists
                    elif not item.get("details") and not (
                        item.get("title") or item.get("degree")
                    ):
                        item_errors.append(
                            f"Entry {item_num} in '{section}' seems incomplete (missing details/title/degree)."
                        )
                elif (
                    section == "skills" and not isinstance(item, str)
                ) or not item.strip():
                    item_errors.append(
                        f"Skill entry {item_num} in '{section}' is invalid or empty."
                    )

            return "; ".join(item_errors) if item_errors else None

        # 4. Handle other types if necessary (e.g., simple string for summary)
        elif isinstance(data, str):
            if rule.section_required and not data.strip():
                return f"The content for section '{section}' cannot be empty."
            # Add length check? Example:
            # if section == 'summary' and len(data) < 10:
            #     return f"The summary for '{section}' seems too short."
            return None  # Basic string validation passes

        else:
            logger.warning(
                f"Unexpected data type ({type(data)}) for section {section} during pre-validation."
            )
            return (
                f"Internal error: Unexpected data type received for section {section}."
            )

    async def validate_cv(
        self, section: str, data: dict[str, Any], strict: bool = True
    ) -> tuple[bool, str]:
        """
        Validates a specific section of the CV data.
        Args:
            section: The CV section to validate (e.g., 'personal_info', 'education', etc.)
            data: The data for that section
            strict: If True, fails on any validation issue
        Returns:
            Tuple[bool, str]: (is_valid, detailed_message)
        """
        print(f"validate_cv section: {section} data: {data}")
        is_valid, message = await self.validate_section(section, data)
        print(f"{section} validation:", is_valid, message)
        return is_valid, message

    def _validate_format(self, field: str, value: Any, rule: str) -> bool:
        """Validate field format using regex rules. Handles non-string values gracefully."""
        if not isinstance(value, str):
            return False
        try:
            # Use fullmatch for stricter validation of the entire string
            return bool(re.fullmatch(rule, value))
        except re.error as e:
            logger.error(
                f"Regex error validating field '{field}' with rule '{rule}': {e}"
            )
            return False

    def _pre_validate(self, section: str, data: dict[str, Any]) -> str | None:
        """Perform preliminary validation checks."""
        if section not in self._validation_rules:
            # This should ideally not happen if __init__ syncs with PROMPTS
            logger.error(f"Attempted to pre-validate unknown section: {section}")
            return f"Configuration error: Unknown validation section '{section}'"

        # If data for the section is entirely missing (None or empty dict/list)
        # Check if the section itself is required
        rule = self._validation_rules[section]
        if not data and rule.section_required:
            return f"Missing required section: {section}"
        elif not data:
            return (
                None  # Section is optional and missing, that's okay for pre-validation
            )

        # If data is present but not a dictionary (e.g., for skills, education it might be list/str)
        # skip field-specific pre-validation. LLM will handle content.
        if not isinstance(data, dict):
            # Allow lists or strings for sections like education, skills, work_experience
            # Pre-validation on these structures is limited here, rely on LLM
            return None

        # --- Field-specific checks (only if data is a dictionary) ---
        errors = []

        # 1. Check required fields within the dictionary
        missing = [f for f in rule.required_fields if f not in data or not data.get(f)]
        if missing:
            errors.append(f"Missing required fields: {', '.join(missing)}")

        # 2. Check format rules for present fields
        format_errors = []
        for field, pattern in rule.format_rules.items():
            if data.get(field):  # Check only if field exists and has a value
                if not self._validate_format(field, data[field], pattern):
                    format_errors.append(f"Invalid format for field '{field}'")
            elif field in data and not data[field] and field in rule.required_fields:
                # Field exists but is empty, and it's required (already caught above, but be explicit)
                # This case is handled by the 'missing' check.
                pass

        if format_errors:
            errors.extend(format_errors)

        return "; ".join(errors) if errors else None

    async def validate_personal_info(self, data: dict[str, Any]) -> tuple[bool, str]:
        """
        Validates personal info fields individually.
        """
        print("Validating personal info fields...")
        # Field-specific validation rules
        name_pattern = r"^[A-Z][a-z]+(\s[A-Z][a-z]+)+$"
        current_field = data.get("current_field")
        if not current_field:
            return False, "Current field not found in data."
        is_valid = True
        message = ""
        print("current field:", current_field)
        # Validate name
        if current_field == "name":
            is_valid = self._validate_format("name", data["name"], name_pattern)
            message = (
                "" if is_valid else "Invalid name format - Use proper capitalization"
            )

        # Validate email
        if current_field == "email":
            is_valid = self._validate_format(
                "email",
                data["email"],
                self._validation_rules["personal_info"].format_rules["email"],
            )
            message = "" if is_valid else "Invalid email format"

        # Validate phone
        if current_field == "phone":
            is_valid = self._validate_format(
                "phone",
                data["phone"],
                self._validation_rules["personal_info"].format_rules["phone"],
            )
            message = "" if is_valid else "Invalid phone format - Include country code"

        return is_valid, message

    async def validate_section(self, section: str, data: Any) -> tuple[bool, str]:
        """
        Validates complete sections using AI model.
        """
        print("Current section being validated:", section)
        if section == "personal_info":
            # Handle personal info fields individually
            print("Validating personal info fields...")
            return await self.validate_personal_info(data.get("personal_info", {}))

        else:
            # Use existing validation for other sections
            result: tuple[bool, str] = await self.validate_input(section, data)
            return result

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential_jitter(initial=3, max=10),
        retry_error_callback=lambda retry_state: (
            False,
            f"Validation failed after {retry_state.attempt_number} attempts",
        ),
    )
    async def validate_input(
        self, section: str, data: dict[str, Any], strict: bool = True
    ) -> tuple[bool, str]:
        """
        Validates user input using AI model with enhanced error handling and validation.

        Args:
            section: The CV section being validated
            data: The data to validate
            strict: If True, fails on any validation issue

        Returns:
            Tuple[bool, str]: (is_valid, detailed_message)
        """
        logger.info(f"Starting validation for section: {section}")

        if section not in self._validation_rules:
            logger.error(f"Unknown section provided for validation: {section}")
            return False, f"Validation rule not found for section: {section}"

        # Perform preliminary validation
        pre_validation_error = self._pre_validate(section, data)
        if pre_validation_error:
            logger.warning(
                f"Pre-validation failed for {section}: {pre_validation_error}"
            )
            if strict:
                # Return pre-validation error directly if strict mode is on
                return False, f"Pre-validation Error: {pre_validation_error}"
            else:
                # Log the warning but proceed to LLM validation if not strict
                logger.info(
                    f"Strict mode off. Proceeding to LLM validation despite pre-validation warning for {section}."
                )

        # Handle cases where data might be None or empty, especially if not caught by pre-validation (e.g., optional section)
        if data is None or (isinstance(data, (dict | list | str)) and not data):
            rule = self._validation_rules[section]
            if rule.section_required:
                logger.warning(
                    f"Data for required section '{section}' is empty or None."
                )
                # Even if not strict, empty required data is usually invalid.
                # Let LLM confirm, or return invalid here? Let's let LLM judge content.
                # If pre-validation didn't catch it (e.g. data={}), let LLM see it.
                pass  # Proceed to LLM which should flag it based on prompt
            else:
                logger.info(
                    f"Data for optional section '{section}' is empty or None. Skipping LLM validation."
                )
                # Optional and empty is considered valid in terms of data structure.
                return True, "VALID: Optional section is empty."

        try:
            prompt = self._validation_rules[section].prompt_template + "\n" + str(data)

            logger.debug(
                f"Sending request to LLM for section {section}. Prompt starts with: {prompt[:50]}..."
            )

            response = await self.client.chat.completions.create(
                model=Config.OPENAI_MODEL,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a meticulous CV data validator. Analyze the provided data for a specific CV section based on the user's criteria. Respond ONLY in the specified 'VALID/INVALID: ... Issues: ... Suggestions: ...' format.",
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.2,  # Lower temperature for more deterministic validation output
                max_tokens=250,  # Adjust as needed based on expected feedback length
            )

            result = response.choices[0].message.content.strip()
            logger.debug(f"LLM raw response for {section}: {result}")

            # Parse structured response
            # Basic parsing of the expected format
            lines = result.split("\n")
            status_line = lines[0] if lines else "INVALID: No response"
            is_valid = status_line.upper().startswith("VALID")

            # Reconstruct the message for clarity, potentially improving formatting
            message_parts = [status_line]
            issues_started = False
            suggestions_started = False
            current_section = None

            for line in lines[1:]:
                line_upper = line.upper().strip()
                if line_upper.startswith("ISSUES:"):
                    # Add newline before Issues
                    message_parts.append("\n" + line)
                    issues_started = True
                    suggestions_started = False
                    current_section = "Issues"
                elif line_upper.startswith("SUGGESTIONS:"):
                    # Add newline before Suggestions
                    message_parts.append("\n" + line)
                    suggestions_started = True
                    issues_started = False
                    current_section = "Suggestions"
                elif (
                    issues_started or suggestions_started
                ) and line.strip().startswith(("-", "*", "•")):
                    # Add bullet points directly under their section
                    message_parts.append(line)
                elif issues_started or suggestions_started:
                    # Append multi-line text to the last bullet point or header if needed (simple approach)
                    # This might need refinement if LLM gives complex multi-line bullets
                    if message_parts[-1].strip().startswith(("-", "*", "•")):
                        message_parts[-1] += (
                            " " + line.strip()
                        )  # Append to previous bullet
                    else:
                        # Append as new line under header
                        message_parts.append(line)
                # Ignore lines that don't fit the structure
            print("current_section:", current_section)
            formatted_message = "\n".join(message_parts).strip()

            # If pre-validation found issues and strict=False, prepend them
            if pre_validation_error and not strict:
                formatted_message = f"Pre-validation Warning: {pre_validation_error}\n---\nLLM Validation:\n{formatted_message}"
                # In non-strict mode, final validity depends on LLM *unless* pre-validation error was critical
                # For simplicity now, let LLM result dominate if strict is False.
                # A more nuanced approach could combine findings.

            logger.info(
                f"LLM validation result for {section}: {'VALID' if is_valid else 'INVALID'}"
            )
            return is_valid, formatted_message

        except Exception as e:
            logger.error(f"Validation error: {e!s}", exc_info=True)
            return False, f"Validation failed due to an error: {e!s}"

    async def batch_validate(
        self, cv_data: dict[str, Any]
    ) -> dict[str, tuple[bool, str]]:
        """
        Validates multiple CV sections concurrently.

        Args:
            cv_data: A dictionary where keys are section names and values are the data for that section.

        Returns:
            A dictionary mapping section names to their validation result tuple (is_valid, message).
            Includes results even for sections with errors during validation.
        """
        tasks = {}
        results = {}

        for section, section_data in cv_data.items():
            if section in self._validation_rules:
                # Create a task for each section found in the rules
                tasks[section] = asyncio.create_task(
                    self.validate_input(
                        section, section_data, strict=True
                    )  # Defaulting to strict=True for batch
                )
            else:
                logger.warning(
                    f"Section '{section}' in input data has no defined validation rule. Skipping."
                )
                results[section] = (
                    True,
                    "SKIPPED: No validation rule defined for this section.",
                )  # Or False? Consider desired behaviour

        # Wait for all validation tasks to complete
        task_results = await asyncio.gather(*tasks.values(), return_exceptions=True)

        # Map results back to section names
        for i, section in enumerate(tasks.keys()):
            result = task_results[i]
            if isinstance(result, Exception):
                logger.error(
                    f"Exception during validation for section {section}: {result}"
                )
                results[section] = (
                    False,
                    f"ERROR: Validation failed due to exception: {result}",
                )
            elif isinstance(result, tuple) and len(result) == 2:
                # Store the (is_valid, message) tuple
                results[section] = result
                logger.info(
                    f"Batch validation result for {section}: {'Valid' if result[0] else 'Invalid'}"
                )
            else:
                # Should not happen with current retry logic, but handle defensively
                logger.error(
                    f"Unexpected result type for section {section} validation: {result}"
                )
                results[section] = (
                    False,
                    "ERROR: Unexpected validation result format.",
                )

        return results
