"""
application/personality_analysis.py
===================================
UseCase encargado de realizar el análisis profundo de personalidad (OCEAN).
Transforma los datos crudos y visuales en un reporte psicológico estructurado.
"""

import logging
import json
from domain.models import ScrapedData, BigFiveModel, BigFiveTrait

logger = logging.getLogger(__name__)

class PersonalityAnalysisUseCase:
    def __init__(self, ai_client):
        self.ai_client = ai_client

    def execute(self, scraped_data: ScrapedData) -> dict:
        """
        Realiza el análisis Big Five basado en bio, posts y análisis visual previo.
        """
        logger.info(f"🧬 Iniciando análisis de personalidad para: {scraped_data.profile.username}")
        
        # 1. Preparar el resumen de posts para la IA
        # Incluimos captions y los hallazgos visuales clave
        posts_context = []
        for p in scraped_data.posts[:15]:  # Analizamos los últimos 15 para balancear costo/precisión
            posts_context.append({
                "caption": p.caption_raw,
                "visual_summary": {
                    "scene": p.visual_analysis.scene_tags,
                    "is_selfie": p.visual_analysis.is_selfie,
                    "aesthetic": p.visual_analysis.aesthetic_style,
                    "emotion": p.visual_analysis.emotion_cues
                },
                "engagement": p.engagement,
                "timestamp": p.timestamp
            })

        # 2. Llamada al cliente de IA para análisis holístico
        try:
            raw_analysis = self.ai_client.analyze_personality_ocean(
                profile_bio=scraped_data.profile.bio,
                posts_data=posts_context
            )
            
            # 3. Estructurar el reporte
            report = {
                "summary": raw_analysis.get("summary", "No se pudo generar un resumen."),
                "traits": raw_analysis.get("traits", {}),
                "academic_notes": raw_analysis.get("academic_notes", "Análisis basado en indicadores conductuales de redes sociales."),
                "potential_biases": raw_analysis.get("potential_biases", ["Limitación de datos públicos", "Sesion de auto-presentación"])
            }
            
            # Guardar en el objeto de datos
            scraped_data.personality_report = report
            return report
            
        except Exception as e:
            logger.error(f"❌ Error durante el análisis de personalidad: {e}")
            return {"error": str(e)}
