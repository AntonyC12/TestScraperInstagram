"""
infrastructure/instagram/posts_fetcher.py
==========================================
Extrae publicaciones de una cuenta pública usando la API web de Instagram.

Estrategia de paginación:
  - Primera página: viene en la respuesta del perfil (?__a=1)
  - Páginas siguientes: POST /graphql/query con query_hash y cursor
  - Delays aleatorios entre páginas para evitar rate limiting
"""

from __future__ import annotations

import json
import logging
import random
import time
from datetime import datetime, timezone
from typing import Optional

import requests
from tenacity import (
    retry, stop_after_attempt, wait_exponential,
    retry_if_exception_type, before_sleep_log
)

from domain.models import Post
from domain.analyzers import extract_hashtags, extract_emojis

logger = logging.getLogger(__name__)

# Query hash para obtener posts del timeline de usuario (web app de IG)
# Este hash es estable pero puede cambiar con actualizaciones de IG
_POSTS_QUERY_HASH = "e769aa130647d2354c40ea6a439bfc08"

# URL de la GraphQL API de Instagram web
_GRAPHQL_URL = "https://www.instagram.com/graphql/query/"


def _unix_to_iso(ts: int) -> str:
    if not ts:
        return ""
    try:
        return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()
    except Exception:
        return ""


def _parse_post_node(node: dict) -> Post:
    """Convierte un nodo de GraphQL en un objeto Post."""
    ts_unix = node.get("taken_at_timestamp", 0)
    caption_edges = node.get("edge_media_to_caption", {}).get("edges", [])
    caption = caption_edges[0].get("node", {}).get("text", "") if caption_edges else ""

    # Tipo de contenido
    typename = node.get("__typename", "GraphImage")

    # Comentarios count
    comments_count = (
        node.get("edge_media_to_comment", {}).get("count", 0)
        or node.get("edge_media_preview_comment", {}).get("count", 0)
    )

    # Likes count
    likes_count = (
        node.get("edge_media_preview_like", {}).get("count", 0)
        or node.get("edge_liked_by", {}).get("count", 0)
    )

    # Localización
    location = node.get("location")
    location_name = None
    location_id   = None
    if location:
        location_name = location.get("name")
        location_id   = str(location.get("id", "")) or None

    return Post(
        id=str(node.get("id", "")),
        shortcode=node.get("shortcode", ""),
        timestamp=_unix_to_iso(ts_unix),
        timestamp_unix=ts_unix,
        type=typename,
        caption=caption,
        hashtags=extract_hashtags(caption),
        emojis=extract_emojis(caption),
        likes_count=likes_count,
        comments_count=comments_count,
        display_url=node.get("display_url", ""),
        is_video=node.get("is_video", False),
        video_view_count=node.get("video_view_count"),
        location=location_name,
        location_id=location_id,
    )


def _parse_edges(edges: list[dict]) -> list[Post]:
    posts: list[Post] = []
    for edge in edges:
        node = edge.get("node", {})
        if node:
            try:
                posts.append(_parse_post_node(node))
            except Exception as exc:
                logger.warning(f"⚠️  Error parseando post {node.get('shortcode')}: {exc}")
    return posts


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=2, min=8, max=60),
    retry=retry_if_exception_type((requests.exceptions.RequestException,)),
    before_sleep=before_sleep_log(logger, logging.WARNING),
    reraise=True,
)
def _fetch_page_rest(
    session: requests.Session,
    user_id: str,
    max_id: str = "",
) -> tuple[list[Post], str, bool]:
    """
    Obtiene una página de posts via REST API (más estable que GraphQL).
    """
    url = f"https://www.instagram.com/api/v1/feed/user/{user_id}/"
    params = {"count": 12}
    if max_id:
        params["max_id"] = max_id

    resp = session.get(url, params=params, timeout=25)
    logger.info(f"📡 REST posts → HTTP {resp.status_code} (max_id: {max_id[:20] if max_id else 'inicio'}...)")

    if resp.status_code == 429:
        resp.raise_for_status()
    if resp.status_code not in (200, 201):
        resp.raise_for_status()

    try:
        data = resp.json()
    except Exception:
        raise ValueError("Respuesta no-JSON en REST posts")

    items = data.get("items", [])
    next_max_id = data.get("next_max_id", "")
    has_next = data.get("more_available", False)

    posts: list[Post] = []
    for item in items:
        try:
            # El formato REST es ligeramente distinto al de GraphQL
            ts_unix = item.get("taken_at", 0)
            caption_dict = item.get("caption") or {}
            caption = caption_dict.get("text", "")
            
            # Tipo
            media_type = item.get("media_type")
            typename = "GraphImage" if media_type == 1 else "GraphVideo" if media_type == 2 else "GraphSidecar"

            posts.append(Post(
                id=str(item.get("pk", "")),
                shortcode=item.get("code", ""),
                timestamp=_unix_to_iso(ts_unix),
                timestamp_unix=ts_unix,
                type=typename,
                caption=caption,
                hashtags=extract_hashtags(caption),
                emojis=extract_emojis(caption),
                likes_count=item.get("like_count", 0),
                comments_count=item.get("comment_count", 0),
                display_url=item.get("image_versions2", {}).get("candidates", [{}])[0].get("url", ""),
                is_video=(media_type == 2),
                video_view_count=item.get("view_count"),
                location=item.get("location", {}).get("name"),
            ))
        except Exception as exc:
            logger.debug(f"Error parseando item REST: {exc}")

    return posts, next_max_id, has_next


def fetch_posts(
    session: requests.Session,
    user_id: str,
    initial_edges: list[dict],
    initial_cursor: str,
    limit: int = 20,
) -> list[Post]:
    """
    Extrae hasta `limit` posts.
    """
    all_posts: list[Post] = []

    # 1. Intentar con initial_edges si existen
    if initial_edges:
        first_page = _parse_edges(initial_edges)
        all_posts.extend(first_page)
        logger.info(f"📄 Primera página (del perfil): {len(first_page)} posts")
        max_id   = initial_cursor
        has_next = bool(max_id)
    else:
        # 2. Si no, usar REST API
        logger.info("📄 Obteniendo posts via REST API...")
        try:
            first_page, max_id, has_next = _fetch_page_rest(session, user_id, "")
            all_posts.extend(first_page)
            logger.info(f"📄 Primera página (REST): {len(first_page)} posts")
        except Exception as exc:
            logger.error(f"❌ Falló obtención de posts via REST: {exc}")
            return []

    # Páginas adicionales
    while has_next and len(all_posts) < limit:
        time.sleep(random.uniform(2.0, 5.0))
        try:
            new_posts, max_id, has_next = _fetch_page_rest(session, user_id, max_id)
            if not new_posts: break
            all_posts.extend(new_posts)
            logger.info(f"📄 Página adicional: {len(new_posts)} posts (total: {len(all_posts)})")
        except Exception as exc:
            logger.error(f"❌ Error en página adicional: {exc}")
            break

    return all_posts[:limit]
