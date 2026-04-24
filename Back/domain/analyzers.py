"""
domain/analyzers.py
===================
Análisis de contenido textual, conducta temporal e interacción social.
Sin dependencias externas excepto 'emoji'. Lógica puramente de dominio.
"""

from __future__ import annotations

import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from typing import TYPE_CHECKING

import emoji as emoji_lib

if TYPE_CHECKING:
    from domain.models import (
        Comment, ContentAnalysis, LanguageStyle, Post,
        SocialInteraction, TemporalBehavior
    )


# ─────────────────────────────────────────────────────────────────────────────
#  HELPERS DE EXTRACCIÓN
# ─────────────────────────────────────────────────────────────────────────────

_HASHTAG_RE = re.compile(r"#(\w+)", re.UNICODE)
_MENTION_RE = re.compile(r"@(\w+)", re.UNICODE)

# Palabras clave por tema (español + inglés comunes)
_THEMES = {
    "vida personal":          ["yo", "mi", "me", "siento", "hoy", "día", "personal", "life", "my"],
    "logros académicos/laborales": ["graduación", "título", "trabajo", "empleo", "proyecto", "logro",
                                    "universidad", "carrera", "study", "job", "work", "degree"],
    "ocio":                   ["viaje", "playa", "vacaciones", "descanso", "fun", "travel", "beach",
                                "trip", "vacation", "fiesta", "party"],
    "espiritualidad":         ["dios", "fe", "oración", "bendición", "gracias", "paz", "espíritu",
                                "god", "faith", "prayer", "blessed"],
    "activismo":              ["justicia", "derechos", "igualdad", "protesta", "causa", "lucha",
                                "justice", "rights", "equality", "protest"],
    "moda":                   ["ropa", "outfit", "estilo", "moda", "fashion", "look", "style", "ootd"],
    "familia":                ["familia", "mamá", "papá", "hermano", "hermana", "hijo", "hija",
                                "family", "mom", "dad", "brother", "sister"],
    "rutina diaria":          ["rutina", "mañana", "noche", "desayuno", "gym", "ejercicio",
                                "morning", "night", "routine", "breakfast"],
    "entretenimiento":        ["serie", "película", "música", "concierto", "juego",
                                "movie", "music", "concert", "game", "netflix"],
    "nostalgia":              ["recuerdo", "antes", "extraño", "nostalgía", "throwback", "memory",
                                "miss", "past"],
    "autorrevelación emocional": ["siento", "emoción", "feliz", "triste", "ansioso", "orgulloso",
                                   "feel", "happy", "sad", "proud", "anxious", "emotional"],
    "naturaleza/mascotas":    ["naturaleza", "planta", "perro", "gato", "mascota", "naturaleza",
                                "nature", "pet", "dog", "cat", "animal"],
    "comida":                 ["comida", "receta", "restaurante", "cena", "almuerzo",
                                "food", "recipe", "restaurant", "lunch", "dinner"],
    "deporte":                ["deporte", "fútbol", "correr", "maratón", "gym", "entreno",
                                "sport", "football", "run", "marathon", "training"],
}

# Indicadores de estado emocional
_EMOTIONAL_WORDS = {
    "alegría":    ["feliz", "alegre", "emocionado", "contento", "happy", "excited", "joy", "love"],
    "tristeza":   ["triste", "extraño", "solo", "perdí", "sad", "miss", "lonely", "lost"],
    "ansiedad":   ["ansioso", "nervioso", "preocupado", "anxious", "nervous", "worried", "stress"],
    "orgullo":    ["orgulloso", "logré", "conseguí", "proud", "achieved", "accomplished"],
    "nostalgia":  ["recuerdo", "antes", "throwback", "nostalgia", "miss"],
    "amor":       ["amor", "quiero", "amo", "corazón", "love", "heart", "❤", "💕"],
}

_INFORMAL_MARKERS = ["jaja", "jeje", "xd", "haha", "hehe", "lol", "omg", "omfg", "wtf",
                      "bro", "men", "wey", "güey", "pues", "osea", "o sea"]
_FORMAL_MARKERS   = ["estimado", "cordialmente", "mediante", "referente", "adjunto",
                      "cabe destacar", "por lo tanto", "en consecuencia"]


def extract_hashtags(text: str) -> list[str]:
    """Devuelve lista de hashtags encontrados en el texto (sin el #)."""
    return [m.lower() for m in _HASHTAG_RE.findall(text)]


def extract_emojis(text: str) -> list[str]:
    """Devuelve lista de emojis encontrados en el texto."""
    return [token["emoji"] for token in emoji_lib.emoji_list(text)]


def extract_mentions(text: str) -> list[str]:
    """Devuelve lista de @menciones encontradas en el texto."""
    return [m.lower() for m in _MENTION_RE.findall(text)]


# ─────────────────────────────────────────────────────────────────────────────
#  ANÁLISIS DE LENGUAJE
# ─────────────────────────────────────────────────────────────────────────────

