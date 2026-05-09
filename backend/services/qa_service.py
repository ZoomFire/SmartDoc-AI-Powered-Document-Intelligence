from groq import Groq
import os
from dotenv import load_dotenv
from services.embedding_service import search

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

def ask_question(question):
    context = search(question)

    if not context:
        return "Please upload a PDF first."

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",   # ✅ latest working model
        messages=[
            {
                "role": "system",
                "content": "Give a clear, detailed answer (at least 80 words) in simple language."
            },
            {
                "role": "user",
                "content": f"""
                Answer the question using the context below.

                Question:
                {question}

                Context:
                {context}
                """
            }
        ]
    )

    return response.choices[0].message.content