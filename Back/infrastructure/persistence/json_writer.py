"""
infrastructure/persistence/json_writer.py
==========================================
Serializa el objeto ScrapedData completo a un archivo JSON en Back/.
Usa dataclasses.asdict para convertir recursivamente todos los modelos.
"""

from __future__ import annotations

import json
import logging
from dataclasses import asdict
from pathlib import Path

from domain.models import ScrapedData

logger = logging.getLogger(__name__)


def _clean(obj):
    """Limpia valores nulos/vacíos recursivamente para un JSON más limpio."""
    if isinstance(obj, dict):
        return {k: _clean(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_clean(v) for v in obj]
    return obj


def save_to_json(data: ScrapedData, output_path: Path) -> Path:
    """
    Serializa ScrapedData a JSON y lo guarda en output_path.

    Args:
        data: Objeto ScrapedData completo con todos los datos
        output_path: Ruta donde guardar el .json (ej: Back/instagram_data.json)

    Returns:
        La ruta absoluta del archivo generado
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    raw_dict = asdict(data)
    clean_dict = _clean(raw_dict)

    output_path.write_text(
        json.dumps(clean_dict, indent=2, ensure_ascii=False, default=str),
        encoding="utf-8"
    )

    size_kb = output_path.stat().st_size / 1024
    logger.info(f"💾 JSON guardado en: {output_path} ({size_kb:.1f} KB)")
    return output_path.resolve()
