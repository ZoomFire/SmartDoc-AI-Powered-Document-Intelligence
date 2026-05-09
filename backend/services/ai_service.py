from groq import Groq
import os
from dotenv import load_dotenv

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

def summarize(text):
    text = text[:3000]

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",   # ✅ latest working model
        messages=[
            {
                "role": "user",
                "content": f"""
                Summarize the following text clearly in 5-6 lines:

                {text}
                """
            }
        ]
    )

    return response.choices[0].message.content