from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import os, io, uuid
import pdfplumber
import numpy as np
import faiss
from groq import Groq
from sentence_transformers import SentenceTransformer

# DB
from sqlalchemy import create_engine, Column, Integer, String, Text
from sqlalchemy.orm import declarative_base, sessionmaker

# ---------- LOAD ENV ----------
load_dotenv()

app = FastAPI()

# ---------- CORS ----------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------- DATABASE ----------
DATABASE_URL = "sqlite:///./smartdocs.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()

# ---------- TABLES ----------
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    username = Column(String, unique=True)
    password = Column(String)

class History(Base):
    __tablename__ = "history"
    id = Column(Integer, primary_key=True)
    username = Column(String)
    question = Column(Text)
    answer = Column(Text)

# 🔥 NEW TABLES
class Document(Base):
    __tablename__ = "documents"
    id = Column(Integer, primary_key=True)
    filename = Column(String)
    content = Column(Text)
    owner = Column(String)

class ShareLink(Base):
    __tablename__ = "share_links"
    id = Column(Integer, primary_key=True)
    doc_id = Column(Integer)
    token = Column(String)

class Team(Base):
    __tablename__ = "teams"
    id = Column(Integer, primary_key=True)
    name = Column(String)

Base.metadata.create_all(bind=engine)

# ---------- GROQ ----------
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

# ---------- EMBEDDINGS ----------
embedder = SentenceTransformer("all-MiniLM-L6-v2")

# ---------- STORAGE ----------
DOCUMENT_CHUNKS = []
INDEX = None

# ---------- CLEAN ----------
def clean_text(text):
    import re
    return re.sub(r'\s+', ' ', text).strip()

# ---------- SPLIT ----------
def split_text(text, size=500):
    return [text[i:i+size] for i in range(0, len(text), size)]

# ---------- INDEX ----------
def create_index(chunks):
    embeddings = embedder.encode(chunks)
    dim = embeddings.shape[1]
    index = faiss.IndexFlatL2(dim)
    index.add(np.array(embeddings))
    return index

# ---------- RETRIEVE ----------
def retrieve(query, k=3):
    query_embedding = embedder.encode([query])
    _, indices = INDEX.search(np.array(query_embedding), k)
    return [DOCUMENT_CHUNKS[i] for i in indices[0]]

# ---------- LLM ----------
def ask_llm(prompt):
    try:
        res = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": "Give clear answers"},
                {"role": "user", "content": prompt}
            ]
        )
        return res.choices[0].message.content
    except:
        res = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": prompt}]
        )
        return res.choices[0].message.content

# ================= AUTH =================

@app.post("/register")
def register(data: dict):
    db = SessionLocal()
    db.add(User(username=data["username"], password=data["password"]))
    db.commit()
    return {"status": "registered"}

@app.post("/login")
def login(data: dict):
    db = SessionLocal()
    user = db.query(User).filter(User.username == data["username"]).first()
    if user and user.password == data["password"]:
        return {"status": "success"}
    return {"status": "fail"}

# ================= SUMMARIZE =================

@app.post("/summarize")
async def summarize(file: UploadFile = File(...), mode: str = Form("Short")):
    global DOCUMENT_CHUNKS, INDEX

    DOCUMENT_CHUNKS = []
    INDEX = None

    content = await file.read()
    text = ""

    try:
        if file.filename.endswith(".pdf"):
            with pdfplumber.open(io.BytesIO(content)) as pdf:
                for p in pdf.pages:
                    text += p.extract_text() or ""
        elif file.filename.endswith(".txt"):
            text = content.decode()
        else:
            return {"error": "Only PDF and TXT supported"}
    except Exception as e:
        return {"error": str(e)}

    text = clean_text(text)
    chunks = split_text(text)

    DOCUMENT_CHUNKS = chunks
    INDEX = create_index(chunks)

    # 🔥 SAVE DOCUMENT
    db = SessionLocal()
    db.add(Document(filename=file.filename, content=text, owner="user"))
    db.commit()

    summary_text = "\n\n".join(chunks[:3])

    if mode == "Bullet":
        prompt = f"Convert into bullet points:\n{summary_text}"
    elif mode == "Detailed":
        prompt = f"Explain in detail:\n{summary_text}"
    elif mode == "ELI5":
        prompt = f"Explain simply:\n{summary_text}"
    else:
        prompt = f"Short summary:\n{summary_text}"

    return {"summary": ask_llm(prompt)}

# ================= ASK =================

@app.post("/ask")
async def ask(data: dict):
    db = SessionLocal()

    if not DOCUMENT_CHUNKS:
        return {"answer": "Process document first"}

    question = data["question"]
    username = data.get("username", "guest")

    context = "\n".join(retrieve(question))
    answer = ask_llm(f"{context}\nQ:{question}")

    db.add(History(username=username, question=question, answer=answer))
    db.commit()

    return {"answer": answer}

# ================= HISTORY =================

@app.get("/history/{user}")
def history(user: str):
    db = SessionLocal()
    h = db.query(History).filter(History.username == user).all()
    return {"history": [{"q": x.question, "a": x.answer} for x in h]}

# ================= SHARE =================

@app.post("/share")
def share():
    db = SessionLocal()

    doc = db.query(Document).order_by(Document.id.desc()).first()
    if not doc:
        return {"error": "No document"}

    token = str(uuid.uuid4())
    db.add(ShareLink(doc_id=doc.id, token=token))
    db.commit()

    return {"url": f"http://127.0.0.1:8000/share/{token}"}

@app.get("/share/{token}")
def open_share(token: str):
    db = SessionLocal()

    link = db.query(ShareLink).filter(ShareLink.token == token).first()
    if not link:
        return {"error": "Invalid link"}

    doc = db.query(Document).filter(Document.id == link.doc_id).first()
    return {"content": doc.content[:2000]}

# ================= ANALYTICS =================

@app.get("/analytics/{username}")
def analytics(username: str):
    db = SessionLocal()

    history = db.query(History).filter(History.username == username).all()

    return {
        "total_questions": len(history),
        "recent": [h.question for h in history[-5:]]
    }

# ================= TEAM =================

@app.post("/create-team")
def create_team(data: dict):
    db = SessionLocal()
    db.add(Team(name=data["name"]))
    db.commit()
    return {"status": "team created"}