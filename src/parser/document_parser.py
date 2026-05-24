import PyPDF2
import docx  
import os
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def extract_text_from_pdf(pdf_path: str) -> str:
    extracted_text = ""
    try:
        with open(pdf_path, "rb") as file:
            pdf_reader = PyPDF2.PdfReader(file)
            for page in pdf_reader.pages:
                page_content = page.extract_text()
                if page_content:
                    extracted_text += page_content + "\n"
        return extracted_text.strip()
    except Exception as e:
        logger.error(f"Failed to parse PDF: {str(e)}")
        return ""

def extract_text_from_docx(docx_path: str) -> str:
    try:
        doc = docx.Document(docx_path)
        full_text = []
        for para in doc.paragraphs:
            full_text.append(para.text)
        return "\n".join(full_text).strip()
    except Exception as e:
        logger.error(f"Failed to parse DOCX: {str(e)}")
        return ""

def get_document_text(file_path: str) -> str:
    ext = os.path.splitext(file_path)[1].lower()
    if ext == ".pdf":
        return extract_text_from_pdf(file_path)
    elif ext == ".docx":
        return extract_text_from_docx(file_path)
    else:
        logger.warning(f"Unsupported file format: {ext}")
        return ""