def classify_language_style(captions: list[str]) -> "LanguageStyle":
    from domain.models import LanguageStyle

    if not captions:
        return LanguageStyle()

    non_empty = [c for c in captions if c.strip()]
    if not non_empty:
        return LanguageStyle()

    all_hashtags: list[str] = []
    all_emojis:   list[str] = []

    for cap in non_empty:
        all_hashtags.extend(extract_hashtags(cap))
        all_emojis.extend(extract_emojis(cap))

    lengths = [len(c.split()) for c in non_empty]
    avg_len = sum(lengths) / len(lengths)
    avg_hashtags = len(all_hashtags) / len(non_empty)
    avg_emojis   = len(all_emojis)   / len(non_empty)

    # Verbosidad
    if avg_len < 10:
        verbosity = "breve"
    elif avg_len < 30:
        verbosity = "moderado"
    else:
        verbosity = "extenso"

    # Tono formal/informal
    full_text = " ".join(non_empty).lower()
    informal_hits = sum(1 for w in _INFORMAL_MARKERS if w in full_text)
    formal_hits   = sum(1 for w in _FORMAL_MARKERS   if w in full_text)

    if informal_hits > formal_hits + 2:
        tone = "informal"
    elif formal_hits > informal_hits + 2:
        tone = "formal"
    elif avg_emojis > 1.5:
        tone = "emocional"
    else:
        tone = "neutro"

    # Reflexividad
    reflective_markers = ["pienso", "creo", "siento que", "me pregunto", "reflexión",
                           "i think", "i feel", "i wonder", "reflection"]
    impulsive_markers  = ["!!!", "ahora", "ya", "now", "right now", "hoy mismo"]
    refl_hits = sum(1 for m in reflective_markers if m in full_text)
    impu_hits = sum(1 for m in impulsive_markers  if m in full_text)
    if refl_hits > impu_hits:
        reflexivity = "reflexivo"
    elif impu_hits > refl_hits:
        reflexivity = "impulsivo"
    else:
        reflexivity = "neutro"

    # Indicadores emocionales
    emotional_indicators: list[str] = []
    for emotion, words in _EMOTIONAL_WORDS.items():
        if any(w in full_text for w in words):
            emotional_indicators.append(emotion)

    # Top hashtags
    ht_counter = Counter(all_hashtags)
    top_hashtags = [{"tag": t, "count": c} for t, c in ht_counter.most_common(20)]

    # Top emojis
    em_counter = Counter(all_emojis)
    top_emojis = [{"emoji": e, "count": c} for e, c in em_counter.most_common(20)]

    return LanguageStyle(
        avg_caption_length=round(avg_len, 2),
        avg_hashtags_per_post=round(avg_hashtags, 2),
        avg_emojis_per_post=round(avg_emojis, 2),
        tone_classification=tone,
        verbosity=verbosity,
        reflexivity=reflexivity,
        emotional_indicators=emotional_indicators,
        top_hashtags=top_hashtags,
        top_emojis=top_emojis,
    )


def detect_recurring_themes(captions: list[str]) -> list[str]:
    """Detecta temas recurrentes contando palabras clave por categoría."""
    full_text = " ".join(captions).lower()
    theme_scores: dict[str, int] = {}
    for theme, keywords in _THEMES.items():
        score = sum(full_text.count(kw) for kw in keywords)
        if score > 0:
            theme_scores[theme] = score
    # Ordenar por frecuencia, retornar nombres de temas
    return [t for t, _ in sorted(theme_scores.items(), key=lambda x: x[1], reverse=True)]


def build_content_analysis(posts: list["Post"]) -> "ContentAnalysis":
    from domain.models import ContentAnalysis

    captions     = [p.caption for p in posts if p.caption]
    all_hashtags = [ht for p in posts for ht in p.hashtags]
    all_emojis   = [em for p in posts for em in p.emojis]

    # Comentarios escritos por el dueño del perfil
    owner_comments: list[str] = []
    for post in posts:
        for comment in post.comments:
            if comment.is_owner_comment:
                owner_comments.append(comment.text)

    return ContentAnalysis(
        captions=captions,
        all_hashtags=all_hashtags,
        all_emojis=all_emojis,
        owner_comments=owner_comments,
        recurring_themes=detect_recurring_themes(captions),
        language_style=classify_language_style(captions),
    )


# ─────────────────────────────────────────────────────────────────────────────
#  ANÁLISIS TEMPORAL
# ─────────────────────────────────────────────────────────────────────────────

