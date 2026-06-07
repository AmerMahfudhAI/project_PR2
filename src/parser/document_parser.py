import os
import logging
import PyPDF2
import docx  

# Configure logging to monitor parsing activities and errors safely
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def extract_text_from_pdf(pdf_path: str) -> str:
    """
    Extracts and merges raw text from all pages of a PDF file.
    
    Args:
        pdf_path (str): The local server path to the uploaded PDF file.
        
    Returns:
        str: Accumulated plain text from the document, or empty string on failure.
    """
    extracted_text = ""
    try:
        with open(pdf_path, "rb") as file:
            pdf_reader = PyPDF2.PdfReader(file)
            # Loop through each page in the PDF and extract text characters
            for page in pdf_reader.pages:
                page_content = page.extract_text()
                if page_content:
                    extracted_text += page_content + "\n"
        return extracted_text.strip()
    except Exception as e:
        logger.error(f"Failed to parse PDF at {pdf_path}: {str(e)}")
        return ""

def extract_text_from_docx(docx_path: str) -> str:
    """
    Extracts and merges paragraphs from a Microsoft Word (.docx) file.
    
    Args:
        docx_path (str): The local server path to the uploaded Word file.
        
    Returns:
        str: Accumulated plain text from the document, or empty string on failure.
    """
    try:
        doc = docx.Document(docx_path)
        full_text = []
        # Gather all text paragraphs while maintaining line-breaks
        for para in doc.paragraphs:
            if para.text.strip():
                full_text.append(para.text)
        return "\n".join(full_text).strip()
    except Exception as e:
        logger.error(f"Failed to parse DOCX at {docx_path}: {str(e)}")
        return ""

def get_document_text(file_path: str) -> str:
    """
    Router function that detects the file extension and triggers the appropriate parser.
    
    Args:
        file_path (str): The path to the document file.
        
    Returns:
        str: Extracted clean textual content of the document.
    """
    # Extract the file extension and convert to lowercase for comparison
    _, ext = os.path.splitext(file_path)
    ext = ext.lower()
    
    if ext == ".pdf":
        logger.info(f"Triggering PDF parser for: {file_path}")
        return extract_text_from_pdf(file_path)
    elif ext == ".docx":
        logger.info(f"Triggering Word DOCX parser for: {file_path}")
        return extract_text_from_docx(file_path)
    else:
        logger.warning(f"Unsupported file format attempted: {ext}")
        return ""