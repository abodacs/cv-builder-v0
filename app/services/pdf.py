import os
import uuid
from typing import List, Dict
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from app.core.state import CVState
from app.core.config import Config

# Setup Arabic font from static directory
if not os.path.exists(Config.FONTS_DIR):
    os.makedirs(Config.FONTS_DIR, exist_ok=True)

if os.path.exists(Config.ARABIC_FONT_PATH):
    pdfmetrics.registerFont(TTFont('ArabicFont', Config.ARABIC_FONT_PATH))
    ARABIC_FONT_REGISTERED = True
else:
    print(f"Warning: Arabic font not found at {Config.ARABIC_FONT_PATH}")
    ARABIC_FONT_REGISTERED = False

def format_cv_text(state: CVState) -> str:
    """Format CV content as text."""
    lang = state.language
    p_info = state.personal_info or {}
    
    cv_lines = [
        p_info.get("name", "N/A"),
        f"{p_info.get('email', 'N/A')} | {p_info.get('phone', 'N/A')} | {p_info.get('address', 'N/A')}",
        "\n" + ("التعليم" if lang == "ar" else "Education"),
        "-" * 30,
        *[item.get("details", "") for item in state.education],
        "\n" + ("الخبرة المهنية" if lang == "ar" else "Work Experience"),
        "-" * 30,
        *[item.get("details", "") for item in state.work_experience],
        "\n" + ("المهارات" if lang == "ar" else "Skills"),
        "-" * 30,
        ", ".join(state.skills)
    ]
    return "\n".join(line for line in cv_lines if line)

def generate_cv_pdf(state: CVState) -> str:
    """Generate PDF CV and return download URL."""
    pdf_filename = f"cv_output_{uuid.uuid4().hex}.pdf"
    static_dir = "static"
    pdf_filepath = os.path.join(static_dir, pdf_filename)
    
    styles = getSampleStyleSheet()
    style_normal = styles['Normal'].clone('style_normal')
    style_heading = styles['h2'].clone('style_heading')
    
    if state.language == "ar" and ARABIC_FONT_REGISTERED:
        style_normal.fontName = style_heading.fontName = 'ArabicFont'
        style_normal.alignment = style_heading.alignment = 2  # Right align
    
    doc = SimpleDocTemplate(
        pdf_filepath,
        pagesize=letter,
        leftMargin=50,
        rightMargin=50,
        topMargin=50,
        bottomMargin=50
    )
    
    story = []
    def add_section(title: str, content: List[str]):
        story.append(Paragraph(title, style_heading))
        for item in content:
            if item.strip():
                story.append(Paragraph(item.replace('\n', '<br/>'), style_normal))
        story.append(Paragraph("<br/>", style_normal))
    
    # Add sections
    p_info = state.personal_info
    story.append(Paragraph(p_info.get("name", ""), style_heading))
    story.append(Paragraph(
        f"{p_info.get('email', '')} | {p_info.get('phone', '')} | {p_info.get('address', '')}",
        style_normal
    ))
    
    add_section(
        "التعليم" if state.language == "ar" else "Education",
        [edu.get("details", "") for edu in state.education]
    )
    
    add_section(
        "الخبرة المهنية" if state.language == "ar" else "Work Experience",
        [exp.get("details", "") for exp in state.work_experience]
    )
    
    add_section(
        "المهارات" if state.language == "ar" else "Skills",
        [", ".join(state.skills)]
    )
    
    doc.build(story)
    return f"/static/{pdf_filename}"
