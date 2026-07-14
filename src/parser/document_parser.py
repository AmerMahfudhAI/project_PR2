import os
import docx2txt
from pypdf import PdfReader
import requests

def get_document_text(file_source: str) -> str:
    """
    Extracts text from PDF and DOCX files safely without printing logs.
    """
    local_path = file_source
    is_downloaded = False

    # إذا كان المسار يبدأ بـ http فهذا يعني أنه رابط أونلاين من Cloudinary
    if file_source.startswith("http://") or file_source.startswith("https://"):
        try:
            response = requests.get(file_source, timeout=15)
            response.raise_for_status()
            
            # استخراج اسم الملف وامتداده من الرابط
            filename = file_source.split("/")[-1].split("?")[0]
            if not filename or "." not in filename:
                filename = "downloaded_doc.pdf"
                
            local_path = f"temp_{filename}"
            with open(local_path, "wb") as f:
                f.write(response.content)
            is_downloaded = True
        except Exception as e:
            return ""

    # استخراج النص بناءً على امتداد الملف المكتشف
    text = ""
    try:
        if local_path.lower().endswith('.pdf'):
            reader = PdfReader(local_path)
            for page in reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
        elif local_path.lower().endswith(('.docx', '.doc')):
            text = docx2txt.process(local_path)
    except Exception:
        text = ""
    finally:
        # حذف الملف المؤقت فوراً إذا تم تحميله من أونلاين للحفاظ على نظافة السيرفر
        if is_downloaded and os.path.exists(local_path):
            os.remove(local_path)

    return text