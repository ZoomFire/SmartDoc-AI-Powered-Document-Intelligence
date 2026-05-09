from fastapi import APIRouter, UploadFile, File
from pydantic import BaseModel
from services.pdf_service import extract_text
from services.ai_service import summarize
from services.qa_service import ask_question

router = APIRouter()

class QuestionRequest(BaseModel):
    question: str


@router.post("/summarize")
async def summarize_pdf(file: UploadFile = File(...)):
    text = extract_text(file)
    summary = summarize(text)

    return {
        "filename": file.filename,
        "summary": summary
    }


@router.post("/ask")
def ask(req: QuestionRequest):
    answer = ask_question(req.question)
    return {"answer": answer}