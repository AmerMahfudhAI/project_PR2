import os
import docx2txt
from pypdf import PdfReader  # تم التحديث هنا لاستخدام المكتبة الجديدة بدلاً من PyPDF2

def get_document_text(file_path: str) -> str:
    """
    Extracts text from PDF and DOCX files safely.
    """
    if not os.path.exists(file_path):
        return ""
        
    ext = os.path.splitext(file_path)[1].lower()
    text = ""
    
    try:
        if ext == ".pdf":
            reader = PdfReader(file_path)
            for page in reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
        elif ext in [".docx", ".doc"]:
            text = docx2txt.process(file_path)
    except Exception as e:
        print(f"Error parsing document {file_path}: {str(e)}")
        
    return text.strip()