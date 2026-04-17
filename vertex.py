import time
from pathlib import Path
from google import genai
from google.genai.types import HttpOptions

client = genai.Client(http_options=HttpOptions(api_version="v1"))
chat = client.chats.create(model="gemini-2.5-flash")

readme = Path("README.md")
repo_context = readme.read_text()[:12000] if readme.exists() else ""

print("Type 'exit' to quit.")
while True:
    user_input = input("You> ").strip()
    if user_input.lower() in {"exit", "quit"}:
        break

    prompt = f"""You are helping with this repository.

Repository context:
{repo_context}

User request:
{user_input}
"""

    for attempt in range(5):
        try:
            response = chat.send_message(prompt)
            print("Gemini>", response.text)
            break
        except Exception as e:
            if "429" in str(e) and attempt < 4:
                wait = 2 ** attempt
                print(f"Rate limited, retrying in {wait}s...")
                time.sleep(wait)
            else:
                raise
