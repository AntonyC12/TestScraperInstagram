"""
Back/tests/test_personality_logic.py
====================================
Prueba unitaria para validar el análisis de personalidad Big Five.
Usa datos existentes de un JSON para evitar llamadas a Instagram.
"""

import sys
import os
import json
import logging

# Añadir el path raíz para que los imports funcionen
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from application.personality_analysis import PersonalityAnalysisUseCase
from infrastructure.ai.gemini_client import GeminiClient
from domain.models import ScrapedData, Post, Profile, VisualAnalysis
from config.settings import Settings

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_personality_flow():
    # 1. Cargar Settings (para la API Key)
    settings = Settings()
    if not settings.gemini_api_key:
        logger.error("❌ GEMINI_API_KEY no encontrada en .env")
        return

    # 2. Simular datos scrapeados (Mock)
    # Cargamos el archivo que el usuario nos pasó para que la prueba sea realista
    json_path = os.path.join("Back", "sessions", "Ig_Data_Kruscaya.json")
    if not os.path.exists(json_path):
        logger.error(f"❌ No se encontró el archivo: {json_path}")
        return

    with open(json_path, "r", encoding="utf-8") as f:
        raw_data = json.load(f)

    # 3. Convertir a objetos de dominio (simplificado para el test)
    posts = []
    for p in raw_data.get("posts", [])[:5]: # Solo 5 para el test
        # Simulamos un análisis visual básico si está vacío
        va = p.get("visual_analysis", {})
        if not va.get("scene_tags"):
            va["scene_tags"] = ["paisaje", "naturaleza"]
            va["aesthetic_style"] = "natural/exterior"
            va["emotion_cues"] = ["paz"]

        posts.append(Post(
            post_id=p["post_id"],
            shortcode=p["shortcode"],
            timestamp=p["timestamp"],
            type=p["type"],
            caption_raw=p["caption_raw"],
            caption_clean=p["caption_clean"],
            visual_analysis=VisualAnalysis(**va),
            display_url=p.get("display_url", "")
        ))

    scraped_data = ScrapedData(
        metadata=None,
        profile=Profile(
            username=raw_data["profile"]["username"],
            bio=raw_data["profile"]["bio"]
        ),
        data_quality=None,
        posts=posts
    )

    # 4. Ejecutar Análisis
    # Intentamos Gemini 1.5 Flash si el 2.0 está agotado o no disponible
    model_to_use = "gemini-1.5-flash" 
    logger.info(f"Using model: {model_to_use}")
    client = GeminiClient(settings.gemini_api_key, model_name=model_to_use)
    use_case = PersonalityAnalysisUseCase(client)
    
    logger.info("🚀 Iniciando prueba de análisis de personalidad...")
    try:
        report = use_case.execute(scraped_data)

        # 5. Validar Resultados
        if "traits" in report:
            logger.info("✅ Reporte generado exitosamente.")
            print("\n" + "="*50)
            print("--- RESUMEN DE PERSONALIDAD ---")
            print("="*50)
            print(f"Resumen: {report.get('summary', 'N/A')}")
            print("\nRasgos detectados:")
            for trait, data in report.get("traits", {}).items():
                print(f"- {trait.capitalize()}: {data.get('score', 0)} (Confianza: {data.get('confidence', 0)})")
                print(f"  Interpretacion: {data.get('interpretation', 'N/A')[:100]}...")
            print("="*50)
        else:
            logger.error(f"❌ Error en el reporte: {report.get('error', 'Desconocido')}")
    except Exception as e:
        logger.error(f"❌ Error crítico en el test: {e}")

if __name__ == "__main__":
    # Forzar salida UTF-8 en Windows
    if sys.platform == "win32":
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    test_personality_flow()
