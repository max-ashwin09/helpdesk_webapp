import os
from typing import List
from django.conf import settings

def build_context_snippet(question_title: str, related_titles: List[str]) -> str:
    ctx = "Similar questions (titles):\n"
    for i, t in enumerate(related_titles, 1):
        ctx += f"{i}. {t}\n"
    ctx += "\nAnswer the user clearly with steps and code if relevant."
    return ctx

def fake_ai_answer(question_title: str, ctx: str) -> str:
    # Dev/testing ke liye bina API cost ke placeholder
    return (
        f"(FAKE-AI) Draft for: {question_title}\n\n"
        f"- Check docs/FAQ.\n- Try common fixes.\n- Context seen:\n{ctx}"
    )

def get_ai_answer(question_title: str, ctx: str) -> str:
    # Fallback: fake AI
    if getattr(settings, "USE_FAKE_AI", False) or not settings.OPENAI_API_KEY:
        return fake_ai_answer(question_title, ctx)

    try:
        # OpenAI modern client
        from openai import OpenAI
        client = OpenAI(api_key=settings.OPENAI_API_KEY)

        prompt = (
            "You are a helpful support agent for a developer helpdesk.\n"
            f"User Question: {question_title}\n\n"
            f"Context:\n{ctx}\n\n"
            "Write a concise, accurate answer. If you’re unsure, state assumptions. "
            "Prefer bullet points and short code snippets where helpful."
        )
        resp = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.4,
            max_tokens=350,
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        # Don’t break UI; show graceful message
        return f"(AI error) Could not fetch AI answer: {e}"
