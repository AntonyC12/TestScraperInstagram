"""
application/scrape_profile.py
==============================
Caso de uso principal: orquesta el flujo completo de scraping.

Flujo:
  1. Playwright extrae cookies dinámicas + x-ig-app-id
  2. Se construye requests.Session con todas las cookies + headers
  3. Se extrae el perfil (profile_fetcher)
  4. Se extraen los posts (posts_fetcher) — con paginación
  5. Se extraen comentarios de cada post (comments_fetcher)
  6. Se ejecutan los analizadores (domain/analyzers)
  7. Se ensambla ScrapedData y se retorna para persistir
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path

from config.settings import Settings
from domain.models import ScrapedData
from domain.analyzers import (
    build_content_analysis,
    analyze_temporal_behavior,
    analyze_social_interaction,
)
from infrastructure.auth.cookie_session import get_session_data
from infrastructure.instagram.http_client import build_session, random_delay
from infrastructure.instagram.profile_fetcher import fetch_profile
from infrastructure.instagram.posts_fetcher import fetch_posts
from infrastructure.instagram.comments_fetcher import fetch_all_post_comments
from infrastructure.persistence.json_writer import save_to_json

logger = logging.getLogger(__name__)

SCRAPER_VERSION = "2.0.0"


class ScrapeProfileUseCase:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def execute(self) -> ScrapedData:
        s = self.settings
        target = s.target_account

        sep = "=" * 62
        logger.info(sep)
        logger.info(f"  🕵️  Instagram Profile Scraper  v{SCRAPER_VERSION}")
        logger.info(sep)
        logger.info(f"  Target  : @{target}")
        logger.info(f"  Posts   : hasta {s.posts_limit}")
        logger.info(f"  Comments: hasta {s.comments_limit} por post")
        logger.info(sep)

        # ── FASE 1: Playwright — obtener cookies dinámicas y app_id ──────────
        logger.info("🎭 [Fase 1/5] Iniciando Playwright para validar sesión...")
        session_data = get_session_data(
            target_username=target,
            cookies_dict=s.as_cookies_dict(),
            app_id_override=s.ig_app_id,
            headless=s.playwright_headless,
            cookies_path=s.cookies_file,
            save_cookies=True,
        )

        if not session_data.get("is_logged_in"):
            logger.warning("⚠️  Playwright no pudo confirmar login. Continuando con cookies del .env...")

        cookies = session_data["cookies"]
        app_id  = session_data["app_id"]

        # ── FASE 2: Construir requests.Session ───────────────────────────────
        logger.info("🔧 [Fase 2/5] Construyendo HTTP session...")
        http_session = build_session(cookies, app_id)
        random_delay(1.0, 2.0)

        # ── FASE 3: Extraer perfil ───────────────────────────────────────────
        logger.info(f"👤 [Fase 3/5] Extrayendo perfil de @{target}...")
        profile, user_id, end_cursor, initial_edges = fetch_profile(http_session, target)
        logger.info(
            f"  ✅ @{profile.username} | "
            f"Seguidores: {profile.followers_count:,} | "
            f"Siguiendo: {profile.following_count:,} | "
            f"Posts: {profile.posts_count:,}"
        )

        # ── FASE 4: Extraer posts ─────────────────────────────────────────────
        logger.info(f"📸 [Fase 4/5] Extrayendo hasta {s.posts_limit} posts...")
        # initial_edges ya viene incluido en fetch_profile — sin request extra.
        random_delay(1.5, 3.0)
        posts = fetch_posts(
            session=http_session,
            user_id=user_id,
            initial_edges=initial_edges,
            initial_cursor=end_cursor,
            limit=s.posts_limit,
        )
        logger.info(f"  ✅ {len(posts)} posts extraídos")

        # ── FASE 5: Extraer comentarios ───────────────────────────────────────
        logger.info(f"💬 [Fase 5/5] Extrayendo comentarios ({s.comments_limit}/post)...")
        fetch_all_post_comments(
            session=http_session,
            posts=posts,
            owner_username=target,
            limit_per_post=s.comments_limit,
        )
        total_comments = sum(p.comments_fetched for p in posts)
        logger.info(f"  ✅ {total_comments} comentarios extraídos en total")

        # ── ANÁLISIS ──────────────────────────────────────────────────────────
        logger.info("🔬 Ejecutando analizadores de dominio...")
        content_analysis    = build_content_analysis(posts)
        temporal_behavior   = analyze_temporal_behavior(posts)
        social_interaction  = analyze_social_interaction(posts, target)

        # ── ENSAMBLAR ScrapedData ─────────────────────────────────────────────
        scraped_data = ScrapedData(
            metadata={
                "scraped_at":       datetime.now(tz=timezone.utc).isoformat(),
                "target_account":   target,
                "scraper_version":  SCRAPER_VERSION,
                "posts_requested":  s.posts_limit,
                "posts_obtained":   len(posts),
                "comments_per_post": s.comments_limit,
                "total_comments_obtained": total_comments,
                "session_valid":    session_data.get("is_logged_in", False),
                "app_id_used":      app_id,
            },
            profile=profile,
            posts=posts,
            content_analysis=content_analysis,
            temporal_behavior=temporal_behavior,
            social_interaction=social_interaction,
        )

        # ── PERSISTIR ─────────────────────────────────────────────────────────
        logger.info(f"💾 Guardando resultados en {s.output_file}...")
        output_path = save_to_json(scraped_data, s.output_file)

        logger.info(sep)
        logger.info("  ✅  SCRAPING COMPLETADO")
        logger.info(f"  📄  JSON en: {output_path}")
        logger.info(f"  👤  Perfil:  @{profile.username} ({profile.full_name})")
        logger.info(f"  👥  Seguidores: {profile.followers_count:,}")
        logger.info(f"  📸  Posts: {len(posts)} | 💬 Comentarios: {total_comments}")
        logger.info(f"  🎨  Tono: {content_analysis.language_style.tone_classification}")
        logger.info(f"  📅  Frecuencia: {temporal_behavior.posting_frequency_days} días entre posts")
        logger.info(sep)

        return scraped_data
