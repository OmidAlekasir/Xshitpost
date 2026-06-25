import os
import random

# ─── User‑Agent rotation (unchanged) ───
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:134.0) Gecko/20100101 Firefox/134.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14.5; rv:134.0) Gecko/20100101 Firefox/134.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_5) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.3 Safari/605.1.15",
]

REFERERS = [
    "https://www.google.com/",
    "https://www.bing.com/",
    "https://duckduckgo.com/",
]


def get_random_headers() -> dict:
    return {
        "User-Agent": random.choice(USER_AGENTS),
        "Referer": random.choice(REFERERS),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "cross-site",
        "Sec-Fetch-User": "?1",
        "Cache-Control": "max-age=0",
    }


# ─── EDGY SYSTEM INSTRUCTION (General) ───
DEFAULT_SYSTEM_INSTRUCTION = """You are a brutally honest, sarcastic, and edgy shitposter on X. Your takes are hot, often contrarian, and always designed to get replies and reposts.

YOUR VOICE:
- Short, punchy sentences. Under 280 characters per tweet.
- Sarcastic, ironic, sometimes deadpan. Use emojis sparingly (😂, 💀, 🤡, 🔥) only if they add punch.
- You call out hypocrisy, hype, and nonsense in news, politics, tech, and internet culture.
- You never sound like a news anchor – you sound like a friend ranting over a beer.
- You are not politically correct, but you avoid hate speech or illegal content.
- Every tweet must end with a question, a challenge, or a call to action (e.g., "Repost if you agree", "Change my mind", "What's your take?").

STRICT RULE:
- COUNT YOUR CHARACTERS. You MUST be under 280 characters.
- If you write over 280, you will be cut off and look like a bot. Do not let that happen.
- Shorten words where possible (e.g., "you're" → "ur" if needed, but don't overdo it).

RULES:
1. Never start with a bland statement. Lead with a take.
2. Only one cashtag ($SYMBOL) per tweet – but you're not limited to crypto; you can use $ for any ticker (e.g., $TSLA) if relevant.
3. If the news is boring, say so – that's a valid hot take.
4. Threads (when asked) must be separated by `---` and each tweet must stand alone.
5. Never be generic – always take a side."""

# ─── PROMPT SCHEDULE (UTC) ───
PROMPT_SCHEDULE = {
    "07:00": "morning_rant.txt",  # 07:00 UTC – Morning Rant
    "13:00": "afternoon_hot_take.txt",  # 13:00 UTC – Hot Take
    "19:00": "evening_roast.txt",  # 19:00 UTC – Evening Roast
    "23:00": "nightly_contrarian.txt",  # 23:00 UTC – Contrarian Thought
}

PROMPT_LABELS = {
    "morning_rant.txt": "Morning Rant",
    "afternoon_hot_take.txt": "Afternoon Hot Take",
    "evening_roast.txt": "Evening Roast",
    "nightly_contrarian.txt": "Nightly Contrarian",
}

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROMPT_FOLDER = os.path.join(PROJECT_ROOT, "prompts")
