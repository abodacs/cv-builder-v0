# HTML for the frontend
CSS_STYLES = """
<style>
==== Global Styles & Variables ==== */
:root {
    --user-msg-bg: #007bff; /* Blue */
    --bot-msg-bg: #e9e9eb;  /* Light Gray */
    --text-light: #ffffff;
    --text-dark: #1c1c1e;
    --border-color: #ccc;
    --input-bg: #f0f0f0;
    --container-bg: #ffffff;
    --body-bg: #f4f4f8;
    --spacing: 10px;
    --bubble-radius: 18px;
    --bubble-tail-radius: 5px;
}

*, *::before, *::after {
  box-sizing: border-box; /* Better sizing calculations */
}

body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
    margin: 0; /* Remove default body margin */
    padding: var(--spacing); /* Use logical padding once, body fills viewport */
    background-color: var(--body-bg);
    display: flex;
    justify-content: center;
    align-items: flex-start;
    min-height: 100vh;
}

input {
  field-sizing: content;
}

/* ==== Chat Container ==== */
.chat-container {
    background-color: var(--container-bg);
    border-radius: 8px;
    box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
    overflow: hidden;
    display: flex;
    flex-direction: column;
    max-width: 600px;
    width: 100%;
    height: 85vh;
    margin: var(--spacing);
}

h1 {
    font-size: 1.2em;
    text-align: center;
    /* Logical padding: block (top/bottom), inline (start/end) */
    padding-block: calc(var(--spacing) * 1.5);
    padding-inline: var(--spacing);
    margin: 0;
    background-color: #f8f9fa;
    border-block-end: 1px solid var(--border-color); /* Logical border */
}

.language-selector {
    padding: var(--spacing);
    text-align: center;
    background-color: #f8f9fa;
    font-size: 0.9em;
}

.language-selector select {
    padding-block: 3px;
    padding-inline: 5px;
    margin-inline-start: 5px; /* Logical margin */
}


/* ==== Chatbox & Messages ==== */
#chatbox {
    flex-grow: 1;
    overflow-y: auto;
    padding: var(--spacing);
    scroll-behavior: smooth;
    background-color: var(--container-bg);
}

.message {
    /* Logical padding */
    padding-block: var(--spacing);
    padding-inline: calc(var(--spacing) * 1.5);
    border-radius: var(--bubble-radius); /* Base radius for all corners */
    margin-block-end: var(--spacing); /* Logical margin */
    max-width: 75%;
    word-wrap: break-word;
    line-height: 1.4;
    position: relative;
    clear: both; /* Ensure messages don't overlap weirdly if floats were used (though we use margins here) */
}

.message .sender {
    font-weight: bold;
    display: block;
    font-size: 0.8em;
    margin-block-end: 3px; /* Logical margin */
    opacity: 0.8;
    text-align: start; /* Align sender based on writing direction */
}
.message .timestamp {
    font-size: 0.7em;
    opacity: 0; /* Hidden initially */
    transition: opacity 0.2s ease;
    position: absolute; /* Position it nicely */
    bottom: 2px;
    /* Adjust start/end based on user/bot */
}

.message:hover .timestamp {
    opacity: 0.6; /* Show on hover */
}

/* User Messages - Align to the END of the inline direction */
.message.message-user {
    background-color: var(--user-msg-bg);
    color: var(--text-light);
    margin-inline-start: auto; /* Push to the end */
    margin-inline-end: 0;     /* Anchor to the end */
    /* Bubble tail on the logical 'end-end' corner (bottom-right in LTR, bottom-left in RTL) */
    border-end-end-radius: var(--bubble-tail-radius);
    direction: ltr;
    text-align: start;
}

/* Bot Messages - Align to the START of the inline direction */
.message.message-bot {
    background-color: var(--bot-msg-bg);
    color: var(--text-dark);
    margin-inline-end: auto;   /* Push to the start */
    margin-inline-start: 0;    /* Anchor to the start */
    /* Bubble tail on the logical 'end-start' corner (bottom-left in LTR, bottom-right in RTL) */
    border-end-start-radius: var(--bubble-tail-radius);
    direction: rtl;
}

.message.message-error {
    background-color: #f8d7da; /* Light red */
    color: #721c24; /* Dark red */
    border: 1px solid #f5c6cb;
    /* Align center or like bot messages */
    margin-inline: auto; /* Center it */
    max-width: 90%;
}


/* ==== Input Area ==== */
.input-area {
    display: flex;
    padding: var(--spacing);
    border-block-start: 1px solid var(--border-color); /* Logical border */
    background-color: #f8f9fa;
    gap: var(--spacing); /* Use gap for spacing between flex items */
}

.input-area button:disabled {
    background-color: #cccccc;
    cursor: not-allowed;
    opacity: 0.7;
}

.new-message-indicator {
    position: absolute;
    bottom: calc(var(--spacing) * 2 + 50px); /* Above input area */
    left: 50%;
    transform: translateX(-50%);
    background-color: var(--user-msg-bg);
    color: var(--text-light);
    padding: 5px 10px;
    border-radius: 15px;
    cursor: pointer;
    opacity: 0; /* Hidden by default */
    transition: opacity 0.3s ease;
    z-index: 10;
}
.new-message-indicator.visible {
    opacity: 1;
}

.input-area button:active {
    background-color: #004085; /* Even darker when clicked */
    transform: scale(0.98); /* Optional subtle press effect */
}

#input {
    flex-grow: 1;
    /* Logical padding */
    padding-block: calc(var(--spacing) * 0.8);
    padding-inline: var(--spacing);
    border: 1px solid var(--border-color);
    border-radius: var(--bubble-radius); /* Match bubble radius */
    background-color: var(--container-bg);
    font-size: 1em;
    line-height: 1.3;
    outline: none;
    /* No margin needed here now, using 'gap' in parent */
}
#input:focus {
    border-color: var(--user-msg-bg);
    box-shadow: 0 0 0 2px rgba(0, 123, 255, 0.2);
}

.input-area button {
    /* Logical padding */
    padding-block: calc(var(--spacing) * 0.8);
    padding-inline: calc(var(--spacing) * 1.5);
    background-color: var(--user-msg-bg);
    color: var(--text-light);
    border: none;
    border-radius: var(--bubble-radius); /* Match bubble radius */
    cursor: pointer;
    font-size: 1em;
    transition: background-color 0.2s ease;
    white-space: nowrap;
}

.input-area button:hover {
    background-color: #0056b3;
}
.input-area button:active {
    background-color: #004085;
}

.typing-indicator {
    padding: 5px var(--spacing);
    margin-inline-start: var(--spacing); /* Align like bot message */
    margin-block-end: var(--spacing);
    display: inline-block; /* Or block */
    /* Style with animated dots */
}
.typing-indicator span { /* Animated dots */
   /* Animation CSS */
}

</style>
"""
SCRTIPT = """
 <script>
    let sessionId = localStorage.getItem("cv_session_id");
    let currentLanguage = localStorage.getItem("cv_language") || "ar"; // Default to Arabic
    const chatbox = document.getElementById("chatbox");
    const input = document.getElementById("input");
    const languageSelect = document.getElementById("language");
    const sendButton = document.querySelector(".input-area button"); // Target button specifically

    // --- Initialization ---
    if (!sessionId) {
        sessionId = window.crypto.randomUUID();
        localStorage.setItem("cv_session_id", sessionId);
    }

    // Set initial language and direction
    languageSelect.value = currentLanguage;
    updateUIDirection(currentLanguage);

    // --- WebSocket Connection ---
    let ws = null;
    let reconnectAttempts = 0;
    const MAX_RECONNECT_ATTEMPTS = 5;

    function connectWebSocket() {
        if (ws !== null) {
            ws.close();
        }

        // Check WebSocket health before connecting
        fetch('/ws/health')
            .then(response => response.json())
            .then(() => {
                initializeWebSocket();
            })
            .catch(error => {
                console.error('WebSocket health check failed:', error);
                scheduleReconnect();
            });
    }

    function initializeWebSocket() {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws/cv_builder`;

        ws = new WebSocket(wsUrl);

        ws.onopen = () => {
            console.log('WebSocket connected successfully');
            reconnectAttempts = 0;
            ws.send(JSON.stringify({
                session_id: sessionId,
                language: document.getElementById('language').value
            }));
        };

        ws.onclose = (event) => {
            console.log('WebSocket closed:', event.code, event.reason);
            scheduleReconnect();
        };

        ws.onerror = (error) => {
            console.error('WebSocket error:', error);
        };

        ws.onmessage = function(event) {
            try {
                const message = JSON.parse(event.data);
                // Assuming the server sends back messages with 'sender' ('bot' or maybe 'system') and 'text'
                // And potentially 'language' if the bot's response language differs
                const senderType = message.sender && message.sender.toLowerCase() === 'chatbot' ? 'bot' : 'system'; // Default to system if unknown
                const messageLang = message.language || currentLanguage; // Use message lang or current UI lang

                addMessage(message.text, senderType, messageLang);

            } catch (e) {
                console.error("Failed to parse message or process:", e);
                addSystemMessage("Received an invalid message from the server.");
            }
        };
    }

    function scheduleReconnect() {
        if (reconnectAttempts < MAX_RECONNECT_ATTEMPTS) {
            reconnectAttempts++;
            const delay = Math.min(1000 * Math.pow(2, reconnectAttempts), 10000);
            console.log(`Reconnecting in ${delay}ms (attempt ${reconnectAttempts})`);
            setTimeout(connectWebSocket, delay);
        } else {
            console.error('Max reconnection attempts reached');
            alert('Failed to connect to the server. Please refresh the page.');
        }
    }

    // Initialize WebSocket connection
    connectWebSocket();

    // --- UI Functions ---

    function updateUIDirection(lang) {
        const isRtl = lang === "ar";
        document.documentElement.dir = isRtl ? "rtl" : "ltr";
        // No need for body.dir if html.dir is set
        input.placeholder = isRtl ? "اكتب ردك هنا..." : "Type your response here...";
        sendButton.textContent = isRtl ? "إرسال" : "Send";
        // Update language selector label if needed (assuming it might change)
        // document.querySelector(".language-selector label").textContent = isRtl ? "اللغة:" : "Language:";
    }

    function changeLanguage() {
        const newLang = languageSelect.value;
        if (newLang !== currentLanguage) {
            currentLanguage = newLang;
            localStorage.setItem("cv_language", newLang);
            updateUIDirection(newLang);

            // Clear chatbox on language change? Optional, depends on desired UX.
            // chatbox.innerHTML = '';

            // Notify server about language change if the backend needs to adjust
            if (ws.readyState === WebSocket.OPEN) {
                ws.send(JSON.stringify({
                    session_id: sessionId,
                    text: "", // No user text, just a command
                    language: newLang,
                    change_language: true // Specific flag for language change
                }));
                // Maybe add a system message?
                // addSystemMessage(newLang === 'ar' ? "تم تغيير اللغة إلى العربية." : "Language changed to English.");
            } else {
                console.warn("WebSocket not open. Cannot notify server of language change yet.");
                // Optionally queue the change or handle on next successful open/message
            }
        }
    }

    function addMessage(text, senderType, lang) {
        // senderType should be 'user' or 'bot' or 'system'
        const messageDiv = document.createElement("div");
        messageDiv.classList.add("message");
        messageDiv.classList.add(`message-${senderType}`); // e.g., message-user, message-bot

        // Handle LTR text within the message bubble if necessary
        // The CSS primarily handles bubble alignment based on sender and overall direction.
        // This class ensures text *inside* the bubble flows correctly if its language
        // differs from the main UI direction (e.g., English message in Arabic UI).
        if (lang === "en") {
            messageDiv.classList.add("ltr");
        }
        // No need for an explicit 'rtl' class if the default direction is handled by CSS `inherit` and `text-align: start`

        // Add sender label (optional, can be removed for cleaner look)
        const senderSpan = document.createElement("span");
        senderSpan.classList.add("sender");
        if (senderType === 'user') {
            senderSpan.textContent = (currentLanguage === "ar" ? "أنت" : "You");
        } else if (senderType === 'bot') {
            senderSpan.textContent = (currentLanguage === "ar" ? "المساعد" : "Assistant"); // Or Bot, CV Builder etc.
        } else {
            senderSpan.textContent = (currentLanguage === "ar" ? "النظام" : "System");
        }
        messageDiv.appendChild(senderSpan);

        // Add message text (use textContent for security)
        const textNode = document.createElement('span'); // Wrap text for potential styling
        textNode.textContent = text;
        messageDiv.appendChild(textNode);


        chatbox.appendChild(messageDiv);

        // Scroll to bottom
        scrollToBottom();
    }

    // Helper for system messages (errors, info)
    function addSystemMessage(text) {
        const messageDiv = document.createElement("div");
        messageDiv.classList.add("message", "message-system"); // Style system messages differently if desired
        messageDiv.style.textAlign = 'center'; // Center system messages
        messageDiv.style.fontSize = '0.85em';
        messageDiv.style.color = '#6c757d'; // Muted color
        messageDiv.style.maxWidth = '90%';
        messageDiv.style.margin = '10px auto'; // Center block
        messageDiv.textContent = text;
        chatbox.appendChild(messageDiv);
        scrollToBottom();
    }

    function sendMessage() {
        const text = input.value.trim();
        if (text && ws.readyState === WebSocket.OPEN) {
            // Add user message immediately to UI
            addMessage(text, 'user', currentLanguage);

            // Send message to server
            ws.send(JSON.stringify({
                session_id: sessionId,
                text: text,
                language: currentLanguage
            }));

            // Clear input field
            input.value = "";
            input.focus(); // Keep focus on input
        } else if (!text) {
            // Maybe provide feedback if input is empty? (e.g., shake input)
            console.log("Input is empty.");
        } else {
            console.error("WebSocket is not open. ReadyState:", ws.readyState);
            addSystemMessage("Cannot send message: Connection not active.");
        }
    }

    function scrollToBottom() {
        // Use timeout to ensure the DOM has updated before scrolling
        setTimeout(() => {
            chatbox.scrollTop = chatbox.scrollHeight;
        }, 0);
    }

    // --- Event Listeners ---
    input.addEventListener("keypress", function(event) {
        // Send message on Enter key press (but not Shift+Enter for multi-line, if needed)
        if (event.key === "Enter" && !event.shiftKey) {
            event.preventDefault(); // Prevent default Enter behavior (like line break)
            sendMessage();
        }
    });

    // Initial focus on input field
    input.focus();
 </script>
"""
HTML = f"""
<!DOCTYPE html>
<html dir="rtl">
<head>
    <title>منشئ السيرة الذاتية | CV Builder</title>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    {CSS_STYLES}
</head>
<body>
    <div class="chat-container">
        <div class="language-selector">
            <label>اللغة / Language:</label>
            <select id="language" onchange="changeLanguage()">
                <option value="ar" selected>العربية</option>
                <option value="en">English</option>
            </select>
        </div>

        <h1>منشئ السيرة الذاتية | CV Builder</h1>

        <div id="chatbox">
            <!-- Messages will be appended here -->
        </div>

        <div class="input-area">
            <input id="input" type="text" placeholder="اكتب ردك هنا..." />
            <button onclick="sendMessage()">إرسال</button>
        </div>
    </div>
    {SCRTIPT}
</body>
</html>
"""
