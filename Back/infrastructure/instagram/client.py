"""
infrastructure/instagram/client.py
====================================
Cliente de Instagram con anti-detección integrada.
Gestiona la sesión, el login y las configuraciones de dispositivo móvil
para minimizar la probabilidad de ser detectado como bot.
"""

import logging
from pathlib import Path

from instagrapi import Client
from instagrapi.exceptions import ChallengeRequired, LoginRequired

logger = logging.getLogger(__name__)

# Ruta donde se guarda la sesión para no re-loguear cada ejecución
SESSION_FILE = Path(__file__).resolve().parent.parent.parent / "session.json"

# ──────────────────────────────────────────────
#  Configuración de dispositivo (anti-detección)
#  Simula un Samsung Galaxy S10 con Android 8
# ──────────────────────────────────────────────
DEVICE_SETTINGS = {
    "app_version": "269.0.0.18.75",
    "android_version": 26,
    "android_release": "8.0.0",
    "dpi": "480dpi",
    "resolution": "1080x1920",
    "manufacturer": "Samsung",
    "device": "SM-G973F",
    "model": "galaxy_s10_eu",
    "cpu": "samsungexynos9820",
    "version_code": "314665256",
}


def _build_client() -> Client:
    """
    Construye un cliente de instagrapi con configuraciones anti-detección:
    - Device spoofing: simula un dispositivo Android real.
    - Delay aleatorio entre peticiones (2–5 segundos).
    - Timeout generoso para evitar errores en redes lentas.
    """
    cl = Client()
    cl.set_device(DEVICE_SETTINGS)
    cl.delay_range = [2, 5]       # Delay aleatorio entre requests (imita humano)
    cl.request_timeout = 30        # Timeout generoso
    return cl


def get_authenticated_client(username: str, password: str) -> Client:
    """
    Retorna un cliente autenticado de Instagram.

    Estrategia de sesión persistente:
    1. Si existe session.json → carga la sesión guardada y la verifica.
    2. Si la sesión caducó → elimina el archivo y hace login de nuevo.
    3. Si no existe session.json → login desde cero y guarda la sesión.

    Esto evita hacer login en cada ejecución, lo que reduce el riesgo
    de que Instagram detecte actividad sospechosa.

    Args:
        username: Nombre de usuario de Instagram (desde .env).
        password: Contraseña de Instagram (desde .env).

    Returns:
        Cliente de instagrapi autenticado y listo para usar.

    Raises:
        ChallengeRequired: Si Instagram exige verificación adicional.
        Exception: Si el login falla por razones inesperadas.
    """
    cl = _build_client()

    # ── Intento 1: restaurar sesión guardada ──
    if SESSION_FILE.exists():
        logger.info("📂 Sesión guardada encontrada. Intentando restaurar...")
        try:
            cl.load_settings(SESSION_FILE)
            cl.login(username, password)
            logger.info("✅ Sesión restaurada exitosamente. Sin nuevo login.")
            return cl
        except LoginRequired:
            logger.warning("⚠️  Sesión caducada. Se eliminará y se hará login de nuevo.")
            SESSION_FILE.unlink(missing_ok=True)
        except Exception as e:
            logger.warning(f"⚠️  Error restaurando sesión: {e}. Reintentando login...")
            SESSION_FILE.unlink(missing_ok=True)

    # ── Intento 2: login limpio ──
    logger.info("🔑 Iniciando sesión por primera vez...")
    try:
        cl.login(username, password)
        cl.dump_settings(SESSION_FILE)
        logger.info(f"✅ Login exitoso. Sesión guardada en: {SESSION_FILE}")
    except ChallengeRequired as e:
        logger.error(
            "❌ Instagram solicitó verificación (ChallengeRequired). "
            "Intenta iniciar sesión manualmente desde la app y vuelve a intentarlo."
        )
        raise

    return cl
