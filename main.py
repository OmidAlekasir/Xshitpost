import os
import sys
import re
from datetime import datetime
from modules.config import (
    PROMPT_SCHEDULE,
    PROMPT_LABELS,
    PROMPT_FOLDER,
    DEFAULT_SYSTEM_INSTRUCTION,
)
from modules.twitter_client import TwitterClient
from modules.ai_client import AIClient
from modules.news_fetcher import NewsFetcher


def load_prompt(filename: str) -> str:
    """Load a prompt file from the prompts folder."""
    path = os.path.join(PROMPT_FOLDER, filename)
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        print(f"Prompt file not found: {path}")
        return ""
    except Exception as e:
        print(f"Error loading prompt: {e}")
        return ""


def get_current_prompt_filename(now: datetime = None) -> str:
    """Return the prompt filename for the current run.

    Priority:
    1. PROMPT_FILE env var — set by the GitHub Actions workflow step that
       maps each cron trigger to its prompt. This is the authoritative source
       and avoids timezone mismatch (runners execute in UTC, schedule keys
       were previously in EST).
    2. Time-matching fallback — used when running locally or in environments
       where the env var is not set. Compares against UTC keys in
       PROMPT_SCHEDULE (kept in sync with schedule.yml cron hours).
    """
    env_prompt = os.environ.get("PROMPT_FILE", "").strip()
    if env_prompt:
        print(f"[INFO] Using PROMPT_FILE from environment: {env_prompt}")
        return env_prompt

    # Fallback: match against UTC time (PROMPT_SCHEDULE keys are UTC)
    from datetime import timezone
    if now is None:
        now = datetime.now(timezone.utc)
    current = now.strftime("%H:%M")
    times = sorted(PROMPT_SCHEDULE.keys())
    for t in reversed(times):
        if current >= t:
            return PROMPT_SCHEDULE[t]
    return PROMPT_SCHEDULE[times[0]]


def validate_tweet_content(content: str) -> bool:
    """
    Check if the generated content is valid (not an error message).
    """
    if not content:
        return False
    # Check for common error patterns
    error_patterns = [
        "LLM Error",
        "Error:",
        "UNAVAILABLE",
        "503",
        "429",
        "API key",
        "service unavailable",
        "try again later",
    ]
    content_lower = content.lower()
    for pattern in error_patterns:
        if pattern.lower() in content_lower:
            return False
    return True


def enforce_cashtag_limit(text: str) -> str:
    """
    X's free API tier allows a maximum of ONE cashtag ($SYMBOL) per tweet.
    If the model produces more than one, keep only the first occurrence and
    replace all subsequent ones with just the symbol name (e.g. $BTC -> BTC).

    This is a safety net — the prompts already instruct the model to use one
    cashtag per tweet, but LLMs slip. Better to silently fix than to 403.
    """
    cashtags = re.findall(r'\$[A-Z]{2,10}', text)
    if len(cashtags) <= 1:
        return text

    # Keep the first cashtag, replace the rest with plain text
    first = cashtags[0]
    seen = set()
    seen.add(first)

    def replace_extra(m):
        tag = m.group(0)
        if tag in seen:
            return tag  # first occurrence: keep as-is
        seen.add(tag)
        return tag[1:]  # strip the $ from subsequent occurrences

    result = re.sub(r'\$[A-Z]{2,10}', replace_extra, text)
    removed = [t for t in cashtags if t != first]
    print(f"[INFO] Cashtag limit enforced: kept {first}, de-tagged {set(removed)}")
    return result


def create_fallback_content(prompt_label: str, error_message: str) -> str:
    """
    Create a fallback tweet when AI generation fails.
    """
    fallbacks = {
        "Morning Flash": "Markets are quiet this morning. Watching key levels for a potential breakout. Waiting for clearer signals before taking action. Will update later.",
        "Strategy Thread": "Strategy update pending. Market structure remains unclear. Watching volume and key support/resistance levels. Stay tuned for detailed analysis.",
        "Session Recap": "Today's session was mixed. Volume lower than average. Waiting for more data before drawing conclusions. Key levels remain intact.",
        "Contrarian View": "No strong contrarian signals today. Markets appear to be pricing in current news. Monitoring for divergence in sentiment and positioning.",
    }

    return fallbacks.get(
        prompt_label,
        "Market analysis update pending. Data is still being processed. Will share insights shortly.",
    )


