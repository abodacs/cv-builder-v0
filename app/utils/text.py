from app.core.state import CVState


def format_cv_text(state: CVState) -> str:
    """Format CV data into human-readable text."""
    lang = state.language
    sections = {
        "header": _format_header(state.personal_info, lang),
        "education": _format_section(
            state.education, "التعليم" if lang == "ar" else "Education"
        ),
        "experience": _format_section(
            state.work_experience,
            "الخبرة المهنية" if lang == "ar" else "Work Experience",
        ),
        "skills": _format_skills(
            state.skills, "المهارات" if lang == "ar" else "Skills"
        ),
    }

    return "\n\n".join(sections.values())


def _format_header(info: dict[str, str], lang: str) -> str:
    """Format personal information section."""
    name = info.get("name", "")
    contact = " | ".join(
        filter(
            None,
            [info.get("email", ""), info.get("phone", ""), info.get("address", "")],
        )
    )
    return f"{name}\n{contact}"


def _format_section(items: list[dict], title: str) -> str:
    """Format a section with its items."""
    if not items:
        return f"{title}\n" + "-" * 30
    return f"{title}\n" + "-" * 30 + "\n" + "\n".join(item["details"] for item in items)


def _format_skills(skills: list[str], title: str) -> str:
    """Format skills section."""
    return f"{title}\n" + "-" * 30 + "\n" + ", ".join(skills)
