import fitz
from services.embedding_service import create_embeddings

def extract_text(file):
    file_bytes = file.file.read()

    doc = fitz.open(stream=file_bytes, filetype="pdf")

    text = ""
    for page in doc:
        text += page.get_text()

    create_embeddings(text)

    return text