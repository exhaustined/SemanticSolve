from openai import OpenAI
from dotenv import load_dotenv
import os
import time

load_dotenv()
api_key = os.getenv("OPENROUTER_API_KEY")

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=api_key,
)

def get_merge_candidates(prompt, retries=3):
    for attempt in range(retries):
        try:
            response = client.chat.completions.create(
                model="deepseek/deepseek-r1-0528:free",
                extra_headers={},
                messages=[
                    {"role": "user", "content": prompt}
                ],
                timeout=60  # optional
            )
            return response.choices[0].message.content

        except Exception as e:
            print(f"[⚠️] Attempt {attempt + 1} failed: {e}")
            time.sleep(2 * (attempt + 1))

    print("[❌] All attempts failed. LLM may be rate-limited or offline.")
    return None
