# Web Framework
from fastapi import FastAPI, WebSocket
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

# AI/Language Processing
from langgraph.graph import StateGraph, END
from langchain_openai import ChatOpenAI

# Data Models and Types
from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any

# PDF Generation
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
# PDF Generation
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# Utilities
import os
import json
import uuid
import redis
import uvicorn
from dotenv import load_dotenv

# Local imports
from .template import HTML

# Load environment variables
load_dotenv()
# --- PDF Font Setup for Arabic ---
# Ensure you have an Arabic font file (e.g., Amiri-Regular.ttf)
# Download from: https://fonts.google.com/specimen/Amiri
arabic_font_path = os.path.join(os.path.dirname(__file__), "Amiri-Regular.ttf") # Adjust path if needed
if os.path.exists(arabic_font_path):
    pdfmetrics.registerFont(TTFont('ArabicFont', arabic_font_path))
    ARABIC_FONT_REGISTERED = True
else:
    print(f"Warning: Arabic font not found at {arabic_font_path}. PDF Arabic text may not render correctly.")
    ARABIC_FONT_REGISTERED = False

# Initialize FastAPI app
app = FastAPI()

# Mount static directory for PDFs
if not os.path.exists("static"):
    os.makedirs("static")
app.mount("/static", StaticFiles(directory="static"), name="static")

# Initialize Redis client
redis_client = redis.Redis(host="localhost", port=6379, db=0, decode_responses=True)

# Initialize LLM
llm = ChatOpenAI(model="gpt-4o-mini", api_key=os.getenv("OPENAI_API_KEY"))

# Define the order of personal info fields
PERSONAL_INFO_FIELDS = ["name", "email", "phone", "address"]

# Define CVState with the new field tracker
class CVState(BaseModel):
    language: str = "ar"  # Default to Arabic
    # Use Field(default_factory=dict) for mutable defaults
    personal_info: Dict[str, str] = Field(default_factory=dict)
    education: List[Dict] = Field(default_factory=list)
    work_experience: List[Dict] = Field(default_factory=list)
    skills: List[str] = Field(default_factory=list)
    current_section: str = "personal_info"
    # New field to track which specific detail we are asking for
    current_field: Optional[str] = PERSONAL_INFO_FIELDS[0] # Start with 'name'
    user_input: Optional[str] = None # Holds the LATEST message from the user
    chatbot_response: Optional[str] = None # Holds the NEXT message for the user
    cv_output: Optional[str] = None
    is_complete: bool = False

# Prompts for different sections

PROMPTS: Dict[str, Dict[str, Any]] = {
    "ar": {
        "personal_info": { # Now a dictionary of fields
            "name": "ما هو اسمك الكامل؟",
            "email": "ما هو عنوان بريدك الإلكتروني؟",
            "phone": "ما هو رقم هاتفك؟",
            "address": "ما هو عنوانك؟"
        },
        "education": "الرجاء تقديم تفاصيل تعليمك (المؤسسة، الدرجة العلمية، سنوات الدراسة، مثال: 'جامعة الملك سعود، بكالوريوس علوم حاسب، 2018-2022'). أضف مدخلاً واحداً في كل مرة أو اكتب 'تم' للانتقال.",
        "work_experience": "الرجاء تقديم تفاصيل خبرتك المهنية (الشركة، المنصب، السنوات، المسؤوليات الرئيسية، مثال: 'شركة التقنية، مهندس برمجيات، 2022-2024، تطوير أنظمة'). أضف مدخلاً واحداً في كل مرة أو اكتب 'تم' للانتقال.",
        "skills": "الرجاء إدراج مهاراتك (مثال: بايثون، جافاسكريبت، إدارة المشاريع). أضف مهارة واحدة في كل مرة أو اكتب 'تم' للانتقال.",
        "finalize": "سيرتك الذاتية جاهزة للإنشاء. هل تريد مراجعة التفاصيل، إنشاء السيرة الذاتية، أو إجراء تغييرات؟ (اكتب 'مراجعة'، 'إنشاء'، أو 'تعديل')."
    },
    "en": {
        "personal_info": { # Now a dictionary of fields
            "name": "What is your full name?",
            "email": "What is your email address?",
            "phone": "What is your phone number?",
            "address": "What is your address?"
        },
        "education": "Please provide details of your education (institution, degree, years attended, e.g., 'MIT, BS Computer Science, 2018-2022'). Add one entry at a time or type 'done' to move on.",
        "work_experience": "Please provide details of your work experience (company, role, years, key responsibilities, e.g., 'Google, Software Engineer, 2022-2024, Developed backend systems'). Add one entry at a time or type 'done' to move on.",
        "skills": "Please list your skills (e.g., Python, JavaScript, Project Management). Add one skill at a time or type 'done' to move on.",
        "finalize": "Your CV is ready to be generated. Would you like to review the details, generate the CV, or make changes? (Type 'review', 'generate', or 'edit')."
    }
}


