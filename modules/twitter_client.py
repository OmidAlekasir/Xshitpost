import os
import time
from requests_oauthlib import OAuth1
import requests
import tweepy
from .config import get_random_headers


class TwitterClient:
    def __init__(
        self, api_key=None, api_secret=None, access_token=None, access_token_secret=None
    ):
        self.api_key = api_key or os.getenv("TWITTER_API_KEY")
        self.api_secret = api_secret or os.getenv("TWITTER_API_SECRET")
        self.access_token = access_token or os.getenv("TWITTER_ACCESS_TOKEN")
        self.access_token_secret = access_token_secret or os.getenv(
            "TWITTER_ACCESS_TOKEN_SECRET"
        )

        if not all(
            [self.api_key, self.api_secret, self.access_token, self.access_token_secret]
        ):
            raise ValueError(
                "Twitter API credentials missing. Set environment variables."
            )

        self.client_v2 = tweepy.Client(
            consumer_key=self.api_key,
            consumer_secret=self.api_secret,
            access_token=self.access_token,
            access_token_secret=self.access_token_secret,
        )
        self.auth = tweepy.OAuth1UserHandler(
            self.api_key, self.api_secret, self.access_token, self.access_token_secret
        )
        self.api_v1 = tweepy.API(self.auth)

    def upload_media_from_url(self, url: str, retries: int = 3) -> str | None:
        filename = "temp_image.jpg"
        for attempt in range(retries):
            try:
                headers = get_random_headers()
                resp = requests.get(url, stream=True, timeout=10, headers=headers)
                if resp.status_code != 200:
                    print(
                        f"[WARNING] Attempt {attempt + 1}: Failed download (status {resp.status_code})"
                    )
                    time.sleep(2)
                    continue

                with open(filename, "wb") as f:
                    for chunk in resp.iter_content(chunk_size=8192):
                        f.write(chunk)

                media = self.api_v1.media_upload(filename)
                os.remove(filename)
                media_id = str(media.media_id)  # ✅ string
                print(f"[INFO] Media uploaded with ID {media_id}")
                # Wait a bit for processing
                time.sleep(2)
                return media_id

            except Exception as e:
                print(f"[WARNING] Attempt {attempt + 1}: upload error: {e}")
                if os.path.exists(filename):
                    os.remove(filename)
                time.sleep(2)

        return None

    def post_tweet(self, text, media_ids=None, in_reply_to=None):
        """
        Post a tweet (or reply) to X/Twitter.

        Args:
            text (str): The tweet content (max 280 chars).
            media_ids (list, optional): List of media ID strings from upload_media().
            in_reply_to (str/int, optional): ID of the tweet to reply to.

        Returns:
            str: The ID of the posted tweet, or None if failed.
        """
        if not text or len(text) > 280:
            print(f"[ERROR] Tweet text invalid (length: {len(text)})")
            return None

        try:
            # --- 1. Prepare the payload for API v2 ---
            payload = {"text": text}

            # Add media if provided
            if media_ids:
                payload["media"] = {"media_ids": [str(mid) for mid in media_ids]}

            # Add reply threading if provided
            if in_reply_to:
                payload["reply"] = {"in_reply_to_tweet_id": str(in_reply_to)}

            # --- 2. Make the API request ---
            url = "https://api.twitter.com/2/tweets"
            response = requests.post(
                url,
                json=payload,
                auth=OAuth1(
                    self.api_key,
                    self.api_secret,
                    self.access_token,
                    self.access_token_secret,
                ),
            )

            # --- 3. Handle response ---
            if response.status_code in (200, 201):
                tweet_id = response.json().get("data", {}).get("id")
                print(f"[SUCCESS] Tweet posted. ID: {tweet_id}")
                return tweet_id
            else:
                error_msg = response.json().get("detail", response.text)
                print(f"[ERROR] Twitter API error {response.status_code}: {error_msg}")
                return None

        except Exception as e:
            print(f"[ERROR] Failed to post tweet: {e}")
            return None

    def post_thread(self, tweets: list, media_ids: list = None) -> list:
        """
        Post a thread (multiple tweets in reply to each other).
        Returns a list of tweet IDs.
        """
        tweet_ids = []
        previous_id = None
        for i, text in enumerate(tweets):
            if len(text) > 280:
                text = text[:277] + "..."
            media = media_ids if i == 0 and media_ids else None
            tweet_id = self.post_tweet(text, media_ids=media, in_reply_to=previous_id)
            tweet_ids.append(tweet_id)
            previous_id = tweet_id
        return tweet_ids

    def reply(self, text: str, in_reply_to: str, media_ids: list = None) -> str:
        """Convenience method to reply to a tweet."""
        return self.post_tweet(text, media_ids=media_ids, in_reply_to=in_reply_to)
