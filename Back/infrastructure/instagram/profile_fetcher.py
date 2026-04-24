"""
infrastructure/instagram/profile_fetcher.py
=============================================
Extrae información del perfil de Instagram.
Actualizado para soportar el modelo de dominio v2.1.
"""

from __future__ import annotations
import logging
from datetime import datetime, timezone
from typing import Optional, Tuple
import requests
from tenacity import (
    retry, stop_after_attempt, wait_exponential,
    retry_if_exception_type, before_sleep_log
)
from domain.models import Profile, DeclaredContext

logger = logging.getLogger(__name__)

def _iso(ts_unix: Optional[int]) -> str:
    if not ts_unix: return ""
    try:
        return datetime.fromtimestamp(ts_unix, tz=timezone.utc).isoformat()
    except:
        return ""

@retry(
    stop=stop_after_attempt(4),
    wait=wait_exponential(multiplier=2, min=5, max=60),
    retry=retry_if_exception_type((requests.exceptions.RequestException,)),
    before_sleep=before_sleep_log(logger, logging.WARNING),
    reraise=True,
)
def _get_profile_json(session: requests.Session, username: str) -> dict:
    url = f"https://www.instagram.com/{username}/"
    params = {"__a": "1", "__d": "dis"}
    extra_headers = {
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "X-Requested-With": "XMLHttpRequest",
    }
    resp = session.get(url, params=params, headers=extra_headers, timeout=20)
    if resp.status_code not in (200, 201):
        resp.raise_for_status()
    try:
        return resp.json()
    except:
        # Fallback a búsqueda regex si el response es HTML con JSON embebido
        import re, json
        m = re.search(r'window\.__additionalDataLoaded\s*\(\s*["\']feed["\']\s*,\s*(\{.+?\})\s*\)', resp.text, re.S)
        if m: return json.loads(m.group(1))
        raise ValueError("No se pudo extraer JSON del perfil")

def _get_profile_via_web_info(session: requests.Session, username: str) -> dict:
    url = "https://www.instagram.com/api/v1/users/web_profile_info/"
    params = {"username": username}
    resp = session.get(url, params=params, timeout=20)
    resp.raise_for_status()
    return resp.json()

def fetch_profile(session: requests.Session, username: str) -> Tuple[Profile, str, str, list]:
    raw = {}
    try:
        raw = _get_profile_json(session, username)
    except:
        raw = _get_profile_via_web_info(session, username)

    if "data" in raw and "user" in raw["data"]:
        user_data = raw["data"]["user"]
    elif "graphql" in raw and "user" in raw["graphql"]:
        user_data = raw["graphql"]["user"]
    else:
        user_data = raw.get("user", raw)

    user_id = str(user_data.get("id", ""))
    
    # Mapeo al nuevo modelo Profile v2.1
    profile = Profile(
        username=username,
        full_name=user_data.get("full_name", ""),
        is_private=user_data.get("is_private", False),
        is_verified=user_data.get("is_verified", False),
        is_business=user_data.get("is_business_account", False),
        followers_count=user_data.get("edge_followed_by", {}).get("count", 0),
        following_count=user_data.get("edge_follow", {}).get("count", 0),
        posts_count=user_data.get("edge_owner_to_timeline_media", {}).get("count", 0),
        bio=user_data.get("biography", ""),
        external_url=user_data.get("external_url", "") or "",
        profile_pic_url=user_data.get("profile_pic_url", ""),
        profile_pic_hd_url=user_data.get("profile_pic_url_hd", ""),
        declared_context=DeclaredContext() # Se llenará después con Gemini
    )

    timeline = user_data.get("edge_owner_to_timeline_media", {})
    end_cursor = timeline.get("page_info", {}).get("end_cursor", "")
    edges = timeline.get("edges", [])

    return profile, user_id, end_cursor, edges
