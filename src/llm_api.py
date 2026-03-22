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
                model="nvidia/nemotron-3-super-120b-a12b:free",
                # model="deepseek/deepseek-r1-0528:free",
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

def refine_merge_candidate(original_prompt: str, feedback: str, previous_output: str, model="meituan/longcat-flash-chat:free"):
    """Regenerate a merge candidate with user feedback."""
    refinement_prompt = f"""
You are refining a merge candidate for Java code.

Original instruction:
{original_prompt}

Previous merge candidate:
{previous_output}
User feedback:
{feedback}

Generate a new improved merge candidate that incorporates the feedback.
"""
    try:
        response = client.chat.completions.create(
            model=model,
            extra_headers={},
            messages=[{"role": "user", "content": refinement_prompt}],
            temperature=0.3,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"[❌] Error during refinement: {e}")
        return None

def get_chat_completion(messages, retries=3):
    """
    Takes a full conversation history (list of message dicts) 
    and returns the LLM's next response.
    """
    for attempt in range(retries):
        try:
            response = client.chat.completions.create(
                model="nvidia/nemotron-3-super-120b-a12b:free", # Or your preferred model
                extra_headers={},
                messages=messages,
                timeout=120 
            )
            return response.choices[0].message.content

        except Exception as e:
            print(f"[⚠️] Attempt {attempt + 1} failed: {e}")
            time.sleep(2 * (attempt + 1))

    print("[❌] All attempts failed. LLM may be rate-limited or offline.")
    return None