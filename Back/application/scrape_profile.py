"""
application/scrape_profile.py
==============================
Orquestador del flujo de scraping Robusto v2.1.
Incluye análisis visual con Gemini y análisis profundo de personalidad.
"""

from __future__ import annotations
import logging
from datetime import datetime, timezone
from pathlib import Path

from config.settings import Settings
import time
from domain.models import ScrapedData, Metadata, DataQuality, BigFiveModel, VisualAnalysis
from domain.analyzers import DomainAnalyzer
from infrastructure.auth.cookie_session import get_session_data
from infrastructure.instagram.http_client import build_session, random_delay
from infrastructure.instagram.profile_fetcher import fetch_profile
from infrastructure.instagram.posts_fetcher import fetch_posts
from infrastructure.instagram.comments_fetcher import fetch_all_post_comments
from infrastructure.persistence.json_writer import save_to_json
from infrastructure.ai.gemini_client import GeminiClient
from application.personality_analysis import PersonalityAnalysisUseCase
from application.report_generator import ReportGeneratorUseCase
from infrastructure.persistence.mongo_repository import MongoRepository

logger = logging.getLogger(__name__)

SCRAPER_VERSION = "2.1.0"

class ScrapeProfileUseCase:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        
        if settings.ai_provider == "groq":
            from infrastructure.ai.groq_client import GroqClient
            self.ai_client = GroqClient(settings.groq_api_key, model_name=settings.groq_model)
        else:
            self.ai_client = GeminiClient(settings.gemini_api_key, model_name=settings.gemini_model)

    def execute(self) -> ScrapedData:
        s = self.settings
        target = s.target_account

        logger.info("==============================================================")
        logger.info(f"  🕵️  Instagram Profile Scraper  v{SCRAPER_VERSION} (ROBUSTO)")
        logger.info("==============================================================")

        # ── FASE 1: Sesión ───────────────────────────────────────────────────
        session_data = get_session_data(
            target_username=target,
            cookies_dict=s.as_cookies_dict(),
            app_id_override=s.ig_app_id,
            headless=s.playwright_headless,
            cookies_path=s.cookies_file,
            save_cookies=True,
        )
        http_session = build_session(session_data["cookies"], session_data["app_id"])

        # ── FASE 2: Perfil ───────────────────────────────────────────────────
        profile, user_id, end_cursor, initial_edges = fetch_profile(http_session, target)
        
        # Inferencia de contexto inicial
        if (s.gemini_api_key or s.groq_api_key):
            logger.info(f"🤖 Infiriendo contexto declarado con {s.ai_provider.upper()}...")
            context_data = self.ai_client.infer_context_and_demographics(profile.bio, [])
            profile.declared_context.language = context_data.get("language")
            profile.declared_context.country = context_data.get("country")
            profile.declared_context.city = context_data.get("city")
            profile.declared_context.age_range = context_data.get("age_range")
            profile.declared_context.occupation = context_data.get("occupation")

        # ── FASE 3: Posts ────────────────────────────────────────────────────
        posts = fetch_posts(http_session, user_id, initial_edges, end_cursor, s.posts_limit)
        
        # ── FASE 4: Comentarios ──────────────────────────────────────────────
        fetch_all_post_comments(http_session, posts, target, s.comments_limit)
        total_comments = sum(len(p.comments_sample) for p in posts)

        # ── FASE 5: Análisis Profundo (Visual + Texto) ───────────────────────
        logger.info(f"🔬 Analizando {len(posts)} posts (Visual + Texto)...")
        for i, post in enumerate(posts):
            # Análisis Textual (Heurística)
            post.text_analysis = DomainAnalyzer.analyze_text(post)
            post.derived_features = DomainAnalyzer.calculate_derived(post)
            
            # Análisis Visual (IA)
            if (s.gemini_api_key or s.groq_api_key) and post.display_url:
                logger.info(f"  📸 [{i+1}/{len(posts)}] Analizando imagen: {post.shortcode}")
                visual_data = self.ai_client.analyze_post_visual(post.display_url, post.caption_raw)
                post.visual_analysis = VisualAnalysis(
                    model_used=getattr(self.ai_client, "model_name", "unknown"),
                    image_inputs=[{"url": post.display_url, "role": "primary"}],
                    **visual_data
                )
                time.sleep(2) # Pequeño respiro para evitar 429

        # ── FASE 6: Agregados y Personalidad ─────────────────────────────────
        logger.info("🧬 Generando análisis de personalidad (Big Five)...")
        aggregate_features = DomainAnalyzer.build_aggregate_features(posts)
        
        personality_report = {}
        if (s.gemini_api_key or s.groq_api_key):
            personality_service = PersonalityAnalysisUseCase(self.ai_client)
            personality_report = personality_service.execute(
                ScrapedData(
                    metadata=None, # Dummy para el service
                    profile=profile,
                    data_quality=None,
                    posts=posts
                )
            )

        # ── ENSAMBLAR ────────────────────────────────────────────────────────
        scraped_data = ScrapedData(
            metadata=Metadata(
                scraped_at=datetime.now(tz=timezone.utc).isoformat(),
                target_account=target,
                scraper_version=SCRAPER_VERSION,
                posts_requested=s.posts_limit,
                posts_obtained=len(posts),
                comments_per_post=s.comments_limit,
                total_comments_obtained=total_comments,
                session_valid=session_data.get("is_logged_in", False),
                app_id_used=session_data["app_id"]
            ),
            profile=profile,
            data_quality=DataQuality(
                first_post_date=posts[-1].timestamp if posts else "",
                last_post_date=posts[0].timestamp if posts else "",
                posts_requested=s.posts_limit,
                posts_obtained=len(posts),
                comments_obtained=total_comments
            ),
            posts=posts,
            aggregate_features=aggregate_features,
            personality_report=personality_report,
            model_outputs={"big_five_raw": personality_report.get("traits", {})}
        )

        # ── PERSISTIR ────────────────────────────────────────────────────────
        save_to_json(scraped_data, s.output_file)
        
        # Debug: Verificar si la URI existe
        if not s.mongo_uri:
            logger.warning("🚨 MONGO_URI no detectada en la configuración. Revisa el archivo .env")
        else:
            logger.info(f"🔗 Intentando conectar a MongoDB Atlas (URI detectada)...")
            try:
                mongo_repo = MongoRepository(s.mongo_uri, s.mongo_database)
                mongo_repo.save_analysis("personality_reports", scraped_data.to_dict())
                mongo_repo.close()
            except Exception as e:
                logger.error(f"❌ Error crítico en el flujo de MongoDB: {e}")

        # Generar Reporte PDF
        report_service = ReportGeneratorUseCase(s.back_dir / "reports")
        pdf_path = report_service.execute(scraped_data.to_dict())
        
        logger.info("==============================================================")
        logger.info(f"  ✅  SCRAPING ROBUSTO COMPLETADO")
        logger.info(f"  📄  JSON guardado en: {s.output_file}")
        logger.info(f"  📊  PDF generado en: {pdf_path}")
        logger.info("==============================================================")

        return scraped_data
