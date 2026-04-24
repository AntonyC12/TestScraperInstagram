import os
import json
import logging
import base64
import httpx
from typing import Any, Optional
from groq import Groq

logger = logging.getLogger(__name__)

class GroqClient:
    def __init__(self, api_key: str, model_name: str = "llama-3.2-90b-vision-preview"):
        if not api_key or "tu_groq_api_key" in api_key:
            logger.warning("⚠️ GROQ_API_KEY no configurada. El análisis visual/OCEAN por Groq será omitido.")
            self.client = None
            return
            
        try:
            self.client = Groq(api_key=api_key)
            self.model_name = model_name
            logger.info(f"🚀 Cliente Groq listo (Modelo: {model_name})")
        except Exception as e:
            logger.error(f"❌ Error inicializando cliente Groq: {e}")
            self.client = None

    def analyze_post_visual(self, image_url: str, caption: str) -> dict:
        """Analiza imagen usando Llama 3.2 Vision en Groq."""
        if not self.client: return {}

        try:
            # Descargar imagen y convertir a base64 para Groq
            image_resp = httpx.get(image_url)
            base64_image = base64.b64encode(image_resp.content).decode('utf-8')
            
            prompt = f"Analiza esta imagen de Instagram. Contexto: {caption}. Responde ÚNICAMENTE en JSON con estos campos: scene_tags (list), objects (list), people_count (int), has_face (bool), is_selfie (bool), indoor_outdoor (string), activity_type (string), aesthetic_style (string), confidence (float), evidence (list)."

            completion = self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}
                            }
                        ]
                    }
                ],
                response_format={"type": "json_object"}
            )
            return json.loads(completion.choices[0].message.content)
        except Exception as e:
            logger.error(f"❌ Error en Groq Visual Analysis: {e}")
            return {}

    def analyze_personality_ocean(self, profile_bio: str, posts_data: list[dict]) -> dict:
        """Analiza personalidad usando Llama 3 en Groq."""
        if not self.client: return {}

        prompt = f"""
        Analiza el perfil de Instagram para determinar rasgos Big Five (OCEAN) con propósito académico.
        Bio: {profile_bio}
        Resumen de Posts: {json.dumps(posts_data, ensure_ascii=False)}
        
        Responde ÚNICAMENTE en JSON con esta estructura:
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
            completion = self.client.chat.completions.create(
                model="llama-3.3-70b-versatile", 
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"}
            )
            return json.loads(completion.choices[0].message.content)
        except Exception as e:
            logger.error(f"❌ Error en Groq Personality Analysis: {e}")
            return {}

    def infer_context_and_demographics(self, bio: str, captions: list[str]) -> dict:
        """Infiere contexto demográfico usando Llama 3 en Groq."""
        if not self.client: return {}

        prompt = f"Analiza bio y captions para extraer: language, country, city, age_range, occupation, gender_identity. Bio: {bio}. Captions: {json.dumps(captions[:10])}. Responde ÚNICAMENTE en JSON."
        try:
            completion = self.client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"}
            )
            return json.loads(completion.choices[0].message.content)
        except Exception as e:
            logger.error(f"❌ Error en Groq Context Analysis: {e}")
            return {}
