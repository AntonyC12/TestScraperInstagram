"""
domain/models.py
================
Modelos de datos robustos para el análisis de perfiles de Instagram.
Sigue la estructura v2.1 solicitada con campos de confianza y evidencia.
"""

from __future__ import annotations
from dataclasses import dataclass, field, asdict
from typing import Any, Optional

# ==============================================================================
#  AUXILIARES
# ==============================================================================

@dataclass
class ConfidenceField:
    """Campo con trazabilidad y confianza."""
    value: Any = None
    confidence: float = 0.0
    evidence: list[str] = field(default_factory=list)

# ==============================================================================
#  METADATA Y CALIDAD
# ==============================================================================

@dataclass
class Metadata:
    scraped_at: str
    target_account: str
    scraper_version: str = "2.1.0"
    posts_requested: int = 0
    posts_obtained: int = 0
    comments_per_post: int = 0
    total_comments_obtained: int = 0
    session_valid: bool = True
    app_id_used: str = ""

@dataclass
class DataQuality:
    account_created_approx: str = ""
    first_post_date: str = ""
    last_post_date: str = ""
    posts_requested: int = 0
    posts_obtained: int = 0
    comments_obtained: int = 0
    missing_fields: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

# ==============================================================================
#  PERFIL Y CONTEXTO
# ==============================================================================

@dataclass
class DeclaredContext:
    language: Optional[str] = None
    country: Optional[str] = None
    city: Optional[str] = None
    age_range: Optional[str] = None
    education_level: Optional[str] = None
    occupation: Optional[str] = None

@dataclass
class Profile:
    username: str = ""
    full_name: str = ""
    is_private: bool = False
    is_verified: bool = False
    is_business: bool = False
    followers_count: int = 0
    following_count: int = 0
    posts_count: int = 0
    bio: str = ""
    external_url: str = ""
    profile_pic_url: str = ""
    profile_pic_hd_url: str = ""
    declared_context: DeclaredContext = field(default_factory=DeclaredContext)

# ==============================================================================
#  ANÁLISIS DE POST (VISUAL + TEXTO)
# ==============================================================================

@dataclass
class VisualAnalysis:
    model_used: Optional[str] = None
    image_inputs: list[dict] = field(default_factory=list)
    scene_tags: list[str] = field(default_factory=list)
    objects: list[str] = field(default_factory=list)
    people_count: Optional[int] = None
    has_face: Optional[bool] = None
    is_selfie: Optional[bool] = None
    is_group_photo: Optional[bool] = None
    indoor_outdoor: Optional[str] = None
    activity_type: Optional[str] = None
    aesthetic_style: Optional[str] = None
    emotion_cues: list[str] = field(default_factory=list)
    text_in_image: Optional[str] = None
    confidence: float = 0.0
    evidence: list[str] = field(default_factory=list)

@dataclass
class TextAnalysis:
    language_detected: Optional[str] = None
    sentiment: Optional[str] = None
    emotion_labels: list[str] = field(default_factory=list)
    topic_tags: list[str] = field(default_factory=list)
    verbosity: Optional[str] = None
    reflexivity: Optional[str] = None
    tone: Optional[str] = None
    confidence: float = 0.0

@dataclass
class DerivedFeatures:
    posting_hour: Optional[int] = None
    posting_day: Optional[str] = None
    caption_length: int = 0
    emoji_density: float = 0.0
    hashtag_density: float = 0.0
    social_presence_score: float = 0.0
    visual_self_presentation_score: float = 0.0

@dataclass
class Comment:
    comment_id: str
    username: str
    text: str
    timestamp: str
    is_owner_comment: bool = False
    sentiment: Optional[str] = None

@dataclass
class Post:
    post_id: str
    shortcode: str
    timestamp: str
    type: str
    caption_raw: str
    caption_clean: str
    hashtags: list[str] = field(default_factory=list)
    emojis: list[str] = field(default_factory=list)
    mentions: list[str] = field(default_factory=list)
    location: dict = field(default_factory=lambda: {"name": None, "id": None, "confidence": 0.0})
    engagement: dict = field(default_factory=lambda: {"likes_count": 0, "comments_count": 0})
    visual_analysis: VisualAnalysis = field(default_factory=VisualAnalysis)
    text_analysis: TextAnalysis = field(default_factory=TextAnalysis)
    comments_sample: list[Comment] = field(default_factory=list)
    derived_features: DerivedFeatures = field(default_factory=DerivedFeatures)
    display_url: str = "" # Para uso interno del fetcher

    def to_dict(self):
        return asdict(self)

# ==============================================================================
#  PERSONALIDAD Y AGREGADOS
# ==============================================================================

@dataclass
class BigFiveTrait:
    score: Optional[float] = None
    interpretation: str = ""
    confidence: float = 0.0
    evidence: list[str] = field(default_factory=list)

@dataclass
class BigFiveModel:
    openness: BigFiveTrait = field(default_factory=BigFiveTrait)
    conscientiousness: BigFiveTrait = field(default_factory=BigFiveTrait)
    extraversion: BigFiveTrait = field(default_factory=BigFiveTrait)
    agreeableness: BigFiveTrait = field(default_factory=BigFiveTrait)
    neuroticism: BigFiveTrait = field(default_factory=BigFiveTrait)

@dataclass
class ScrapedData:
    metadata: Metadata
    profile: Profile
    data_quality: DataQuality
    posts: list[Post]
    aggregate_features: dict = field(default_factory=dict)
    context_variables: dict = field(default_factory=dict)
    personality_report: Optional[dict] = None
    model_outputs: dict = field(default_factory=dict)
    human_review: dict = field(default_factory=lambda: {
        "reviewed": False,
        "reviewer_notes": "",
        "disagreements_with_model": []
    })

    def to_dict(self):
        import dataclasses
        def _fix(obj):
            if isinstance(obj, dict): return {str(k): _fix(v) for k, v in obj.items()}
            if isinstance(obj, list): return [_fix(i) for i in obj]
            return obj
        return _fix(dataclasses.asdict(self))
