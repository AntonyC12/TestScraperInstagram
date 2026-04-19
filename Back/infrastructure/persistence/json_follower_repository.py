"""
infrastructure/persistence/json_follower_repository.py
========================================================
Repositorio de persistencia: guarda seguidores en un archivo JSON local.
Implementa la capa de salida del sistema — no conoce nada de Instagram.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import List

from domain.entities.follower import Follower

logger = logging.getLogger(__name__)

# Ruta por defecto del archivo de salida
DEFAULT_OUTPUT = Path(__file__).resolve().parent.parent.parent / "debug_followers.json"


class JsonFollowerRepository:
    """
    Persiste una lista de entidades Follower en un archivo JSON con metadata.

    Formato del archivo generado:
    {
        "metadata": {
            "target_account": "usuario_objetivo",
            "total_followers_scraped": 123,
            "scraped_at": "2024-01-01T12:00:00"
        },
        "followers": [
            { "pk": "...", "username": "...", ... },
            ...
        ]
    }
    """

    def __init__(self, output_path: Path = DEFAULT_OUTPUT):
        self._output_path = output_path

    def save(self, target: str, followers: List[Follower]) -> Path:
        """
        Serializa y guarda la lista de seguidores en JSON.

        Args:
            target    : Username de la cuenta scrapeada.
            followers : Lista de entidades Follower a guardar.

        Returns:
            Path absoluto del archivo JSON generado.
        """
        payload = {
            "metadata": {
                "target_account": target,
                "total_followers_scraped": len(followers),
                "scraped_at": datetime.now().isoformat(),
            },
            "followers": [f.to_dict() for f in followers],
        }

        # Asegurar que el directorio padre existe
        self._output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(self._output_path, "w", encoding="utf-8") as fp:
            json.dump(payload, fp, ensure_ascii=False, indent=2)

        logger.info(
            f"💾 debug_followers.json guardado: "
            f"{len(followers)} seguidores → {self._output_path}"
        )
        return self._output_path
