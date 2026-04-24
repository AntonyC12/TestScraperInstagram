"""
infrastructure/instagram/http_client.py
========================================
Construye y retorna un requests.Session completamente configurado
para hacer peticiones a los endpoints web de Instagram con cookies reales.
"""

from __future__ import annotations

import logging
import random

import requests
from fake_useragent import UserAgent

logger = logging.getLogger(__name__)

# User-Agent fijo de Chrome como fallback si fake-useragent falla
_CHROME_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)

# Headers base que Instagram espera en cualquier request web autenticado
_BASE_HEADERS = {
    "Accept":             "*/*, application/json",
    "Accept-Language":    "es-ES,es;q=0.9,en;q=0.8",
    "Accept-Encoding":    "gzip, deflate",
    "Connection":         "keep-alive",
    "Origin":             "https://www.instagram.com",
    "Referer":            "https://www.instagram.com/",
    "Sec-Fetch-Dest":     "empty",
    "Sec-Fetch-Mode":     "cors",
    "Sec-Fetch-Site":     "same-origin",
    "X-Requested-With":   "XMLHttpRequest",
    "X-IG-WWW-Claim":     "0",
    # Indica que es una petición AJAX de la web (no de la app móvil)
    "X-Asbd-Id":          "198387",
}


def build_session(cookies: dict, app_id: str) -> requests.Session:
    """
    Construye un requests.Session con:
      - Todas las cookies de identidad inyectadas
      - Headers que imitan al navegador Chrome
      - x-ig-app-id y x-csrftoken configurados
      - User-Agent rotado aleatoriamente

    Args:
        cookies: dict con todas las cookies (sessionid, mid, ig_did, etc.)
        app_id: El x-ig-app-id extraído por playwright o el valor de fallback

    Returns:
        requests.Session lista para hacer peticiones a Instagram
    """
    session = requests.Session()

    # ── 1. Inyectar cookies ──────────────────────────────────────────────────
    for name, value in cookies.items():
        if value:
            session.cookies.set(name, str(value), domain=".instagram.com", path="/")

    csrf_token = cookies.get("csrftoken", "")

    # ── 2. Configurar User-Agent ─────────────────────────────────────────────
    try:
        # Desactivamos la carga de datos externos para evitar el warning de fallback
        ua = UserAgent(use_external_data=False)
        user_agent = ua.chrome
    except Exception:
        user_agent = _CHROME_UA

    logger.debug(f"🌐 User-Agent: {user_agent[:60]}...")

    # ── 3. Configurar headers ────────────────────────────────────────────────
    headers = dict(_BASE_HEADERS)
    headers["User-Agent"]      = user_agent
    headers["X-IG-App-ID"]     = str(app_id)
    if csrf_token:
        headers["X-CSRFToken"] = csrf_token

    session.headers.update(headers)

    logger.info(f"🔧 Session HTTP construida — app_id={app_id}, cookies={len(cookies)}")
    return session


def random_delay(min_s: float = 1.5, max_s: float = 4.0) -> None:
    """Pausa aleatoria para simular comportamiento humano entre requests."""
    import time
    delay = random.uniform(min_s, max_s)
    logger.debug(f"⏳ Delay {delay:.1f}s")
    time.sleep(delay)
