
# HTML for the frontend
HTML = """
<!DOCTYPE html>
<html dir="rtl">
<head>
    <title>منشئ السيرة الذاتية | CV Builder</title>
    <meta charset="UTF-8">
    <style>
        body { 
            font-family: 'Arial', 'Traditional Arabic', sans-serif; 
            margin: 20px; 
        }
        #chatbox { 
            border: 1px solid #ccc; 
            height: 400px; 
            overflow-y: scroll; 
            padding: 10px; 
            margin-bottom: 10px; 
            text-align: start; /* For Arabic */
        }
        #input { 
            width: 80%; 
            padding: 5px; 
            text-align: start; /* For Arabic */
        }
        button { 
            padding: 5px 10px; 
        }
        .language-selector {
            margin-bottom: 10px;
        }
        /* Add class for left-to-right content */
        .ltr {
            direction: ltr;
            text-align: end;
        }
    </style>
</head>
<body>
    <div class="language-selector">
        <label>اللغة / Language:</label>
        <select id="languageSelect" onchange="changeLanguage()">
            <option value="ar" selected>العربية</option>
            <option value="en">English</option>
        </select>
    </div>
    <h1>منشئ السيرة الذاتية | CV Builder</h1>
    <div id="chatbox"></div>
    <input id="input" type="text" placeholder="اكتب ردك هنا..." />
    <button onclick="sendMessage()">إرسال</button>

    <script>
        let sessionId = localStorage.getItem("cv_session_id");
        let currentLanguage = localStorage.getItem("cv_language") || "ar";
        
        if (!sessionId) {
            sessionId = window.crypto.randomUUID();
            localStorage.setItem("cv_session_id", sessionId);
        }

        // Set initial language
        document.getElementById("languageSelect").value = currentLanguage;
        updateDirection(currentLanguage);

        const ws = new WebSocket("ws://" + window.location.host + "/ws/cv_builder");
        const chatbox = document.getElementById("chatbox");
        const input = document.getElementById("input");

        function updateDirection(lang) {
            document.documentElement.dir = lang === "ar" ? "rtl" : "ltr";
            document.body.dir = lang === "ar" ? "rtl" : "ltr";
            input.placeholder = lang === "ar" ? "اكتب ردك هنا..." : "Type your response here...";
            document.querySelector("button").textContent = lang === "ar" ? "إرسال" : "Send";
        }

        function changeLanguage() {
            const lang = document.getElementById("languageSelect").value;
            currentLanguage = lang;
            localStorage.setItem("cv_language", lang);
            updateDirection(lang);
            // Notify server about language change
            ws.send(JSON.stringify({ 
                session_id: sessionId, 
                text: "", 
                language: lang,
                change_language: true 
            }));
        }

        ws.onopen = function() {
            // Send session ID and language on connect
            ws.send(JSON.stringify({ 
                session_id: sessionId, 
                text: "",
                language: currentLanguage 
            }));
        };

        ws.onmessage = function(event) {
            const message = JSON.parse(event.data);
            const p = document.createElement("p");
            p.innerHTML = message.sender + ": " + message.text;
            if (message.language === "en") {
                p.classList.add("ltr");
            }
            chatbox.appendChild(p);
            chatbox.scrollTop = chatbox.scrollHeight;
        };

        function sendMessage() {
            const text = input.value.trim();
            if (text) {
                ws.send(JSON.stringify({ 
                    session_id: sessionId, 
                    text: text,
                    language: currentLanguage 
                }));
                const p = document.createElement("p");
                p.innerHTML = (currentLanguage === "ar" ? "أنت" : "You") + ": " + text;
                if (currentLanguage === "en") {
                    p.classList.add("ltr");
                }
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
