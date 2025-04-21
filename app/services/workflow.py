from langgraph.graph import StateGraph, END
import json
from app.core.constants import PROMPTS, PERSONAL_INFO_FIELDS
from app.core.state import CVState
from app.handlers.personal_info import handle_personal_info
from app.handlers.education import handle_education
from app.handlers.experience import handle_experience
from app.handlers.skills import handle_skills
from app.handlers.finalize import handle_finalize
from typing import Dict, Any

def process_input(state: CVState) -> Dict[str, Any]:
    """Process user input based on current state."""
    if not state.user_input or not state.user_input.strip():
        return {"user_input": None, "chatbot_response": None}
    
    handlers = {
        "personal_info": lambda: handle_personal_info(state.user_input, state.personal_info, state.current_field),
        "education": lambda: handle_education(state.user_input, state.education, state.language),
        "work_experience": lambda: handle_experience(state.user_input, state.work_experience, state.language),
        "skills": lambda: handle_skills(state.user_input, state.skills, state.language),
        "finalize": lambda: handle_finalize(state.user_input, state, state.language)
    }
    
    handler = handlers.get(state.current_section)
    if not handler:
        return {
            "chatbot_response": "An error occurred. Please try again.",
            "current_section": "personal_info"
        }
    
    try:
        updates = handler()
        updates["user_input"] = None
        return updates
    except Exception as e:
        print(f"Error in {state.current_section} handler: {e}")
        return {
            "chatbot_response": "An error occurred. Please try again.",
            "current_section": state.current_section
        }


def generate_prompt(state: CVState) -> Dict[str, Any]:
    """Generates the next prompt based on the current state."""
    # If process_input already set a specific response (e.g., error message), use it.
    if state.chatbot_response:
        return {"chatbot_response": state.chatbot_response}
    if state.is_complete and state.cv_output:
         return {"chatbot_response": state.cv_output}
    language = state.language
    current_section = state.current_section
    updates = {}

    # Priority 2: Handle 'review' state
    if current_section == "review":
        # Format state data for review (excluding transient fields)
        review_data = state.model_dump(exclude={'user_input', 'chatbot_response', 'is_complete', 'cv_output', 'current_section', 'current_field', 'language'})
        review_text = json.dumps(review_data, indent=2, ensure_ascii=False) # ensure_ascii=False for Arabic
        # Reset section back to finalize after showing review
        updates = {
             "chatbot_response": f"Reviewing details:\n{review_text}\n\n{PROMPTS[language]['finalize']}",
             "current_section": "finalize",
             "current_field": None # Clear field tracker when moving away
         }

    # Priority 3: Handle 'personal_info' section (asking field by field)
    elif current_section == "personal_info":
        current_field = state.current_field
        if current_field and current_field in PROMPTS[language]["personal_info"]:
            prompt = PROMPTS[language]["personal_info"][current_field]
            updates = {"chatbot_response": prompt}
        else:
            # Should not happen if logic is correct, but safety net
            print(f"Warning: Invalid or missing current_field '{current_field}' in personal_info section.")
            # Attempt to recover or give a generic message
            first_field = PERSONAL_INFO_FIELDS[0]
            prompt = PROMPTS[language]["personal_info"].get(first_field, "Please provide your personal details.")
            updates = {"chatbot_response": prompt, "current_field": first_field}

    # Priority 4: Handle other sections (education, work, skills, finalize)
    else:
        prompt = PROMPTS[language].get(current_section)
        if prompt:
            updates = {"chatbot_response": prompt}
        else: # Should not happen if logic is correct
            print(f"Warning: Could not find prompt for section '{current_section}'.")
            updates = {"chatbot_response": "An unexpected error occurred regarding the next step."}

    # Ensure transient fields are reset if not explicitly set
    if "user_input" not in updates:
        updates["user_input"] = None # Clear user input after processing

    return updates


def create_workflow() -> StateGraph:
    """Create and configure the workflow graph."""
    workflow = StateGraph(CVState)
    
    workflow.add_node("process_input", process_input)
    workflow.add_node("generate_prompt", generate_prompt)
    
    workflow.set_entry_point("process_input")
    
    workflow.add_conditional_edges(
        "process_input",
        lambda state: END if state.is_complete else "generate_prompt",
        {END: END, "generate_prompt": "generate_prompt"}
    )
    
    workflow.add_edge("generate_prompt", END)
    
    return workflow.compile()

# Initialize workflow
graph = create_workflow()
