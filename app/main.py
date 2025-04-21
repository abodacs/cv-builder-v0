# Web Framework
from fastapi import FastAPI, WebSocket
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

# AI/Language Processing
from langgraph.graph import StateGraph, END
from langchain_openai import ChatOpenAI

# Data Models and Types
from pydantic import BaseModel
from typing import Dict, List, Optional, Any

# PDF Generation
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

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

# Define CVState
class CVState(BaseModel):
    language: str = "ar"  # Default to Arabic
    personal_info: Optional[Dict] = None
    education: List[Dict] = []
    work_experience: List[Dict] = []
    skills: List[str] = []
    current_section: str = "personal_info"
    user_input: Optional[str] = None # This will hold the LATEST message from the user
    chatbot_response: Optional[str] = None # This will hold the NEXT message for the user
    cv_output: Optional[str] = None
    is_complete: bool = False

# Prompts for different sections

PROMPTS: Dict[str, Dict[str, str]] = {
    "ar": {
        "personal_info": "الرجاء تقديم معلوماتك الشخصية (الاسم، البريد الإلكتروني، رقم الهاتف، والعنوان، مفصولة بفواصل).",
        "education": "الرجاء تقديم تفاصيل تعليمك (المؤسسة، الدرجة العلمية، سنوات الدراسة، مثال: 'جامعة الملك سعود، بكالوريوس علوم حاسب، 2018-2022'). أضف مدخلاً واحداً في كل مرة أو اكتب 'تم' للانتقال.",
        "work_experience": "الرجاء تقديم تفاصيل خبرتك المهنية (الشركة، المنصب، السنوات، المسؤوليات الرئيسية، مثال: 'شركة التقنية، مهندس برمجيات، 2022-2024، تطوير أنظمة'). أضف مدخلاً واحداً في كل مرة أو اكتب 'تم' للانتقال.",
        "skills": "الرجاء إدراج مهاراتك (مثال: بايثون، جافاسكريبت، إدارة المشاريع). أضف مهارة واحدة في كل مرة أو اكتب 'تم' للانتقال.",
        "finalize": "سيرتك الذاتية جاهزة للإنشاء. هل تريد مراجعة التفاصيل، إنشاء السيرة الذاتية، أو إجراء تغييرات؟ (اكتب 'مراجعة'، 'إنشاء'، أو 'تعديل')."
    },
    "en": {
        "personal_info": "Please provide your personal information (name, email, phone number, and address, separated by commas).",
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
    # If process_input already set a specific response (e.g., error message), use it.
    if state.chatbot_response:
        return {"chatbot_response": state.chatbot_response}
    language = state.get("language", "ar")
    # Handle the special 'review' state
    if state.current_section == "review":
         # Reset section back to finalize after showing review
         return {
             "chatbot_response": "Reviewing details:\n" + json.dumps(state.model_dump(exclude={'user_input', 'chatbot_response', 'is_complete', 'cv_output', 'current_section'}), indent=2) + "\n\n" + PROMPTS[language]["finalize"],
             "current_section": "finalize"
         }

    # Otherwise, generate prompt based on the current section
    prompt = PROMPTS[language].get(state.current_section)
    if not prompt: # Should not happen if logic is correct, but safety check
        return {"chatbot_response": "An unexpected error occurred."}

    return {"chatbot_response": prompt}

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
    if user_input is None:
        return updates

    # Define section handlers as a dictionary of functions
    section_handlers = {
        "personal_info": lambda: handle_personal_info(user_input, language),
        "education": lambda: handle_list_section(user_input, state.education, "education", "skills", language),
        "work_experience": lambda: handle_list_section(user_input, state.work_experience, "work_experience", "finalize", language),
        "skills": lambda: handle_list_section(user_input, state.skills, "skills", "finalize", language),
        "finalize": lambda: handle_finalize(user_input, state, language)
    }

    # Get and execute the appropriate handler
    handler = section_handlers.get(current_section)
    if handler:
        updates.update(handler())

    # Clear chatbot_response if not set by handlers
    if "chatbot_response" not in updates:
        updates["chatbot_response"] = None

    return updates

def handle_personal_info(user_input: str, language: str) -> Dict[str, Any]:
    try:
        parts = [part.strip() for part in user_input.split(",")]
        if len(parts) < 4:
            error_msg = {
                "ar": "صيغة غير صحيحة. الرجاء تقديم الاسم والبريد الإلكتروني ورقم الهاتف والعنوان مفصولة بفواصل.",
                "en": "Invalid format. Please provide name, email, phone, and address separated by commas."
            }
            return {
                "chatbot_response": error_msg[language],
                "current_section": "personal_info"
            }
        
        return {
            "personal_info": {
                "name": parts[0],
                "email": parts[1],
                "phone": parts[2],
                "address": parts[3]
            },
            "current_section": "education"
        }
    except Exception:
        error_msg = {
            "ar": "صيغة غير صحيحة. الرجاء تقديم الاسم والبريد الإلكتروني ورقم الهاتف والعنوان مفصولة بفواصل.",
            "en": "Invalid format. Please provide name, email, phone, and address separated by commas."
        }
        return {
            "chatbot_response": error_msg[language],
            "current_section": "personal_info"
        }

def handle_list_section(user_input: str, current_list: List, current_section: str, next_section: str, language: str) -> Dict[str, Any]:
    if user_input.lower() == KEYWORDS[language]["done"]:
        return {"current_section": next_section}
    
    if isinstance(current_list, list):
        if current_section == "skills":
            return {
                "skills": current_list + [user_input],
                "current_section": current_section
            }
        else:
            return {
                current_section: current_list + [{"details": user_input}],
                "current_section": current_section
            }
    return {"current_section": current_section}

def handle_finalize(user_input: str, state: CVState, language: str) -> Dict[str, Any]:
    actions = {
        KEYWORDS[language]["generate"]: lambda: handle_generate(state),
        KEYWORDS[language]["review"]: lambda: {"current_section": "review"},
        KEYWORDS[language]["edit"]: lambda: {"current_section": "personal_info"}
    }

    handler = actions.get(user_input.lower())
    if not handler:
        error_msg = {
            "ar": "الرجاء كتابة 'مراجعة'، 'إنشاء'، أو 'تعديل'.",
            "en": "Please type 'review', 'generate', or 'edit'."
        }
        return {
            "chatbot_response": error_msg[language],
            "current_section": "finalize"
        }
    
    return handler()

def handle_generate(state: CVState) -> Dict[str, Any]:
    cv_content = generate_cv(state)
    return {
        "cv_output": cv_content,
        "is_complete": True
    }

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
    redis_client.setex(
        f"cv_session:{session_id}",
        3600,  # 1-hour TTL
        json.dumps(state.dict())
    )

def load_state(session_id: str) -> Optional[CVState]:
    state_json = redis_client.get(f"cv_session:{session_id}")
    if state_json:
        return CVState(**json.loads(state_json))
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

        # Load or initialize state
        state = load_state(session_id)
        print(f"state: {state}")
        if not state:
            state = CVState(language=language)
            # Manually set the initial prompt for the very first interaction
            state.chatbot_response = PROMPTS[language][state.current_section]
            save_state(session_id, state)
        elif not state.chatbot_response and not state.is_complete:
            # If state exists but has no pending response (e.g., server restarted), generate prompt
            print("State loaded, generating prompt for current section:", state.current_section)
            # We can call generate_prompt directly here or invoke a minimal graph
            prompt_state = generate_prompt(state)
            
            state = CVState(**{**state.dict(), **prompt_state}) # Update state with the prompt
            save_state(session_id, state)

        
        
        # Send the initial/current prompt
        response_to_send = state.cv_output if state.is_complete else state.chatbot_response
        if response_to_send:
             await websocket.send_json({"sender": "Chatbot", "text": response_to_send})
        else:
            # Should have a prompt unless something went wrong or CV is done silently
             print("Warning: No initial response to send.")
        
        
        # === Message Loop ===
        while not state.is_complete:
            data = await websocket.receive_json()
            received_session_id = data.get("session_id")
            user_input = data.get("text", "").strip()

            if received_session_id != session_id:
                await websocket.send_json({"sender": "Chatbot", "text": "Error: Session ID mismatch."})
                continue # Or close

            if not user_input:
                await websocket.send_json({"sender": "Chatbot", "text": "Please provide a response."})
                continue

            print(f"\n[Session: {session_id}] Received input: {user_input}")

            # Load the latest state before processing
            state = load_state(session_id)
            if not state:
                 await websocket.send_json({"sender": "Chatbot", "text": "Error: Session expired or not found."})
                 break # Exit loop

            # Prepare state for the graph: add user input
            current_state_dict = state.dict()
            current_state_dict["user_input"] = user_input
            input_state = CVState(**current_state_dict)

            # Invoke the graph for one turn (process input -> generate prompt)
            print(f"[Session: {session_id}] Invoking graph with state section: {input_state.current_section}")
            result_state_dict = graph.invoke(input_state, config={"recursion_limit": 50}) # Limit is fine now
            state = CVState(**result_state_dict) # Update local state variable

            print(f"[Session: {session_id}] Graph finished. Next section: {state.current_section}, Complete: {state.is_complete}")
            print(f"[Session: {session_id}] Chatbot response: {state.chatbot_response}")


            # Save the *new* state returned by the graph
            save_state(session_id, state)

            # Send the response generated by the graph
            response_to_send = state.cv_output if state.is_complete else state.chatbot_response
            if response_to_send:
                 await websocket.send_json({"sender": "Chatbot", "text": response_to_send})
            else:
                # This might happen if is_complete=True but cv_output is somehow None
                print(f"[Session: {session_id}] Warning: No response generated by graph.")
                if state.is_complete:
                     await websocket.send_json({"sender": "Chatbot", "text": "CV generation finished."})

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
            s.bind(('', port))
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
        uvicorn.run(app, host="0.0.0.0", port=port)
    except Exception as e:
        print(f"Failed to start server: {e}")
        exit(1)