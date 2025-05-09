from openai import OpenAI
import json
import re
from config import get_open_ai_cred

API_KEY = get_open_ai_cred().OPEN_AI_API_KEY

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
        "Generate 6 to 10 structured course titles for the given topic. "
        "The courses ranging from beginner to advanced level. "
        "Each course must include:\n"
        "- A clear, concise title\n"
        "- A 1-2 sentence description of what the course offers (use <br> for line breaks) make sure the content not more than 30 - 40 words use bullet point if you think needed\n"
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


def generate_course_structure(course_title: str, course_description: str) -> list:
    prompt = (
        f"You are a course designer.\n"
        f"For the course titled: \"{course_title}\"\n"
        f"With description: \"{course_description}\"\n"
        f"Generate a JSON list of 10-12 sections. Each section must include:\n"
        f"- section_title\n"
        f"- a list of subsection_titles (3-6 per section)."
        f"Special Instruction do not retun dictionary your response should be a list of dictionary always"
        "in the dictionary always follow the structure  {section_title: generated from you, subsection_titles: [list of subtitles generated] }"
    )

    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,
    )

    content = response.choices[0].message.content
    return safe_parse_json(content)


def generate_section_content(course_title, course_level, section_title, subsection_title):
    # Tailor prompt based on the course level
    if course_level.lower() == "beginner":
        level_instruction = "The content should be simple and beginner-friendly, avoiding technical jargon."
    elif course_level.lower() == "intermediate":
        level_instruction = (
            "The content should assume the reader has basic knowledge of the topic and should cover deeper concepts with some technical terms."
        )
    elif course_level.lower() == "advanced":
        level_instruction = (
            "The content should be advanced, covering complex topics in detail and using technical language where necessary."
        )
    else:
        # Default fallback
        level_instruction = "Write detailed content appropriate for the target audience."

    prompt = (
        f"You are a course writer.\n"
        f"Course title: \"{course_title}\" (Level: {course_level})\n"
        f"Section: \"{section_title}\"\n"
        f"Subsection: \"{subsection_title}\"\n\n"
        f"Write detailed content (around 300-400 words).\n"
        f"{level_instruction}\n"
        f"Include examples where useful and make the content engaging.\n\n"
        f"If you include any code, make sure it is wrapped using proper Markdown code blocks "
        f"like this:\n\n"
        f"```"
        f"<your code here>"
        f"```"
    )

    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,
    )
    return response.choices[0].message.content