def analyze_temporal_behavior(posts: list["Post"]) -> "TemporalBehavior":
    from domain.models import TemporalBehavior

    if not posts:
        return TemporalBehavior()

    timestamps: list[datetime] = []
    for p in posts:
        if p.timestamp_unix:
            try:
                dt = datetime.fromtimestamp(p.timestamp_unix, tz=timezone.utc)
                timestamps.append(dt)
            except (OSError, OverflowError, ValueError):
                pass

    if not timestamps:
        return TemporalBehavior()

    timestamps.sort()

    # Frecuencia de publicación
    if len(timestamps) > 1:
        deltas = [(timestamps[i+1] - timestamps[i]).days for i in range(len(timestamps)-1)]
        avg_freq = sum(deltas) / len(deltas)
    else:
        avg_freq = 0.0

    # Distribución por mes
    month_dist: dict[str, int] = defaultdict(int)
    hour_dist:  dict[str, int] = defaultdict(int)
    day_dist:   dict[str, int] = defaultdict(int)
    days_map = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

    for dt in timestamps:
        month_key = dt.strftime("%Y-%m")
        month_dist[month_key] += 1
        hour_dist[str(dt.hour)] += 1
        day_dist[days_map[dt.weekday()]] += 1

    most_active_hour = max(hour_dist, key=hour_dist.get) if hour_dist else ""
    most_active_day  = max(day_dist,  key=day_dist.get)  if day_dist  else ""

    # Periodos activos (meses con >= 2 posts) y silencio (0 posts)
    all_months = sorted(month_dist.keys())
    active_periods  = [m for m, c in month_dist.items() if c >= 2]
    silence_periods: list[str] = []
    if all_months:
        # Detectar meses sin actividad en el rango
        start = datetime.strptime(all_months[0],  "%Y-%m")
        end   = datetime.strptime(all_months[-1], "%Y-%m")
        cur   = start
        while cur <= end:
            key = cur.strftime("%Y-%m")
            if key not in month_dist:
                silence_periods.append(key)
            # Avanzar un mes
            if cur.month == 12:
                cur = cur.replace(year=cur.year+1, month=1)
            else:
                cur = cur.replace(month=cur.month+1)

    # Tendencia de actividad
    monthly_counts = [month_dist[m] for m in sorted(month_dist.keys())]
    if len(monthly_counts) >= 3:
        first_half = sum(monthly_counts[:len(monthly_counts)//2])
        second_half = sum(monthly_counts[len(monthly_counts)//2:])
        if second_half > first_half * 1.2:
            trend = "creciente"
        elif second_half < first_half * 0.8:
            trend = "decreciente"
        else:
            trend = "estable"
    else:
        trend = "insuficientes datos"

    return TemporalBehavior(
        posting_frequency_days=round(avg_freq, 2),
        posts_per_month=dict(sorted(month_dist.items())),
        hour_distribution=dict(sorted(hour_dist.items(), key=lambda x: int(x[0]))),
        day_distribution=dict(day_dist),
        most_active_hour=most_active_hour,
        most_active_day=most_active_day,
        first_post_date=timestamps[0].isoformat(),
        last_post_date=timestamps[-1].isoformat(),
        active_periods=sorted(active_periods),
        silence_periods=sorted(silence_periods),
        activity_trend=trend,
    )


# ─────────────────────────────────────────────────────────────────────────────
#  ANÁLISIS DE INTERACCIÓN SOCIAL
# ─────────────────────────────────────────────────────────────────────────────

_FRIENDLY_WORDS   = ["gracias", "genial", "increíble", "hermoso", "bello", "amor",
                      "thanks", "great", "amazing", "beautiful", "love", "wonderful"]
_AFFECTIVE_WORDS  = ["❤", "💕", "😍", "😘", "🥰", "te quiero", "te amo", "love you"]
_POLEMIC_WORDS    = ["mentira", "falso", "ridículo", "vergüenza", "odio", "asco",
                      "lie", "fake", "ridiculous", "shame", "hate", "disgusting"]


def _classify_comment_type(text: str) -> str:
    t = text.lower()
    if any(w in t for w in _POLEMIC_WORDS):
        return "polemica"
    if any(w in t for w in _AFFECTIVE_WORDS):
        return "afectiva"
    if any(w in t for w in _FRIENDLY_WORDS):
        return "amistosa"
    return "neutra"


def analyze_social_interaction(posts: list["Post"], target_username: str) -> "SocialInteraction":
    from domain.models import SocialInteraction

    if not posts:
        return SocialInteraction()

    total_comments = sum(p.comments_count for p in posts)
    total_likes    = sum(p.likes_count    for p in posts)
    n = len(posts)

    commenter_counter: Counter[str] = Counter()
    type_dist: dict[str, int] = {"amistosa": 0, "afectiva": 0, "neutra": 0, "polemica": 0}
    owner_replies = 0
    total_analyzed = 0

    for post in posts:
        for comment in post.comments:
            total_analyzed += 1
            commenter_counter[comment.username] += 1
            ctype = _classify_comment_type(comment.text)
            type_dist[ctype] = type_dist.get(ctype, 0) + 1
            if comment.is_owner_comment:
                owner_replies += 1

    top_commenters = [
        {"username": u, "count": c}
        for u, c in commenter_counter.most_common(10)
        if u != target_username
    ]

    return SocialInteraction(
        avg_comments_per_post=round(total_comments / n, 2),
        avg_likes_per_post=round(total_likes / n, 2),
        total_comments_analyzed=total_analyzed,
        owner_replies_count=owner_replies,
        replies_to_own_posts=owner_replies > 0,
        interaction_type_distribution=type_dist,
        top_commenters=top_commenters,
    )
