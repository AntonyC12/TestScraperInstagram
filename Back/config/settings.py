"""
config/settings.py
==================
Carga y valida todas las variables de entorno necesarias para el scraper.
La autenticación se hace con cookies del navegador; username/password son opcionales.
"""

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

# Carga .env desde Back/.env
_ENV_PATH = Path(__file__).parent.parent / ".env"
load_dotenv(dotenv_path=_ENV_PATH, override=False)


@dataclass
class Settings:
    # ── Cuenta objetivo ───────────────────────────────────────────────────────
    target_account: str = field(default_factory=lambda: os.getenv("TARGET_ACCOUNT", "").strip())

    # ── Cookies de identidad (autenticación principal) ────────────────────────
    ig_session_id: str   = field(default_factory=lambda: os.getenv("IG_SESSION_ID", "").strip())
    ig_mid: str          = field(default_factory=lambda: os.getenv("IG_MID", "").strip())
    ig_did: str          = field(default_factory=lambda: os.getenv("IG_DID", "").strip())
    ig_nrcb: str         = field(default_factory=lambda: os.getenv("IG_NRCB", "1").strip())
    ig_csrftoken: str    = field(default_factory=lambda: os.getenv("IG_CSRFTOKEN", "").strip())
    ig_datr: str         = field(default_factory=lambda: os.getenv("IG_DATR", "").strip())
    ig_ds_user_id: str   = field(default_factory=lambda: os.getenv("IG_DS_USER_ID", "").strip())
    # App ID de Instagram web (extraído por playwright si no está definido)
    ig_app_id: str       = field(default_factory=lambda: os.getenv("IG_APP_ID", "936619743392459").strip())

    # ── Credenciales opcionales (fallback, NO se usan en primera instancia) ──
    ig_username: str = field(default_factory=lambda: os.getenv("IG_USERNAME", "").strip())
    ig_password: str = field(default_factory=lambda: os.getenv("IG_PASSWORD", "").strip())

    # ── Límites de extracción ──────────────────────────────────────────────────
    posts_limit: int    = field(default_factory=lambda: int(os.getenv("POSTS_LIMIT", "20")))
    comments_limit: int = field(default_factory=lambda: int(os.getenv("COMMENTS_LIMIT", "10")))

    # ── Playwright ────────────────────────────────────────────────────────────
    playwright_headless: bool = field(
        default_factory=lambda: os.getenv("PLAYWRIGHT_HEADLESS", "true").lower() == "true"
    )

    # ── Inteligencia Artificial ───────────────────────────────────────────────
    ai_provider: str = field(
        default_factory=lambda: os.getenv("AI_PROVIDER", "gemini").lower().strip()
    )
    gemini_api_key: Optional[str] = field(
        default_factory=lambda: os.getenv("GEMINI_API_KEY")
    )
    gemini_model: str = field(
        default_factory=lambda: os.getenv("GEMINI_MODEL", "gemini-1.5-flash").strip()
    )
    groq_api_key: Optional[str] = field(
        default_factory=lambda: os.getenv("GROQ_API_KEY")
    )
    groq_model: str = field(
        default_factory=lambda: os.getenv("GROQ_MODEL", "llama-3.2-90b-vision-preview").strip()
    )

    # ── Paths ─────────────────────────────────────────────────────────────────
    back_dir: Path    = field(default_factory=lambda: Path(__file__).parent.parent)
    cookies_file: Path = field(
        default_factory=lambda: Path(__file__).parent.parent / "sessions" / "cookies.json"
    )
    output_file: Path  = field(
        default_factory=lambda: Path(__file__).parent.parent / "instagram_data.json"
    )

    def validate(self) -> None:
        """Lanza ValueError si faltan las cookies mínimas requeridas."""
        required = {
            "TARGET_ACCOUNT": self.target_account,
            "IG_SESSION_ID":  self.ig_session_id,
            "IG_MID":         self.ig_mid,
            "IG_DID":         self.ig_did,
        }
        missing = [k for k, v in required.items() if not v]
        if missing:
            raise ValueError(
                f"❌ Faltan variables de entorno obligatorias: {missing}\n"
                f"   → Edita: {_ENV_PATH}"
            )

    def as_cookies_dict(self) -> dict:
        """Retorna el dict de cookies listo para inyectar en requests o playwright."""
        cookies = {
            "sessionid":  self.ig_session_id,
            "mid":        self.ig_mid,
            "ig_did":     self.ig_did,
            "ig_nrcb":    self.ig_nrcb,
            "ds_user_id": self.ig_ds_user_id,
        }
        if self.ig_csrftoken:
            cookies["csrftoken"] = self.ig_csrftoken
        if self.ig_datr:
            cookies["datr"] = self.ig_datr
        return {k: v for k, v in cookies.items() if v}


# Singleton global para uso en todo el proyecto
settings = Settings()
