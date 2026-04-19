"""
Back/main.py  —  Punto de entrada y Composition Root
======================================================
Este archivo es el único lugar del sistema que conoce TODAS las capas.
Su responsabilidad es:
  1. Cargar la configuración desde .env
  2. Instanciar e inyectar las dependencias (Composition Root)
  3. Ejecutar el caso de uso principal
  4. Reportar el resultado al usuario

COMANDOS PARA EJECUTAR MANUALMENTE:
    # Desde la raíz del proyecto (TestScraperInstagram/)
    .venv\\Scripts\\python.exe Back\\main.py

    # O con Python del venv activado:
    .venv\\Scripts\\activate
    python Back\\main.py
"""

import logging
import os
import sys
from pathlib import Path

# ─── Cargar .env ANTES de cualquier import del proyecto ───────────────────────
from dotenv import load_dotenv

_env_path = Path(__file__).parent / ".env"
load_dotenv(dotenv_path=_env_path, override=False)

# ─── Configurar logging ────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  [%(levelname)-8s]  %(name)s — %(message)s",
    datefmt="%H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger(__name__)

# ─── Asegurar que Back/ esté en el path para imports DDD ─────────────────────
_back_dir = Path(__file__).parent
if str(_back_dir) not in sys.path:
    sys.path.insert(0, str(_back_dir))


# ──────────────────────────────────────────────────────────────────────────────
#  COMPOSITION ROOT
# ──────────────────────────────────────────────────────────────────────────────
def main() -> None:
    # 1. Leer configuración desde variables de entorno
    username = os.getenv("IG_USERNAME", "").strip()
    password = os.getenv("IG_PASSWORD", "").strip()
    target   = os.getenv("TARGET_ACCOUNT", "").strip()
    limit    = int(os.getenv("FOLLOWER_COUNT", "100"))

    # Validaciones tempranas
    missing = [k for k, v in {
        "IG_USERNAME": username,
        "IG_PASSWORD": password,
        "TARGET_ACCOUNT": target,
    }.items() if not v or v in ("my_username", "my_password", "count_objetive")]

    if missing:
        logger.error(
            f"❌ Faltan variables de entorno o tienen valores de ejemplo: {missing}\n"
            f"   → Edita el archivo: {_env_path}"
        )
        sys.exit(1)

    # Banner de inicio
    separator = "=" * 62
    logger.info(separator)
    logger.info("  🕵️  Instagram Followers Scraper  —  Modo Debug")
    logger.info(separator)
    logger.info(f"  Target account : @{target}")
    logger.info(f"  Límite          : {limit} seguidores")
    logger.info(f"  .env cargado    : {_env_path}")
    logger.info(separator)

    # 2. Importar capas (dentro de main para que sys.path ya esté configurado)
    from infrastructure.instagram.client import get_authenticated_client
    from infrastructure.instagram.instagram_repository import InstagramFollowerRepository
    from infrastructure.persistence.json_follower_repository import JsonFollowerRepository
    from application.use_cases.fetch_followers import FetchFollowersUseCase

    # 3. Instanciar dependencias (Dependency Injection manual)
    logger.info("🔑 Autenticando en Instagram...")
    client        = get_authenticated_client(username, password)
    ig_repo       = InstagramFollowerRepository(client)
    json_repo     = JsonFollowerRepository()
    use_case      = FetchFollowersUseCase(ig_repo, json_repo)

    # 4. Ejecutar caso de uso
    result = use_case.execute(target=target, limit=limit)

    # 5. Reporte final
    logger.info(separator)
    logger.info("  ✅  SCRAPING COMPLETADO")
    logger.info(f"  👥  Seguidores obtenidos : {result.total}")
    logger.info(f"  📄  Archivo generado     : {result.output_path}")
    logger.info(separator)

    # Muestra los primeros 5 seguidores como preview
    if result.followers:
        logger.info("  📋 Preview (primeros 5 seguidores):")
        for f in result.followers[:5]:
            logger.info(f"      {f}")
        if result.total > 5:
            logger.info(f"      ... y {result.total - 5} más en el JSON.")
    logger.info(separator)


if __name__ == "__main__":
    main()
