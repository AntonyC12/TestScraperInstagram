"""
infrastructure/instagram/profile_fetcher.py
=============================================
Extrae información completa del perfil de una cuenta pública de Instagram
usando el endpoint web: GET /{username}/?__a=1&__d=dis

Retorna un objeto Profile y el end_cursor para paginación de posts.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional

import requests
from tenacity import (
    retry, stop_after_attempt, wait_exponential,
    retry_if_exception_type, before_sleep_log
)

from domain.models import Profile

logger = logging.getLogger(__name__)


def _iso(ts_unix: Optional[int]) -> str:
    if not ts_unix:
        return ""
    try:
        return datetime.fromtimestamp(ts_unix, tz=timezone.utc).isoformat()
    except Exception:
        return ""


@retry(
    stop=stop_after_attempt(4),
    wait=wait_exponential(multiplier=2, min=5, max=60),
    retry=retry_if_exception_type((requests.exceptions.RequestException,)),
    before_sleep=before_sleep_log(logger, logging.WARNING),
    reraise=True,
)
def _get_profile_json(session: requests.Session, username: str) -> dict:
    """Petición al endpoint ?__a=1 con retry automático en fallos de red."""
    url = f"https://www.instagram.com/{username}/"
    params = {"__a": "1", "__d": "dis"}

    # Forzar JSON en la respuesta
    extra_headers = {
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "X-Requested-With": "XMLHttpRequest",
    }

    resp = session.get(url, params=params, headers=extra_headers, timeout=20)
    logger.info(f"📡 GET {url} → HTTP {resp.status_code}")

    if resp.status_code == 401:
        raise PermissionError("❌ 401 No autenticado — verifica las cookies de sessionid")
    if resp.status_code == 302:
        raise PermissionError("❌ 302 Redirigido a login — las cookies expiraron")
    if resp.status_code == 404:
        raise ValueError(f"❌ 404 Cuenta no encontrada: @{username}")
    if resp.status_code == 429:
        logger.warning("⚠️  429 Rate limit — tenacity reintentará con backoff")
        resp.raise_for_status()
    # 201 también es éxito en algunas versiones del endpoint de IG
    if resp.status_code not in (200, 201):
        resp.raise_for_status()

    # Intentar parsear JSON directamente
    content_type = resp.headers.get("Content-Type", "")
    if "json" in content_type or resp.text.strip().startswith("{"):
        try:
            return resp.json()
        except Exception:
            pass

    # IG a veces entrega HTML con un bloque JSON embebido
    # Buscar el objeto JSON principal en el HTML
    import re as _re
    text = resp.text

    # Patrón 1: window.__additionalDataLoaded('feed',{...})
    m = _re.search(r'window\.__additionalDataLoaded\s*\(\s*["\']feed["\']\s*,\s*(\{.+?\})\s*\)', text, _re.S)
    if m:
        try:
            import json as _json
            return _json.loads(m.group(1))
        except Exception:
            pass

    # Patrón 2: JSON en línea en el HTML (IG web moderno devuelve JSON puro a veces)
    m2 = _re.search(r'^\s*(\{"graphql":.+)', text, _re.S | _re.M)
    if m2:
        try:
            import json as _json
            return _json.loads(m2.group(1))
        except Exception:
            pass

    # Patrón 3: {"data":{"user":{...}}}
    m3 = _re.search(r'(\{"data":\{"user":.+)', text, _re.S)
    if m3:
        try:
            import json as _json
            return _json.loads(m3.group(1))
        except Exception:
            pass

    raise ValueError(
        f"❌ Respuesta no-JSON del endpoint de perfil. "
        f"Status={resp.status_code}, Content-Type={content_type}. "
        f"Primeros 500 chars: {text[:500]!r}"
    )


def _get_profile_via_web_info(session: requests.Session, username: str) -> dict:
    """
    Endpoint alternativo más moderno de Instagram web.
    GET /api/v1/users/web_profile_info/?username=<username>
    Requiere x-ig-app-id en los headers (ya configurado en la session).
    """
    url = "https://www.instagram.com/api/v1/users/web_profile_info/"
    params = {"username": username}
    extra_headers = {
        "Accept": "*/*",
        "Referer": f"https://www.instagram.com/{username}/",
    }
    resp = session.get(url, params=params, headers=extra_headers, timeout=20)
    logger.info(f"📡 GET web_profile_info/{username} → HTTP {resp.status_code}")

    if resp.status_code == 404:
        raise ValueError(f"❌ 404 Cuenta no encontrada: @{username}")
    if resp.status_code == 429:
        logger.warning("⚠️  429 Rate limit en web_profile_info")
        resp.raise_for_status()
    if resp.status_code not in (200, 201):
        resp.raise_for_status()

    try:
        return resp.json()
    except Exception as exc:
        raise ValueError(f"❌ web_profile_info tampoco retornó JSON. Status={resp.status_code}") from exc


def fetch_profile(
    session: requests.Session, username: str
) -> tuple["Profile", str, str, list]:
    """
    Extrae el perfil completo del usuario.

    Returns:
        (Profile, user_id, end_cursor, initial_edges)
        - user_id       : ID numérico de Instagram (para paginación de posts)
        - end_cursor    : cursor para obtener más posts con la GraphQL API
        - initial_edges : primera página de posts (ya incluida, sin request extra)
    """
    # ── Intentar endpoint primario, luego fallback ───────────────────────────
    raw: dict = {}
    try:
        raw = _get_profile_json(session, username)
    except ValueError as exc:
        logger.warning(f"⚠️  Endpoint primario falló: {exc}")
        logger.info("🔄 Intentando endpoint alternativo: web_profile_info...")
        raw = _get_profile_via_web_info(session, username)

    # El endpoint ?__a=1 puede retornar:
    #   { data: { user: {...} } }   ← web_profile_info también usa este formato
    #   { graphql: { user: {...} } }
    #   directamente el objeto user
    user_data: dict = {}
    if "data" in raw and "user" in raw.get("data", {}):
        user_data = raw["data"]["user"]
    elif "graphql" in raw and "user" in raw.get("graphql", {}):
        user_data = raw["graphql"]["user"]
    else:
        user_data = raw.get("user", raw)

    if not user_data:
        raise ValueError(f"No se encontraron datos de usuario para @{username}")

    logger.info(f"✅ Perfil obtenido: @{username} — {user_data.get('full_name', '')}")

    # ── Datos del perfil ──────────────────────────────────────────────────────
    user_id   = str(user_data.get("id", ""))
    full_name = user_data.get("full_name", "")
    biography = user_data.get("biography", "")
    is_private = user_data.get("is_private", False)
    is_verified = user_data.get("is_verified", False)
    is_business = user_data.get("is_business_account", user_data.get("is_business", False))
    category    = user_data.get("category_name", user_data.get("business_category_name", ""))

    # Foto de perfil
    profile_pic_url    = user_data.get("profile_pic_url", "")
    profile_pic_hd_url = user_data.get("profile_pic_url_hd", profile_pic_url)

    # Enlace externo
    external_url = user_data.get("external_url", "") or ""
    external_url_linkshimmed = user_data.get("external_url_linkshimmed", "") or ""

    # Contadores
    followers_count = (
        user_data.get("edge_followed_by", {}).get("count", 0)
        or user_data.get("follower_count", 0)
    )
    following_count = (
        user_data.get("edge_follow", {}).get("count", 0)
        or user_data.get("following_count", 0)
    )
    posts_count = (
        user_data.get("edge_owner_to_timeline_media", {}).get("count", 0)
        or user_data.get("media_count", 0)
    )

    # ── Cursor para paginación y primera página de posts ─────────────────────
    timeline = (
        user_data.get("edge_owner_to_timeline_media", {})
        or user_data.get("edge_media_to_timeline_media", {})
    )
    page_info     = timeline.get("page_info", {})
    end_cursor    = page_info.get("end_cursor", "")
    edges         = timeline.get("edges", [])   # Primera página — sin request extra
    initial_edges = edges

    # ── Post más antiguo visible (para inferir antigüedad) ────────────────────
    oldest_ts = ""
    if edges:
        timestamps = [
            e.get("node", {}).get("taken_at_timestamp", 0)
            for e in edges
            if e.get("node", {}).get("taken_at_timestamp")
        ]
        if timestamps:
            oldest_ts = _iso(min(timestamps))
            newest_ts = _iso(max(timestamps))
        else:
            newest_ts = ""
    else:
        newest_ts = ""

    # Aproximar creación de cuenta basado en el primer post visible
    account_created_approx = (
        f"Post más antiguo visible: {oldest_ts}" if oldest_ts
        else "No determinable con los datos obtenidos"
    )

    profile = Profile(
        username=username,
        full_name=full_name,
        biography=biography,
        profile_pic_url=profile_pic_url,
        profile_pic_hd_url=profile_pic_hd_url,
        external_url=external_url,
        external_url_linkshimmed=external_url_linkshimmed,
        is_private=is_private,
        is_verified=is_verified,
        is_business=is_business,
        category=category,
        followers_count=followers_count,
        following_count=following_count,
        posts_count=posts_count,
        user_id=user_id,
        account_created_approx=account_created_approx,
        oldest_post_timestamp=oldest_ts,
    )

    return profile, user_id, end_cursor, initial_edges
