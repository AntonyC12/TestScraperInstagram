"""
infrastructure/instagram/comments_fetcher.py
=============================================
Extrae comentarios de una publicación usando la API web de Instagram.

Endpoint: GET /api/v1/media/{media_id}/comments/
  - Retorna JSON con comentarios paginados
  - Soporta threading (respuestas a comentarios)
"""

from __future__ import annotations

import logging
import random
import time
from datetime import datetime, timezone

import requests
from tenacity import (
    retry, stop_after_attempt, wait_exponential,
    retry_if_exception_type, before_sleep_log
)

from domain.models import Comment

logger = logging.getLogger(__name__)

_COMMENTS_URL = "https://www.instagram.com/api/v1/media/{media_id}/comments/"


def _unix_to_iso(ts: int) -> str:
    if not ts:
        return ""
    try:
        return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()
    except Exception:
        return ""


def _parse_comment(raw: dict, owner_username: str) -> Comment:
    """Convierte un dict de comentario en un objeto Comment."""
    author = raw.get("user", {})
    username = (
        author.get("username", "")
        or raw.get("username", "")
    )
    ts_unix = raw.get("created_at", raw.get("created_at_utc", 0))

    return Comment(
        id=str(raw.get("pk", raw.get("id", ""))),
        username=username,
        text=raw.get("text", ""),
        timestamp=_unix_to_iso(ts_unix),
        timestamp_unix=ts_unix,
        likes_count=raw.get("comment_like_count", raw.get("likes_count", 0)),
        is_owner_comment=(username.lower() == owner_username.lower()),
    )


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=2, min=5, max=45),
    retry=retry_if_exception_type((requests.exceptions.RequestException,)),
    before_sleep=before_sleep_log(logger, logging.WARNING),
    reraise=False,   # En comentarios no lanzamos — retornamos lista vacía si falla
)
def _fetch_comments_raw(
    session: requests.Session,
    media_id: str,
    limit: int = 10,
) -> list[dict]:
    """Obtiene los comentarios crudos del endpoint de la API."""
    url = _COMMENTS_URL.format(media_id=media_id)
    params = {
        "can_support_threading": "true",
        "permalink_enabled":     "false",
    }

    resp = session.get(url, params=params, timeout=20)
    logger.debug(f"💬 GET comentarios {media_id} → HTTP {resp.status_code}")

    if resp.status_code == 404:
        logger.debug(f"🔇 Post {media_id}: comentarios desactivados o no disponibles")
        return []
    if resp.status_code == 429:
        logger.warning(f"⚠️  429 Rate limit en comentarios de {media_id}")
        resp.raise_for_status()
    if resp.status_code not in (200, 201):
        logger.warning(f"⚠️  HTTP {resp.status_code} en comentarios de {media_id}")
        return []

    try:
        data = resp.json()
    except Exception:
        return []

    # El endpoint retorna { comments: [...] } o { data: { comments: [...] } }
    raw_comments: list[dict] = []
    if "comments" in data:
        raw_comments = data["comments"]
    elif "data" in data and "comments" in data["data"]:
        raw_comments = data["data"]["comments"]

    return raw_comments[:limit]


def fetch_comments(
    session: requests.Session,
    media_id: str,
    owner_username: str,
    limit: int = 10,
) -> list[Comment]:
    """
    Extrae hasta `limit` comentarios de una publicación.

    Args:
        media_id: ID numérico del post de Instagram (campo `id` del post)
        owner_username: Username del dueño del perfil (para marcar is_owner_comment)
        limit: Máximo de comentarios a extraer (default 10)

    Returns:
        Lista de objetos Comment
    """
    try:
        raw_list = _fetch_comments_raw(session, media_id, limit)
    except Exception as exc:
        logger.warning(f"⚠️  No se pudieron obtener comentarios de {media_id}: {exc}")
        return []

    comments: list[Comment] = []
    for raw in raw_list:
        try:
            comments.append(_parse_comment(raw, owner_username))
        except Exception as exc:
            logger.debug(f"Error parseando comentario: {exc}")

    return comments


def fetch_all_post_comments(
    session: requests.Session,
    posts: list,  # list[Post]
    owner_username: str,
    limit_per_post: int = 10,
) -> None:
    """
    Enriquece cada Post de la lista con sus comentarios (modifica in-place).

    Args:
        posts: Lista de objetos Post (se modifican directamente)
        owner_username: Para detectar comentarios del dueño del perfil
        limit_per_post: Máx. comentarios por post
    """
    total_posts = len(posts)
    for i, post in enumerate(posts, 1):
        logger.info(f"💬 [{i}/{total_posts}] Obteniendo comentarios de {post.shortcode}...")

        if post.comments_count == 0:
            logger.debug(f"    → Post sin comentarios, saltando")
            continue

        comments = fetch_comments(session, post.id, owner_username, limit_per_post)
        post.comments         = comments
        post.comments_fetched = len(comments)

        logger.info(f"    → {len(comments)} comentarios obtenidos")

        # Delay aleatorio entre posts para no saturar la API
        if i < total_posts:
            delay = random.uniform(1.5, 3.5)
            time.sleep(delay)
