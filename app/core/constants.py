from typing import Any

# CV Fields
PERSONAL_INFO_FIELDS = ["name", "email", "phone", "address"]

# Prompts for different languages
PROMPTS: dict[str, dict[str, Any]] = {
    "ar": {
        "personal_info": {
            "name": "ما هو اسمك الكامل؟",
            "email": "ما هو عنوان بريدك الإلكتروني؟",
            "phone": "ما هو رقم هاتفك؟",
            "address": "ما هو عنوانك؟",
        },
        "education": "الرجاء تقديم تفاصيل تعليمك...",
        "work_experience": "الرجاء تقديم تفاصيل خبرتك المهنية...",
        "skills": "الرجاء إدراج مهاراتك...",
        "finalize": "سيرتك الذاتية جاهزة للإنشاء...",
    },
    "en": {
        "personal_info": {
            "name": "What is your full name?",
            "email": "What is your email address?",
            "phone": "What is your phone number?",
            "address": "What is your address?",
        },
        "education": "Please provide details of your education...",
        "work_experience": "Please provide details of your work experience...",
        "skills": "Please list your skills...",
        "finalize": "Your CV is ready to be generated...",
    },
}

# Keywords for different languages
KEYWORDS = {
    "ar": {"done": "تم", "review": "مراجعة", "generate": "إنشاء", "edit": "تعديل"},
    "en": {"done": "done", "review": "review", "generate": "generate", "edit": "edit"},
}


RESUME_SECTIONS = ["personal_info", "work_experience", "education"]