if __name__ == "__main__":
    """Main entry point: fetch context, generate tweet(s), and post."""
    print("[INFO] Running scheduled prompt...")

    # Initialize clients
    ai = AIClient()
    twitter = TwitterClient()
    news = NewsFetcher()

    # Determine prompt
    prompt_file = get_current_prompt_filename()
    prompt_label = PROMPT_LABELS.get(prompt_file, "Prompt")
    prompt_text = load_prompt(prompt_file)
    if not prompt_text:
        print("[ERROR] Prompt text is empty. Exiting.")
        # Post a fallback error message
        fallback = (
            f"⚠️ System issue: Prompt file '{prompt_file}' not found. Working on a fix."
        )
        twitter.post_tweet(fallback)
        sys.exit()

    # Build context
    context, news_items = news.get_context()
    filled_prompt = prompt_text.replace("{{news_context}}", context)

    # Generate response with error handling
    print("[INFO] Generating AI response...")
    response_data = ai.generate(
        filled_prompt, system_instruction=DEFAULT_SYSTEM_INSTRUCTION
    )

    if not response_data["success"]:
        error_msg = response_data["error"]
        print(f"[ERROR] AI generation failed: {error_msg}")

        # Create a fallback tweet
        fallback_tweet = create_fallback_content(prompt_label, error_msg)
        print(f"[INFO] Using fallback content: {fallback_tweet}")

        # Post the fallback
        twitter.post_tweet(fallback_tweet)
        sys.exit()

    response = response_data["content"]
    print(f"[{prompt_label}] Generated response:\n{response}\n")

    # Validate content
    if not validate_tweet_content(response):
        print(f"[WARNING] Invalid content detected: {response[:100]}...")
        # Try to salvage or use fallback
        if len(response) < 50 or "Error" in response:
            fallback_tweet = create_fallback_content(
                prompt_label, "Generated content was invalid"
            )
            twitter.post_tweet(fallback_tweet)
            sys.exit()

    # Parse the selected news index (if any)
    selected_image_url = None
    match = re.match(r"\[(\d+)\]", response)
    if match:
        idx = int(match.group(1)) - 1
        if 0 <= idx < len(news_items):
            selected_image_url = news_items[idx].get("image_url")
        response = re.sub(r"^\[\d+\]\s*", "", response)

    # Upload image if available
    media_ids = None
    if selected_image_url:
        print(f"[INFO] Uploading media from: {selected_image_url}")
        media_id = twitter.upload_media_from_url(selected_image_url)
        if media_id:
            # Wait a moment for Twitter to process the media
            import time

            time.sleep(3)
            media_ids = [media_id]  # list of strings
        else:
            print("[WARNING] Media upload failed – proceeding without image.")

    # Post as self-reply thread (guaranteed)
    try:
        if "---" in response:
            tweets = [part.strip() for part in response.split("---") if part.strip()]
            tweets = [
                enforce_cashtag_limit(re.sub(r"^\[\d+\]\s*", "", t))
                for t in tweets
                if validate_tweet_content(t)
            ]
            if not tweets:
                raise ValueError("No valid tweets in thread")

            # Post first tweet (the hook) with media (if any)
            first_tweet_id = twitter.post_tweet(tweets[0], media_ids=media_ids)
            print(f"[INFO] Posted hook tweet (ID: {first_tweet_id})")

            # Post remaining tweets as replies to the previous one
            previous_id = first_tweet_id
            for tweet_text in tweets[1:]:
                # Pass the previous tweet ID as reply_to
                reply_id = twitter.post_tweet(tweet_text, in_reply_to=previous_id)
                print(f"[INFO] Posted reply tweet (ID: {reply_id})")
                previous_id = reply_id  # Chain replies (Tweet 2 replies to Tweet 1, Tweet 3 replies to Tweet 2...)

            print(
                f"[SUCCESS] Posted thread with {len(tweets)} tweets (self-reply chain)"
            )
        else:
            if validate_tweet_content(response):
                twitter.post_tweet(enforce_cashtag_limit(response), media_ids=media_ids)
                print("[SUCCESS] Posted single tweet")
            else:
                raise ValueError("Invalid tweet content")

    except Exception as e:
        print(f"[ERROR] Failed to post: {e}")
        # ❌ Do NOT post anything. Just exit.
        sys.exit(1)
