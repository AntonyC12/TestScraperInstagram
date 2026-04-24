"""
infrastructure/auth/cookie_session.py
======================================
Usa Playwright para:
  1. Inyectar las cookies de identidad en el navegador.
  2. Navegar al perfil objetivo y verificar que la sesión sea válida.
  3. Extraer el x-ig-app-id dinámico del HTML/scripts de Instagram.
  4. Opcionalmente guardar las cookies actualizadas en sessions/cookies.json.

NUNCA usa username/password directamente — autenticación 100% via cookies.
"""

from __future__ import annotations

import json
import logging
import re
import time
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# Regex para extraer app_id de los scripts inline de IG
_APP_ID_RE  = re.compile(r'"APP_ID"\s*:\s*"(\d+)"')
_APP_ID_RE2 = re.compile(r'appId["\s:=]+["\'](\d+)["\']')
_APP_ID_RE3 = re.compile(r'"X-IG-App-ID"\s*:\s*"(\d+)"')

FALLBACK_APP_ID = "936619743392459"


def _extract_app_id_from_html(html: str) -> str:
    """Intenta extraer el x-ig-app-id del HTML de la página."""
    for pattern in (_APP_ID_RE, _APP_ID_RE2, _APP_ID_RE3):
        match = pattern.search(html)
        if match:
            return match.group(1)
    return FALLBACK_APP_ID


def _save_cookies(cookies_path: Path, cookies: dict) -> None:
    """Persiste las cookies actualizadas en sessions/cookies.json."""
    try:
        cookies_path.parent.mkdir(parents=True, exist_ok=True)
        existing: dict = {}
        if cookies_path.exists():
            try:
                existing = json.loads(cookies_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                pass
        existing.update(cookies)
        cookies_path.write_text(
            json.dumps(existing, indent=2, ensure_ascii=False),
            encoding="utf-8"
        )
        logger.info(f"💾 Cookies guardadas en {cookies_path}")
    except Exception as exc:
        logger.warning(f"No se pudieron guardar las cookies: {exc}")


def get_session_data(
    target_username: str,
    cookies_dict: dict,
    app_id_override: str = "",
    headless: bool = True,
    cookies_path: Optional[Path] = None,
    save_cookies: bool = True,
) -> dict:
    """
    Lanza Playwright, inyecta las cookies y navega al perfil objetivo.

    Retorna:
        {
            "cookies": {...},   # Cookies actualizadas (pueden incluir nuevas del navegador)
            "app_id": "...",    # x-ig-app-id para headers de API
            "is_logged_in": bool,
            "is_private": bool,
        }
    """
    from playwright.sync_api import sync_playwright, TimeoutError as PWTimeoutError

    result = {
        "cookies":      cookies_dict.copy(),
        "app_id":       app_id_override or FALLBACK_APP_ID,
        "is_logged_in": False,
        "is_private":   False,
    }

    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(
                headless=headless,
                args=[
                    "--no-sandbox",
                    "--disable-blink-features=AutomationControlled",
                    "--disable-dev-shm-usage",
                ]
            )
            context = browser.new_context(
                viewport={"width": 1366, "height": 768},
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0.0.0 Safari/537.36"
                ),
                locale="es-ES",
                timezone_id="America/Bogota",
            )

            # ── Inyectar cookies antes de navegar ────────────────────────────
            pw_cookies: list[dict] = []
            for name, value in cookies_dict.items():
                if value:
                    pw_cookies.append({
                        "name":   name,
                        "value":  str(value),
                        "domain": ".instagram.com",
                        "path":   "/",
                        "secure": True,
                        "httpOnly": name in ("sessionid", "csrftoken"),
                        "sameSite": "Lax",
                    })

            if pw_cookies:
                context.add_cookies(pw_cookies)
                logger.info(f"🍪 {len(pw_cookies)} cookies inyectadas en playwright")

            page = context.new_page()

            # ── Anti-bot: ocultar webdriver flag ─────────────────────────────
            page.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
                Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
            """)

            target_url = f"https://www.instagram.com/{target_username}/"
            logger.info(f"🌐 Navegando a {target_url}")

            try:
                page.goto(target_url, wait_until="domcontentloaded", timeout=30_000)
                time.sleep(3)   # Pausa humana para que IG cargue completamente
            except PWTimeoutError:
                logger.warning("⚠️  Timeout en navegación, continuando con datos parciales")

            current_url = page.url
            logger.info(f"📍 URL final: {current_url}")

            # ── Verificar si estamos logueados ───────────────────────────────
            if "accounts/login" in current_url or "challenge" in current_url:
                logger.warning("⚠️  Redirigido a login — las cookies pueden haber expirado")
                result["is_logged_in"] = False
            else:
                result["is_logged_in"] = True
                logger.info("✅ Sesión válida — logueado correctamente")

            # ── Extraer app_id del contenido de la página ────────────────────
            if not app_id_override:
                html = page.content()
                extracted_id = _extract_app_id_from_html(html)
                if extracted_id != FALLBACK_APP_ID:
                    logger.info(f"🔑 x-ig-app-id extraído: {extracted_id}")
                else:
                    logger.info(f"🔑 Usando app_id de fallback: {FALLBACK_APP_ID}")
                result["app_id"] = extracted_id

            # ── Obtener cookies actualizadas del navegador ───────────────────
            browser_cookies = context.cookies()
            updated: dict = {}
            for c in browser_cookies:
                if "instagram.com" in c.get("domain", ""):
                    updated[c["name"]] = c["value"]

            if updated:
                result["cookies"].update(updated)
                logger.info(f"🍪 {len(updated)} cookies actualizadas desde el navegador")

            # ── Persistir cookies ─────────────────────────────────────────────
            if save_cookies and cookies_path:
                _save_cookies(cookies_path, result["cookies"])

            context.close()
            browser.close()

    except Exception as exc:
        logger.error(f"❌ Error en playwright: {exc}")
        logger.warning("🔄 Continuando con cookies originales del .env")

    return result
