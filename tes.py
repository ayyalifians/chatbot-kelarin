import os
from dotenv import load_dotenv
from groq import Groq

load_dotenv()

api_key = os.getenv("GROQ_API_KEY")
model = os.getenv("GROQ_MODEL")

print("API key terbaca :", "ya" if api_key else "TIDAK (cek file .env)")
print("Model           :", model)

client = Groq(api_key=api_key)
resp = client.chat.completions.create(
    model=model,
    messages=[{"role": "user", "content": "Beri satu tips singkat mengatur waktu belajar."}],
    max_tokens=1500,
)
print("\nJawaban:")
print(resp.choices[0].message.content)