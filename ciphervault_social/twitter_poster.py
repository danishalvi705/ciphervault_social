"""
CipherVault Social — X (Twitter) Poster
Uploads the rendered short as a video tweet via Tweepy.

Note: X's free API tier is read-only. Posting media requires at least the
paid Basic tier (OAuth1 user-context credentials below).

Rate limiting is NOT done here — the DO side checks the daily cap and only
fires the webhook that reaches this service if a post is allowed. This
service posts unconditionally on every call it receives.
"""

from __future__ import annotations
import os
import tweepy


def _client_v1() -> tweepy.API:
    auth = tweepy.OAuth1UserHandler(
        os.environ["X_API_KEY"],
        os.environ["X_API_SECRET"],
        os.environ["X_ACCESS_TOKEN"],
        os.environ["X_ACCESS_SECRET"],
    )
    return tweepy.API(auth)


def _client_v2() -> tweepy.Client:
    return tweepy.Client(
        consumer_key=os.environ["X_API_KEY"],
        consumer_secret=os.environ["X_API_SECRET"],
        access_token=os.environ["X_ACCESS_TOKEN"],
        access_token_secret=os.environ["X_ACCESS_SECRET"],
    )


def post_video(video_path: str, caption: str, signal_id: str = "") -> bool:
    media = _client_v1().media_upload(filename=video_path, media_category="tweet_video")
    _client_v2().create_tweet(text=caption, media_ids=[media.media_id])
    return True
