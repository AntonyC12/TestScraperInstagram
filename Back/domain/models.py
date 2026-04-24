"""
domain/models.py
================
Modelos de datos puros (sin dependencias externas).
Representan toda la información que el scraper extrae de Instagram.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Optional


# ─────────────────────────────────────────────────────────────────────────────
#  1. PERFIL
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class Profile:
    username: str = ""
    full_name: str = ""
    biography: str = ""
    profile_pic_url: str = ""
    profile_pic_hd_url: str = ""
    external_url: str = ""
    external_url_linkshimmed: str = ""
    is_private: bool = False
    is_verified: bool = False
    is_business: bool = False
    category: str = ""
    followers_count: int = 0
    following_count: int = 0
    posts_count: int = 0
    user_id: str = ""
    # Aproximación de creación de cuenta inferida del post más antiguo visible
    account_created_approx: str = ""
    # Primer post visible (para inferir antigüedad)
    oldest_post_timestamp: str = ""


# ─────────────────────────────────────────────────────────────────────────────
#  2. COMENTARIOS
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class Comment:
    id: str = ""
    username: str = ""
    text: str = ""
    timestamp: str = ""             # ISO 8601
    timestamp_unix: int = 0
    likes_count: int = 0
    is_owner_comment: bool = False  # True si el autor es el dueño del perfil


# ─────────────────────────────────────────────────────────────────────────────
#  3. PUBLICACIÓN
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class Post:
    id: str = ""
    shortcode: str = ""
    timestamp: str = ""             # ISO 8601
    timestamp_unix: int = 0
    type: str = ""                  # GraphImage | GraphVideo | GraphSidecar
    caption: str = ""
    hashtags: list[str] = field(default_factory=list)
    emojis: list[str] = field(default_factory=list)
    likes_count: int = 0
    comments_count: int = 0
    display_url: str = ""
    is_video: bool = False
    video_view_count: Optional[int] = None
    location: Optional[str] = None
    location_id: Optional[str] = None
    # Señales visuales — se dejan como None (análisis de visión = fase futura)
    visual_signals: dict[str, Any] = field(default_factory=lambda: {
        "has_face": None,
        "is_selfie_approx": None,
        "scene_tags": [],
        "note": "Visual analysis pending (requires Vision API)"
    })
    comments: list[Comment] = field(default_factory=list)
    comments_fetched: int = 0


# ─────────────────────────────────────────────────────────────────────────────
#  4. ANÁLISIS DE CONTENIDO TEXTUAL
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class LanguageStyle:
    avg_caption_length: float = 0.0
    avg_hashtags_per_post: float = 0.0
    avg_emojis_per_post: float = 0.0
    tone_classification: str = ""       # formal | informal | emocional | neutro
    verbosity: str = ""                 # breve | moderado | extenso
    reflexivity: str = ""               # reflexivo | impulsivo | neutro
    emotional_indicators: list[str] = field(default_factory=list)
    top_hashtags: list[dict] = field(default_factory=list)   # [{tag, count}]
    top_emojis: list[dict] = field(default_factory=list)     # [{emoji, count}]


@dataclass
class ContentAnalysis:
    captions: list[str] = field(default_factory=list)
    all_hashtags: list[str] = field(default_factory=list)
    all_emojis: list[str] = field(default_factory=list)
    owner_comments: list[str] = field(default_factory=list)  # Comentarios del dueño
    recurring_themes: list[str] = field(default_factory=list)
    language_style: LanguageStyle = field(default_factory=LanguageStyle)


# ─────────────────────────────────────────────────────────────────────────────
#  5. CONDUCTA TEMPORAL
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class TemporalBehavior:
    posting_frequency_days: float = 0.0   # Promedio de días entre posts
    posts_per_month: dict[str, int] = field(default_factory=dict)   # {"2024-03": 5}
    hour_distribution: dict[str, int] = field(default_factory=dict) # {"14": 7}
    day_distribution: dict[str, int] = field(default_factory=dict)  # {"Monday": 4}
    most_active_hour: str = ""
    most_active_day: str = ""
    first_post_date: str = ""
    last_post_date: str = ""
    active_periods: list[str] = field(default_factory=list)   # meses con +2 posts
    silence_periods: list[str] = field(default_factory=list)  # meses con 0 posts
    activity_trend: str = ""  # creciente | decreciente | estable | irregular


# ─────────────────────────────────────────────────────────────────────────────
#  6. INTERACCIÓN SOCIAL
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class SocialInteraction:
    avg_comments_per_post: float = 0.0
    avg_likes_per_post: float = 0.0
    total_comments_analyzed: int = 0
    owner_replies_count: int = 0           # Cuántas veces respondió a comentarios
    replies_to_own_posts: bool = False
    interaction_type_distribution: dict[str, int] = field(default_factory=dict)
    # {"amistosa": N, "afectiva": N, "neutra": N, "polemica": N}
    top_commenters: list[dict] = field(default_factory=list)  # [{username, count}]


# ─────────────────────────────────────────────────────────────────────────────
#  7. DATO COMPLETO
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class ScrapedData:
    metadata: dict[str, Any] = field(default_factory=dict)
    profile: Profile = field(default_factory=Profile)
    posts: list[Post] = field(default_factory=list)
    content_analysis: ContentAnalysis = field(default_factory=ContentAnalysis)
    temporal_behavior: TemporalBehavior = field(default_factory=TemporalBehavior)
    social_interaction: SocialInteraction = field(default_factory=SocialInteraction)