# Add language-specific keywords
KEYWORDS = {
    "ar": {
        "done": "تم",
        "review": "مراجعة",
        "generate": "إنشاء",
        "edit": "تعديل"
    },
    "en": {
        "done": "done",
        "review": "review",
        "generate": "generate",
        "edit": "edit"
    }
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

# Node to prompt the user
def prompt_user(state: CVState) -> Dict[str, str]:
    language = state.get("language", "ar")
    prompt = PROMPTS[language][state.current_section]
    return {"user_input": prompt}

def process_input(state: CVState) -> Dict[str, Any]:
    user_input = state.user_input
    current_section = state.current_section
    language = state.language
    updates = {}

    # Early return for None input
    # Ignore empty input more robustly
    if user_input is None or not user_input.strip():
        print("Warning: process_input called with empty user_input.")
        # Return minimal updates: clear input, maybe set a prompt request?
        # Let generate_prompt handle asking again.
        return {"user_input": None, "chatbot_response": None} # Clear input, let generate_prompt ask again

    # Define section handlers as a dictionary of functions
    section_handlers = {
        "personal_info": lambda: handle_personal_info(user_input,  state.personal_info,  state.current_field),
        "education": lambda: handle_list_section(user_input, state.education, "education", "skills", language),
        "work_experience": lambda: handle_list_section(user_input, state.work_experience, "work_experience", "finalize", language),
        "skills": lambda: handle_list_section(user_input, state.skills, "skills", "finalize", language),
        "finalize": lambda: handle_finalize(user_input, state, language)
    }

    # Get and execute the appropriate handler
    handler = section_handlers.get(current_section)
    if handler:
        try:
            # Call the handler function
            handler_updates = handler()
            updates.update(handler_updates)
        except Exception as e:
            print(f"Error executing handler for section '{current_section}': {e}")
            import traceback
            traceback.print_exc()
            # Provide feedback to the user about the error
            updates["chatbot_response"] = f"An error occurred processing your input for {current_section}. Please try again."
            # Optionally reset the section or state here if it's safer
            updates["current_section"] = current_section # Stay in the current section for retry
    else:
        # This case should ideally not be reached if current_section is always valid
        print(f"Error: No handler found for section '{current_section}'.")
        updates["chatbot_response"] = "An internal error occurred (unknown section). Please contact support."
        updates["current_section"] = "personal_info" # Attempt to reset to a known state
        updates["current_field"] = PERSONAL_INFO_FIELDS[0] # Reset field tracker

    # Ensure user_input is cleared after processing
    updates["user_input"] = None

    # Clear chatbot_response if not set by handlers
    if "chatbot_response" not in updates:
        updates["chatbot_response"] = None

    return updates


def handle_personal_info(user_input: str, current_personal_info: Dict[str, str], current_field: Optional[str]) -> Dict[str, Any]:
    """Handles storing one piece of personal info and determining the next step."""
    updates: Dict[str, Any] = {}

    if not current_field:
        # If current_field is somehow None while in personal_info, reset to start
        print("Warning: handle_personal_info called with current_field=None. Resetting.")
        updates["current_field"] = PERSONAL_INFO_FIELDS[0]
        updates["current_section"] = "personal_info" # Stay in this section
        # We didn't process the input, maybe ask again? Or just proceed? Let's proceed to ask the first field.
        return updates

    # Store the received input for the current field
    # Create a mutable copy to update
    updated_personal_info = current_personal_info.copy()
    updated_personal_info[current_field] = user_input.strip()
    updates["personal_info"] = updated_personal_info

    # Determine the next field
    try:
        current_index = PERSONAL_INFO_FIELDS.index(current_field)
        if current_index + 1 < len(PERSONAL_INFO_FIELDS):
            # Move to the next field within personal_info
            next_field = PERSONAL_INFO_FIELDS[current_index + 1]
            updates["current_field"] = next_field
            updates["current_section"] = "personal_info" # Stay in this section
        else:
            # Last field collected, move to the next section
            updates["current_section"] = "education" # Move to education
            updates["current_field"] = None # Clear field tracker
    except ValueError:
        # Should not happen if current_field is always from PERSONAL_INFO_FIELDS
        print(f"Error: current_field '{current_field}' not found in PERSONAL_INFO_FIELDS.")
        updates["current_section"] = "education" # Attempt to recover by moving on
        updates["current_field"] = None

    return updates


def handle_list_section(user_input: str, current_list: List, list_key: str, next_section: str, language: str) -> Dict[str, Any]:
    """Handles adding items to lists (education, experience, skills)."""
    input_strip = user_input.strip()
    input_lower = input_strip.lower()
    done_keyword = KEYWORDS[language]["done"].lower()

    if input_lower == done_keyword:
        # User is done with this section
        return {
            "current_section": next_section,
            "current_field": None # Ensure field tracker is clear when changing section
        }
    elif not input_strip:
         # User submitted empty input, maybe prompt again?
         # For now, just stay in the same section without adding anything.
         # We can add a specific chatbot_response here if needed.
         return {
              "current_section": list_key,
              "chatbot_response": "Please provide details or type 'done'." # Optional feedback
         }
    else:
        # Add the input to the list
        updated_list = list(current_list) # Create a mutable copy

        if list_key == "skills":
            updated_list.append(input_strip)
        else: # Education, Work Experience expect dicts
             updated_list.append({"details": input_strip})

        return {
            list_key: updated_list,
            "current_section": list_key, # Stay in the current section to add more
            "current_field": None # Field tracker not used here, ensure it's None
        }





def handle_finalize(user_input: str, state: CVState, language: str) -> Dict[str, Any]:
    """Handles user commands in the finalize step."""
    input_lower = user_input.strip().lower()
    kw = KEYWORDS[language] # Keywords for the current language

    if input_lower == kw["generate"].lower():
        # Trigger generation and mark as complete
        return handle_generate(state) # handle_generate handles setting is_complete etc.
    elif input_lower == kw["review"].lower():
        # Set section to 'review', generate_prompt will handle showing data
        return {"current_section": "review", "current_field": None}
    elif input_lower == kw["edit"].lower():
        # Go back to the beginning to edit
        return {
            "current_section": "personal_info",
            "current_field": PERSONAL_INFO_FIELDS[0], # Start editing from the first field
            # Decide if editing should clear data or allow modification (current: allows modification)
            # To clear: uncomment below
            # "personal_info": {},
            # "education": [],
            # "work_experience": [],
            # "skills": [],
            "is_complete": False, # Ensure not complete if editing
            "cv_output": None,    # Clear previous output
        }
    else:
        # Invalid command
        error_msg = {
            "ar": f"الرجاء كتابة '{kw['review']}'، '{kw['generate']}'، أو '{kw['edit']}'.",
            "en": f"Please type '{kw['review']}', '{kw['generate']}', or '{kw['edit']}'."
        }
        # Set chatbot_response directly to provide immediate feedback
        return {
            "chatbot_response": error_msg[language],
            "current_section": "finalize", # Stay in finalize section
            "current_field": None
        }


def handle_generate(state: CVState) -> Dict[str, Any]:
    """Generates the CV PDF and content, marks state as complete."""
    try:
        pdf_url = generate_cv_pdf(state)
        text_content = format_cv_text(state) # Generate text version too

        completion_message = {
            "ar": f"تم إنشاء سيرتك الذاتية بنجاح!\n\n--- النسخة النصية ---\n{text_content}\n------\n\nيمكنك تحميل النسخة PDF <a href='{pdf_url}' target='_blank' download>من هنا</a>.",
            "en": f"Your CV has been generated successfully!\n\n--- Text Version ---\n{text_content}\n------\n\nDownload the PDF version <a href='{pdf_url}' target='_blank' download>here</a>."
        }
        output = completion_message[state.language]
        is_complete = True
    except Exception as e:
         print(f"Error during CV generation: {e}")
         import traceback
         traceback.print_exc()
         error_message = {
            "ar": f"حدث خطأ أثناء إنشاء السيرة الذاتية: {e}",
            "en": f"An error occurred while generating the CV: {e}"
         }
         output = error_message[state.language]
         is_complete = False # Stay in finalize section if generation failed

    return {
        "cv_output": output, # Contains either success message + link or error message
        "is_complete": is_complete,
        "chatbot_response": None, # Final output is in cv_output or error message was set here
        "user_input": None,
        # Keep current_section as finalize unless complete? Or set to 'completed'?
        "current_section": "finalize" if not is_complete else "completed",
        "current_field": None
    }

# --- PDF Generation and Text Formatting Functions (Remain the same) ---

def format_cv_text(state: CVState) -> str:
    """Formats the CV data into a plain text string."""
    lang = state.language
    p_info = state.personal_info or {}
    edu = state.education or []
    work = state.work_experience or []
    skills = state.skills or []

    # Basic text formatting (can be enhanced)
    cv_lines = [
        p_info.get("name", "N/A"),
        f"{p_info.get('email', 'N/A')} | {p_info.get('phone', 'N/A')} | {p_info.get('address', 'N/A')}",
        "\n" + ("التعليم" if lang == "ar" else "Education"),
        "-" * 30,
        *[item.get("details", "") for item in edu],
        "\n" + ("الخبرة المهنية" if lang == "ar" else "Work Experience"),
        "-" * 30,
        *[item.get("details", "") for item in work],
        "\n" + ("المهارات" if lang == "ar" else "Skills"),
        "-" * 30,
        ", ".join(skills)
    ]
    return "\n".join(line for line in cv_lines if line) # Join non-empty lines

def generate_cv_pdf(state: CVState) -> str:
    """Generates a PDF CV and returns the download URL."""
    lang = state.language
    pdf_filename = f"cv_output_{uuid.uuid4().hex}.pdf"
    pdf_filepath = os.path.join(static_dir, pdf_filename)
    download_url = f"/{static_dir}/{pdf_filename}" # Relative URL for the browser

    c = canvas.Canvas(pdf_filepath, pagesize=letter)
    width, height = letter # Get page dimensions

    # Basic styling
    styles = getSampleStyleSheet()
    # Create copies to modify safely
    style_normal = styles['Normal'].clone('style_normal')
    style_heading = styles['h2'].clone('style_heading')
    style_normal.spaceAfter = 6
    style_heading.spaceAfter = 12

    # Use Arabic font if registered and language is Arabic
    if lang == "ar" and ARABIC_FONT_REGISTERED:
        style_normal.fontName = 'ArabicFont'
        style_heading.fontName = 'ArabicFont'
        # Right alignment for Arabic text paragraphs
        style_normal.alignment = 2 # TA_RIGHT
        style_heading.alignment = 2 # TA_RIGHT
        style_normal.rightIndent = 0 # Ensure no unexpected indent
        style_heading.rightIndent = 0
        style_normal.leftIndent = 20 # Add some left margin if right aligned
        style_heading.leftIndent = 20
    else:
         # Left alignment for English/Default
        style_normal.alignment = 0 # TA_LEFT
        style_heading.alignment = 0 # TA_LEFT
        style_normal.leftIndent = 0
        style_heading.leftIndent = 0
        style_normal.rightIndent = 0
        style_heading.rightIndent = 0


    # Content elements (using Paragraph for better text flow and potential styling)
    story = []
    margin = 50
    available_width = width - 2 * margin

    # Helper to add Paragraphs safely
    def add_paragraph(text, style):
        if text and text.strip():
             # Replace newlines in user input with <br/> for HTML-like line breaks in Paragraph
             formatted_text = text.strip().replace('\n', '<br/>')
             story.append(Paragraph(formatted_text, style))
        # else:
             # story.append(Spacer(1, style.fontSize * 0.5)) # Add small spacer instead of empty paragraph?

    p_info = state.personal_info or {}
    add_paragraph(p_info.get("name", ""), style_heading)
    # Combine contact info, handle potential Arabic phone numbers (display as is)
    contact_info = f"{p_info.get('email', '')} | {p_info.get('phone', '')} | {p_info.get('address', '')}"
    add_paragraph(contact_info, style_normal)
    story.append(Paragraph("<br/>", style_normal)) # Spacer

    add_paragraph("التعليم" if lang == "ar" else "Education", style_heading)
    for edu in state.education or []:
        add_paragraph(edu.get("details", ""), style_normal)
    story.append(Paragraph("<br/>", style_normal))

    add_paragraph("الخبرة المهنية" if lang == "ar" else "Work Experience", style_heading)
    for work in state.work_experience or []:
        add_paragraph(work.get("details", ""), style_normal)
    story.append(Paragraph("<br/>", style_normal))

    add_paragraph("المهارات" if lang == "ar" else "Skills", style_heading)
    add_paragraph(", ".join(state.skills or []), style_normal)

    # Build the PDF using SimpleDocTemplate for better page handling
    from reportlab.platypus import SimpleDocTemplate #, Spacer

    doc = SimpleDocTemplate(pdf_filepath, pagesize=letter,
                            leftMargin=margin,
                            rightMargin=margin,
                            topMargin=margin,
                            bottomMargin=margin)
    try:
        doc.build(story)
        print(f"PDF generated successfully: {pdf_filepath}")
    except Exception as pdf_err:
         print(f"Error building PDF document: {pdf_err}")
         raise pdf_err # Re-raise the exception to be caught by handle_generate

    return download_url

# Function to generate the CV
def generate_cv(state: CVState) -> str:
    cv_content = f"{state.personal_info['name']}\n"
    cv_content += f"{state.personal_info['email']} | {state.personal_info['phone']} | {state.personal_info['address']}\n\n"
    cv_content += "Education\n" + "-" * 30 + "\n"
    for edu in state.education:
        cv_content += f"{edu['details']}\n"
    cv_content += "\nWork Experience\n" + "-" * 30 + "\n"
    for work in state.work_experience:
        cv_content += f"{work['details']}\n"
    cv_content += "\nSkills\n" + "-" * 30 + "\n"
    cv_content += ", ".join(state.skills) + "\n"

    # Save as PDF in static directory
    pdf_filename = f"static/cv_output_{uuid.uuid4().hex}.pdf"
    c = canvas.Canvas(pdf_filename, pagesize=letter)
    y = 750
    for line in cv_content.split("\n"):
        c.drawString(50, y, line)
        y -= 15
    c.save()

    download_url = f"/{pdf_filename}"
    return cv_content + f"\nCV saved. Download it <a href='{download_url}' target='_blank'>here</a>."

# Define the LangGraph workflow
# Define the LangGraph workflow
workflow = StateGraph(CVState)

workflow.add_node("process_input", process_input)
workflow.add_node("generate_prompt", generate_prompt)

workflow.set_entry_point("process_input")

# After processing, always decide what prompt to generate next (unless complete)
workflow.add_conditional_edges(
    "process_input",
    # Function to decide the next step
    lambda state: END if state.is_complete else "generate_prompt",
    # Mapping: END goes to END, "generate_prompt" goes to the generate_prompt node
    {END: END, "generate_prompt": "generate_prompt"}
)

# After generating the prompt, the graph turn is over.
workflow.add_edge("generate_prompt", END)

graph = workflow.compile()

# Helper functions for Redis
def save_state(session_id: str, state: CVState):
    try:
        redis_client.setex(
            f"cv_session:{session_id}",
            3600,  # 1-hour TTL
            state.model_dump_json() # Use Pydantic's method for robust serialization
        )
    except redis.exceptions.ConnectionError as e:
         print(f"Redis Error (save_state): {e}. State for {session_id} not saved.")
    except Exception as e:
         print(f"Error saving state for {session_id}: {e}")


def load_state(session_id: str) -> Optional[CVState]:
    try:
        state_json = redis_client.get(f"cv_session:{session_id}")
        if state_json:
            try:
                return CVState.model_validate_json(state_json) # Use Pydantic's method
            except Exception as e:
                print(f"Error validating/loading state from Redis for {session_id}: {e}")
                # Optionally delete invalid state from Redis?
                # redis_client.delete(f"cv_session:{session_id}")
                return None # Treat invalid state as missing
        return None
    except redis.exceptions.ConnectionError as e:
         print(f"Redis Error (load_state): {e}. Cannot load state for {session_id}.")
         return None # Cannot load state if Redis is down
    except Exception as e:
         print(f"Error loading state for {session_id}: {e}")
         return None

# Serve the frontend
@app.get("/")
async def get():
    return HTMLResponse(HTML)


# WebSocket endpoint
@app.websocket("/ws/cv_builder")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    session_id = None
    state = None # Initialize state

    try:
        # Receive initial message with session ID
        data = await websocket.receive_json()
        session_id = data.get("session_id")
        language = data.get("language", "ar")
        if not session_id:
            await websocket.send_json({
                "sender": "Chatbot",
                "text": "خطأ: لم يتم تقديم معرف الجلسة." if language == "ar" else "Error: No session ID provided.",
                "language": language
            })
            await websocket.close()
            return
        print(f"\n[Session: {session_id}] Connection established. Language: {language}")
        # Load or initialize state
        state = load_state(session_id)
        if state:
            print(f"[Session: {session_id}] Loaded existing state. Current section: {state.current_section}, Field: {state.current_field}")
            # If loaded state is already complete, send final message and exit loop early
            if state.is_complete and state.cv_output:
                 await websocket.send_json({"sender": "Chatbot", "text": state.cv_output})
                 # Keep connection open but don't enter main loop? Or close?
                 # Let's close for simplicity after sending final msg.
                 await websocket.close()
                 return
            # Refresh language if provided in initial message? Usually no. Stick with saved language.
            # state.language = language # Decide if language override is desired on reconnect
            # Ensure chatbot_response is cleared if we are generating a fresh prompt
            state.chatbot_response = None
            state.user_input = None # Clear any stale input
        else:
            print(f"[Session: {session_id}] No existing state found. Initializing new state.")
            # Initialize new state, ensuring current_field is set for personal_info
            state = CVState(language=language, current_section="personal_info", current_field=PERSONAL_INFO_FIELDS[0])

        # === Run Graph for Initial Prompt ===
        # Invoke graph with the initial/loaded state (without user input yet)
        # The process_input node will do nothing (no user input),
        # then generate_prompt will create the first question.
        print(f"[Session: {session_id}] Running graph for initial prompt...")
        initial_state_dict = graph.invoke(state.dict(), config={"recursion_limit": 5}) # Limit depth for safety
        state = CVState(**initial_state_dict)
        save_state(session_id, state) # Save the state *after* getting the initial prompt
        
        
        # Send the initial/current prompt
        response_to_send = state.cv_output if state.is_complete else state.chatbot_response
        # Send the first prompt
        if state.chatbot_response:
            await websocket.send_json({"sender": "Chatbot", "text": state.chatbot_response})
            print(f"[Session: {session_id}] Sent initial prompt: {state.chatbot_response[:80]}...")
        else:
            print(f"[Session: {session_id}] Warning: No initial prompt generated by graph.")
            await websocket.send_json({"sender": "Chatbot", "text": "Welcome! Let's start building your CV."}) # Fallback
        
        
        # === Message Loop ===
        while not state.is_complete:
            data = await websocket.receive_json()
            received_session_id = data.get("session_id")
            user_input = data.get("text", "").strip()

            if received_session_id != session_id:
                await websocket.send_json({"sender": "Chatbot", "text": "Error: Session ID mismatch."})
                continue # Or close

            if not user_input:
                 # Re-send the last prompt if input is empty
                 if state.chatbot_response:
                    await websocket.send_json({"sender": "Chatbot", "text": f"Please provide a response. {state.chatbot_response}"})
                 else:
                    await websocket.send_json({"sender": "Chatbot", "text": "Please provide a response."})
                 continue

            print(f"\n[Session: {session_id}] Received input: {user_input}")

            # Load the latest state before processing
            current_state = load_state(session_id)
            if not current_state:
                 print(f"[Session: {session_id}] Error: Session expired or not found during loop.")
                 await websocket.send_json({"sender": "Chatbot", "text": "Error: Session expired or not found."})
                 break # Exit loop

            # Prepare state for the graph: add user input
            current_state.user_input = user_input
            
            current_state.chatbot_response = None # Clear previous response before graph run

            # Invoke the graph for one turn
            print(f"[Session: {session_id}] Invoking graph. Section: {current_state.current_section}, Field: {current_state.current_field}")
            result_state_dict = graph.invoke(current_state.dict(), config={"recursion_limit": 50})
            state = CVState(**result_state_dict) # Update local state variable

            print(f"[Session: {session_id}] Graph finished. Next section: {state.current_section}, Next field: {state.current_field}, Complete: {state.is_complete}")
            # print(f"[Session: {session_id}] Chatbot response: {state.chatbot_response}")
            # print(f"[Session: {session_id}] CV Output: {state.cv_output}")


            # Save the *new* state returned by the graph
            save_state(session_id, state)

            # Send the response generated by the graph
            response_to_send = state.cv_output if state.is_complete else state.chatbot_response
            if response_to_send:
                 await websocket.send_json({"sender": "Chatbot", "text": response_to_send})
                 # print(f"[Session: {session_id}] Sent response: {response_to_send[:80]}...")
            else:
                 # This might happen if is_complete=True but cv_output is somehow None, or an error occurred
                 print(f"[Session: {session_id}] Warning: No response generated by graph.")
                 if state.is_complete:
                      await websocket.send_json({"sender": "Chatbot", "text": "CV generation process finished."}) # Fallback completion message

        # === End of Conversation ===
        if state and state.is_complete:
            print(f"Session complete: {session_id}")
            # Optional: Clean up Redis immediately, or rely on TTL
            # redis_client.delete(f"cv_session:{session_id}")

        
    except Exception as e:
        print(f"WebSocket Error (Session: {session_id}): {e}")
        import traceback
        traceback.print_exc() # Print full traceback to server console for debugging
        try:
            await websocket.send_json({"sender": "Chatbot", "text": f"An server error occurred: {str(e)}"})
        except:
            pass # Ignore if websocket is already closed
    finally:
        await websocket.close()

def is_port_in_use(port: int) -> bool:
    import socket
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind(('127.0.0.1', port))
            s.close()
            return False
        except OSError:
            return True

def find_available_port(start_port: int = 8000, max_port: int = 9000) -> int:
    """Find an available port between start_port and max_port."""
    for port in range(start_port, max_port):
        if not is_port_in_use(port):
            return port
    raise RuntimeError(f"No available ports found between {start_port} and {max_port}")

if __name__ == "__main__":
    try:
        port = find_available_port()
        print(f"Starting server on port {port}")
        uvicorn.run(app, host="127.0.0.1", port=port)
    except Exception as e:
        print(f"Failed to start server: {e}")
        exit(1)