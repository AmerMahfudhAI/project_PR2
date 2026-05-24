from fastapi import FastAPI, UploadFile, File
from src.ai_review.reviewer import AIResumeReviewer
from src.parser.document_parser import extract_text_from_pdf # تأكد من اسم المسار عندك
import os

app = FastAPI()
reviewer = AIResumeReviewer()

@app.post("/analyze-resume")
async def analyze_resume(file: UploadFile = File(...)):
    # 1. Save the uploaded file temporarily
    temp_path = f"temp_{file.filename}"
    with open(temp_path, "wb") as buffer:
        buffer.write(await file.read())

    try:
        # 2. Extract text from the PDF using your parser
        resume_text = extract_text_from_pdf(temp_path)
        
        if "ERROR" in resume_text:
            return {"status": "error", "message": "Failed to parse PDF"}

        # 3. Get the structured review from Gemini
        structured_result = reviewer.get_review(resume_text)

        # 4. Return the structured JSON
        return {
            "status": "success",
            "filename": file.filename,
            "data": structured_result
        }

    finally:
        # 5. Clean up: Delete the temporary file
        if os.path.exists(temp_path):
            os.remove(temp_path)