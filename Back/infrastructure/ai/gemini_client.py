"""
infrastructure/ai/gemini_client.py
==================================
Cliente actualizado para la nueva SDK google-genai (v2.0+).
Encargado del análisis visual de posts y la inferencia de personalidad (Big Five).
"""

import json
import logging
from typing import Any, Optional
from google import genai
from google.genai import types
import requests
from io import BytesIO
from tenacity import (
    retry, stop_after_attempt, wait_exponential,
    retry_if_exception_type
)

logger = logging.getLogger(__name__)

class GeminiClient:
    def __init__(self, api_key: str, model_name: str = "gemini-2.0-flash"):
        if not api_key or "tu_gemini_api_key" in api_key:
            logger.warning("⚠️ GEMINI_API_KEY no configurada o es inválida. El análisis visual será omitido.")
            self.client = None
            return
            
        try:
            # Usamos v1beta para soportar responseMimeType (JSON) y análisis multimodal
            api_version = "v1beta"
            self.client = genai.Client(api_key=api_key, http_options={'api_version': api_version})
            self.model_name = model_name
            logger.info(f"🤖 Cliente Gemini listo (Modelo: {model_name}, API: {api_version})")
        except Exception as e:
            logger.error(f"❌ Error inicializando cliente Gemini: {e}")
            self.client = None

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=2, min=5, max=30),
        retry=retry_if_exception_type(Exception),
        reraise=True
    )
    def analyze_post_visual(self, image_url: str, caption: str) -> dict:
        """
        Analiza una imagen usando la nueva SDK de Gemini con reintentos automáticos.
        """
        if not self.client:
            return {}

        prompt = f"""
        Analiza esta imagen de una publicación de Instagram. 
        Contexto (Caption): {caption}
        
        Responde en formato JSON con esta estructura exacta:
        {{
            "scene_tags": ["ambiente", "objetos_clave"],
            "objects": ["lista_de_objetos"],
            "people_count": int,
            "has_face": bool,
            "is_selfie": bool,
            "is_group_photo": bool,
            "indoor_outdoor": "indoor" | "outdoor",
            "activity_type": "descripcion_breve",
            "aesthetic_style": "minimalista|vibrante|oscuro|etc",
            "emotion_cues": ["emociones_detectadas"],
            "text_in_image": "texto detectado o null",
            "confidence": 0.0 a 1.0,
            "evidence": ["por qué se clasifica así"]
        }}
        """

        try:
            resp = requests.get(image_url, timeout=10)
            image_bytes = resp.content
            
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=[
                    types.Part.from_bytes(data=image_bytes, mime_type="image/jpeg"),
                    prompt
                ],
                config=types.GenerateContentConfig(
                    response_mime_type="application/json"
                )
            )
            return json.loads(response.text)
        except Exception as e:
            logger.error(f"❌ Error en Gemini Visual Analysis: {e}")
            raise

    def analyze_personality_ocean(self, profile_bio: str, posts_data: list[dict]) -> dict:
        """
        Analiza la personalidad del usuario (OCEAN) usando la nueva SDK.
        """
        if not self.client:
            return {}

        posts_summary = []
        for p in posts_data[:12]: 
            visual = p.get("visual_analysis")
            scene_tags = getattr(visual, "scene_tags", []) if visual else []
            posts_summary.append({
                "caption": p.get("caption_raw", ""),
                "visual": scene_tags
            })

        prompt = f"""
        Analiza el perfil de Instagram para determinar rasgos Big Five (OCEAN) con propósito académico.
        Bio: {profile_bio}
        Resumen de Posts (Texto + Visual): {json.dumps(posts_summary, ensure_ascii=False)}
        
        Responde en JSON con esta estructura:
        {{
            "summary": "Resumen narrativo de la personalidad",
            "traits": {{
                "openness": {{ "score": float, "interpretation": "...", "confidence": float, "evidence": [] }},
                "conscientiousness": {{ "score": float, "interpretation": "...", "confidence": float, "evidence": [] }},
                "extraversion": {{ "score": float, "interpretation": "...", "confidence": float, "evidence": [] }},
                "agreeableness": {{ "score": float, "interpretation": "...", "confidence": float, "evidence": [] }},
                "neuroticism": {{ "score": float, "interpretation": "...", "confidence": float, "evidence": [] }}
            }},
            "academic_notes": "Relación entre indicadores digitales y rasgos",
            "potential_biases": ["lista de posibles sesgos"]
        }}
        """

        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json"
                )
            )
            return json.loads(response.text)
        except Exception as e:
            logger.error(f"❌ Error en Gemini Personality Analysis (v2): {e}")
            return {}

    def infer_context_and_demographics(self, bio: str, captions: list[str]) -> dict:
        """
        Infiere contexto demográfico usando la nueva SDK.
        """
        if not self.client:
            return {}

        prompt = f"""
        Analiza bio y captions para extraer: language, country, city, age_range, occupation, gender_identity.
        Bio: {bio}
        Captions: {json.dumps(captions[:10], ensure_ascii=False)}
        Responde en JSON.
        """
        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json"
                )
            )
            return json.loads(response.text)
        except Exception as e:
            logger.error(f"❌ Error en Gemini Context Analysis (v2): {e}")
            return {}
