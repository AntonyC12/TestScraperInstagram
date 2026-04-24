"""
Back/main.py  —  Punto de entrada del Instagram Profile Scraper v2.0
=====================================================================
Autenticación: 100% via cookies del navegador (ig_mid, ig_did, sessionid...)
               NO usa username/password en primera instancia.

Ejecutar desde la raíz del proyecto:
    .venv\\Scripts\\python.exe Back\\main.py

O con el venv activado:
    python Back\\main.py
"""

import logging
import os
import sys
from pathlib import Path

# ─── Forzar UTF-8 en la consola de Windows (evita UnicodeEncodeError con emojis) ─
import io
if sys.stdout.encoding and sys.stdout.encoding.upper() not in ("UTF-8", "UTF8"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")
os.environ.setdefault("PYTHONUTF8", "1")

# ─── Asegurar que Back/ esté en el path ─────────────────────────────────────
_back_dir = Path(__file__).parent
if str(_back_dir) not in sys.path:
    sys.path.insert(0, str(_back_dir))

# ─── Configurar logging ──────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  [%(levelname)-8s]  %(name)s — %(message)s",
    datefmt="%H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(_back_dir.parent / "scraper.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger(__name__)


def main() -> None:
    # ── 1. Cargar y validar configuración ───────────────────────────────────
    from config.settings import settings

    try:
        settings.validate()
    except ValueError as exc:
        logger.error(str(exc))
        sys.exit(1)

    # ── 2. Ejecutar caso de uso ──────────────────────────────────────────────
    from application.scrape_profile import ScrapeProfileUseCase

    use_case = ScrapeProfileUseCase(settings)

    try:
        use_case.execute()
    except PermissionError as exc:
        logger.error(f"\n{exc}")
        logger.error(
            "💡 Sugerencia: Renueva las cookies desde DevTools → "
            "Application → Cookies → instagram.com"
        )
        sys.exit(2)
    except ValueError as exc:
        logger.error(f"\n{exc}")
        sys.exit(3)
    except KeyboardInterrupt:
        logger.info("\n🛑 Scraping interrumpido por el usuario.")
        sys.exit(0)
    except Exception as exc:
        logger.exception(f"❌ Error inesperado: {exc}")
        sys.exit(99)


if __name__ == "__main__":
    main()
