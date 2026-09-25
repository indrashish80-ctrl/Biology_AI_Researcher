import os
from dotenv import load_dotenv
from google import genai

# Load variables from .env
load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    raise RuntimeError(
        "GEMINI_API_KEY was not found. Check your .env file."
    )

# Connect to Gemini
client = genai.Client(api_key=api_key)

# Send a simple test request
response = client.models.generate_content(
    model="gemini-3.8-flash",
    contents="Reply with exactly: Gemini is working."
)

print(response.text)