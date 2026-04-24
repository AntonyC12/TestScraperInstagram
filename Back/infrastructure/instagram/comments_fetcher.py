"""
infrastructure/instagram/comments_fetcher.py
=============================================
Extrae comentarios de publicaciones de Instagram.
Actualizado para el modelo Comment v2.1.
"""

from __future__ import annotations
import logging
import random
import time
from datetime import datetime, timezone
import requests
from domain.models import Comment, Post

logger = logging.getLogger(__name__)

def _unix_to_iso(ts: int) -> str:
    if not ts: return ""
    try:
        return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()
    except: return ""

def _parse_comment(raw: dict, owner_username: str) -> Comment:
    author = raw.get("user", {})
    username = author.get("username", "") or raw.get("username", "")
    ts_unix = raw.get("created_at", 0)

    return Comment(
        comment_id=str(raw.get("pk", "")),
        username=username,
        text=raw.get("text", ""),
        timestamp=_unix_to_iso(ts_unix),
        is_owner_comment=(username.lower() == owner_username.lower()),
        sentiment=None # Se llenará en el analyzer
    )

def fetch_comments(session: requests.Session, media_id: str, owner_username: str, limit: int = 10) -> list[Comment]:
    url = f"https://www.instagram.com/api/v1/media/{media_id}/comments/"
    try:
        resp = session.get(url, timeout=20)
        resp.raise_for_status()
        data = resp.json()
        raw_list = data.get("comments", [])[:limit]
        return [_parse_comment(raw, owner_username) for raw in raw_list]
    except Exception as e:
        logger.warning(f"Error obteniendo comentarios de {media_id}: {e}")
        return []

def fetch_all_post_comments(session: requests.Session, posts: list[Post], owner_username: str, limit_per_post: int = 10) -> None:
    for i, post in enumerate(posts, 1):
        if post.engagement["comments_count"] > 0:
            comments = fetch_comments(session, post.post_id, owner_username, limit_per_post)
            post.comments_sample = comments
            if i < len(posts):
                time.sleep(random.uniform(1, 3))
