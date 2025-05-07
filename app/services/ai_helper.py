from openai import OpenAI
import json
import re
from config import get_open_ai_cred

API_KEY = get_open_ai_cred().OPEN_AI_API_KEY

# ✅ Create OpenAI client
client = OpenAI(api_key=API_KEY)


def safe_parse_json(content: str) -> list:
    """
    Safely parse JSON from a string, even if it's embedded in extra content.
    """
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        pass

    try:
        match = re.search(r'\[\s*{.*?}\s*\]', content, re.DOTALL)
        if match:
            return json.loads(match.group(0))
    except Exception as e:
        print("JSON parsing failed:", e)

    return []


def generate_courses(topic: str, description: str = "") -> list:
    """
    Generate 10 structured course ideas for a given topic using OpenAI.
    """
    system_msg = (
        "You are an AI course planner. "
        "Generate 10 structured course titles for the given topic. "
        "The courses should be short, ranging from beginner to advanced level. "
        "Each course must include:\n"
        "- A clear, concise title\n"
        "- A 1-2 sentence description of what the course offers (use <br> for line breaks) make sure the content not more than 30 words\n"
        "- A course level (e.g., Beginner, Intermediate, Advanced)\n"
        "Ensure that all 10 courses are unique in content and coverage.\n"
        "Return the result as a JSON array of objects with keys: title, description, and course_level."
    )

    if description:
        system_msg += f"\n\nTopic description provided by user: \"{description}\""

    user_msg = f"Generate 10 courses for the topic: {topic}"

    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": system_msg},
                {"role": "user", "content": user_msg},
            ],
            temperature=0.7,
        )

        content = response.choices[0].message.content
        return safe_parse_json(content)

    except Exception as e:
        print("Unexpected Error:", e)

    return []
