from langchain_core.runnables import RunnableConfig
from langchain_core.tools import BaseTool, tool


@tool
async def save_personal_info(
    personal_info: dict[str, str], config: RunnableConfig
) -> dict[str, str]:
    """Save personal information."""
    # Simulate saving to a database or file
    print(f"Saving personal info: {personal_info} in {config}")
    return {"status": "success", "message": "Personal info saved successfully."}


@tool
async def save_work_experience(
    work_experience: list[dict[str, str]], *, config: RunnableConfig
) -> dict[str, str]:
    """Save work experience."""
    # Simulate saving to a database or file
    print(f"Saving work experience: {work_experience} in {config}")
    return {"status": "success", "message": "Work experience saved successfully."}


@tool
async def save_education(
    education: list[dict[str, str]], *, config: RunnableConfig
) -> dict[str, str]:
    """Saves the education section of the resume."""

    print(f"Saving education: {education} in {config}")
    return {"status": "success", "message": "Education saved successfully."}


@tool
async def save_skills(skills: list[str], *, config: RunnableConfig) -> dict[str, str]:
    """Saves the skills section of the resume."""
    print(f"Saving skills: {skills} in {config}")
    return {"status": "success", "message": "Skills saved successfully."}


resume_tools: list[BaseTool] = [
    save_personal_info,
    save_work_experience,
    save_education,
    save_skills,
]
