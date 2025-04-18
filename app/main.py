from fastapi import FastAPI, WebSocket
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from langgraph.graph import StateGraph, END
from langchain_openai import ChatOpenAI
from pydantic import BaseModel
from typing import Dict, List, Optional, Any
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import os
from dotenv import load_dotenv
load_dotenv()
import json
import uuid
import redis
import uvicorn

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
PROMPTS = {
    "personal_info": "Please provide your personal information (name, email, phone number, and address, separated by commas).",
    "education": "Please provide details of your education (institution, degree, years attended, e.g., 'MIT, BS Computer Science, 2018-2022'). Add one entry at a time or type 'done' to move on.",
    "work_experience": "Please provide details of your work experience (company, role, years, key responsibilities, e.g., 'Google, Software Engineer, 2022-2024, Developed backend systems'). Add one entry at a time or type 'done' to move on.",
    "skills": "Please list your skills (e.g., Python, JavaScript, Project Management). Add one skill at a time or type 'done' to move on.",
    "finalize": "Your CV is ready to be generated. Would you like to review the details, generate the CV, or make changes? (Type 'review', 'generate', or 'edit')."
}

def generate_prompt(state: CVState) -> Dict[str, Any]:
    # If process_input already set a specific response (e.g., error message), use it.
    if state.chatbot_response:
        return {"chatbot_response": state.chatbot_response}

    # Handle the special 'review' state
    if state.current_section == "review":
         # Reset section back to finalize after showing review
         return {
             "chatbot_response": "Reviewing details:\n" + json.dumps(state.model_dump(exclude={'user_input', 'chatbot_response', 'is_complete', 'cv_output', 'current_section'}), indent=2) + "\n\n" + PROMPTS["finalize"],
             "current_section": "finalize"
         }

    # Otherwise, generate prompt based on the current section
    prompt = PROMPTS.get(state.current_section)
    if not prompt: # Should not happen if logic is correct, but safety check
        return {"chatbot_response": "An unexpected error occurred."}

    return {"chatbot_response": prompt}

# Node to prompt the user
def prompt_user(state: CVState) -> Dict[str, Any]:
    prompt = PROMPTS[state.current_section]
    return {"user_input": prompt}

def process_input(state: CVState) -> Dict[str, Any]:
    user_input = state.user_input
    current_section = state.current_section
    updates = {}

    # Handle initial state or cases where user_input might be None/empty inappropriately
    if user_input is None:
         # If it's the very start, let the next step generate the initial prompt
         # Otherwise, maybe ask to repeat? For now, let's assume the flow handles it.
         pass # Let generate_prompt handle the prompt based on current_section
    elif current_section == "personal_info":
        try:
            parts = [part.strip() for part in user_input.split(",")]
            if len(parts) < 4:
                # Keep current section, let generate_prompt send an error message
                updates["chatbot_response"] = "Invalid format. Please provide name, email, phone, and address separated by commas."
                # Don't advance the section
                updates["current_section"] = "personal_info"
            else:
                updates["personal_info"] = {
                    "name": parts[0],
                    "email": parts[1],
                    "phone": parts[2],
                    "address": parts[3]
                }
                updates["current_section"] = "education" # Advance section
        except Exception as e:
            updates["chatbot_response"] = "Invalid format. Please provide name, email, phone, and address separated by commas."
            updates["current_section"] = "personal_info" # Don't advance

    elif current_section in ["education", "work_experience"]:
        if user_input.lower() == "done":
            # Advance section
            updates["current_section"] = "skills" if current_section == "education" else "finalize"
        else:
            # Add the entry
            entry = {"details": user_input}
            current_list = getattr(state, current_section, []) # Use getattr with default
            updates[current_section] = current_list + [entry]
            # Stay in the same section to allow adding more
            updates["current_section"] = current_section

    elif current_section == "skills":
        if user_input.lower() == "done":
            updates["current_section"] = "finalize" # Advance section
        else:
            # Add the skill
            updates["skills"] = state.skills + [user_input]
             # Stay in the same section to allow adding more
            updates["current_section"] = current_section

    elif current_section == "finalize":
        if user_input.lower() == "generate":
            cv_content = generate_cv(state) # generate_cv needs the current state *before* updates
            # We need to merge the potential updates with the full state to generate CV
            temp_state_dict = state.dict()
            temp_state_dict.update(updates) # Apply updates for generation if needed
            cv_content = generate_cv(CVState(**temp_state_dict))
            updates["cv_output"] = cv_content
            updates["is_complete"] = True
            # No next section needed
        elif user_input.lower() == "review":
            # Let generate_prompt handle showing the review
            updates["current_section"] = "review" # Use a temporary section for review
        elif user_input.lower() == "edit":
            updates["current_section"] = "personal_info" # Go back to start
        else:
            # Ask again
            updates["chatbot_response"] = "Please type 'review', 'generate', or 'edit'."
            updates["current_section"] = "finalize" # Stay here

    # If chatbot_response wasn't set by error handling, clear it
    if "chatbot_response" not in updates:
         updates["chatbot_response"] = None

    # Return only the changes
    return updates


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

# HTML for the frontend
html = """
<!DOCTYPE html>
<html>
<head>
    <title>CV Builder Chatbot</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        #chatbox { border: 1px solid #ccc; height: 400px; overflow-y: scroll; padding: 10px; margin-bottom: 10px; }
        #input { width: 80%; padding: 5px; }
        button { padding: 5px 10px; }
    </style>
</head>
<body>
    <h1>CV Builder Chatbot</h1>
    <div id="chatbox"></div>
    <input id="input" type="text" placeholder="Type your response here..." />
    <button onclick="sendMessage()">Send</button>

    <script>
        let sessionId = localStorage.getItem("cv_session_id");
        if (!sessionId) {
            sessionId = crypto.randomUUID();
            localStorage.setItem("cv_session_id", sessionId);
        }

        const ws = new WebSocket("ws://" + window.location.host + "/ws/cv_builder");
        const chatbox = document.getElementById("chatbox");
        const input = document.getElementById("input");

        ws.onopen = function() {
            // Send session ID on connect
            ws.send(JSON.stringify({ session_id: sessionId, text: "" }));
        };

        ws.onmessage = function(event) {
            const message = JSON.parse(event.data);
            const p = document.createElement("p");
            p.innerHTML = message.sender + ": " + message.text;
            chatbox.appendChild(p);
            chatbox.scrollTop = chatbox.scrollHeight;
        };

        function sendMessage() {
            const text = input.value.trim();
            if (text) {
                ws.send(JSON.stringify({ session_id: sessionId, text: text }));
                const p = document.createElement("p");
                p.innerHTML = "You: " + text;
                chatbox.appendChild(p);
                chatbox.scrollTop = chatbox.scrollHeight;
                input.value = "";
            }
        }

        input.addEventListener("keypress", function(event) {
            if (event.key === "Enter") {
                sendMessage();
            }
        });
    </script>
</body>
</html>
"""

# Serve the frontend
@app.get("/")
async def get():
    return HTMLResponse(html)

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
        if not session_id:
            await websocket.send_json({"sender": "Chatbot", "text": "Error: No session ID provided."})
            await websocket.close()
            return

        # Load or initialize state
        state = load_state(session_id)
        print(f"state: {state}")
        if not state:
            state = CVState()
            # Manually set the initial prompt for the very first interaction
            state.chatbot_response = PROMPTS[state.current_section]
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

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)