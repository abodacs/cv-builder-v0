from typing import Any

from app.core.constants import KEYWORDS, PERSONAL_INFO_FIELDS
from app.core.state import CVState
from app.services.pdf import format_cv_text, generate_cv_pdf


def handle_finalize(
    user_input: str | None, state: CVState, language: str
) -> dict[str, Any]:
    input_lower = (user_input or "").strip().lower()
    kw = KEYWORDS[language]

    if input_lower == kw["generate"].lower():
        return handle_generate(state)
    elif input_lower == kw["review"].lower():
        return {"current_section": "review", "current_field": None}
    elif input_lower == kw["edit"].lower():
        return {
            "current_section": "personal_info",
            "current_field": PERSONAL_INFO_FIELDS[0],
            "is_complete": False,
            "cv_output": None,
        }
    else:
        error_msg = {
            "ar": f"الرجاء كتابة '{kw['review']}'، '{kw['generate']}'، أو '{kw['edit']}'.",
            "en": f"Please type '{kw['review']}', '{kw['generate']}', or '{kw['edit']}'.",
        }
        return {
            "chatbot_response": error_msg[language],
            "current_section": "finalize",
            "current_field": None,
        }


def handle_generate(state: CVState) -> dict[str, Any]:
    try:
        pdf_url = generate_cv_pdf(state)
        text_content = format_cv_text(state)

        completion_message = {
            "ar": f"تم إنشاء سيرتك الذاتية بنجاح!\n\n{text_content}\n\nيمكنك تحميل النسخة PDF <a href='{pdf_url}' target='_blank' download>من هنا</a>.",
            "en": f"Your CV has been generated successfully!\n\n{text_content}\n\nDownload the PDF version <a href='{pdf_url}' target='_blank' download>here</a>.",
        }

        return {
            "cv_output": completion_message[state.language],
            "is_complete": True,
            "chatbot_response": None,
            "user_input": None,
            "current_section": "completed",
            "current_field": None,
        }
    except Exception as e:
        error_message = {
            "ar": f"حدث خطأ أثناء إنشاء السيرة الذاتية: {e}",
            "en": f"An error occurred while generating the CV: {e}",
        }
        return {
            "cv_output": error_message[state.language],
            "is_complete": False,
            "current_section": "finalize",
            "current_field": None,
        }
