"""
application/use_cases/fetch_followers.py
==========================================
Caso de Uso: FetchFollowersUseCase
Orquesta la lógica de obtener seguidores de Instagram y persistirlos en JSON.

Reglas de la capa de aplicación:
- Solo conoce interfaces del dominio (IFollowerRepository).
- No importa nada de instagrapi ni de JSON directamente.
- Es el único lugar donde se coordinan las capas.
"""

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import List

from domain.entities.follower import Follower
from domain.repositories.follower_repository import IFollowerRepository
from infrastructure.persistence.json_follower_repository import JsonFollowerRepository

logger = logging.getLogger(__name__)


@dataclass
class FetchFollowersResult:
    """
    DTO de resultado del caso de uso.
    Contiene los datos de salida listos para ser consumidos por main.py o una API.
    """
    target: str
    total: int
    output_path: Path
    followers: List[Follower]


class FetchFollowersUseCase:
    """
    Caso de uso principal del sistema.

    Responsabilidades:
    1. Delega la obtención de seguidores al IFollowerRepository (dominio).
    2. Delega la persistencia al JsonFollowerRepository (infraestructura).
    3. Retorna un FetchFollowersResult con el resumen de la operación.

    NO contiene lógica de negocio compleja — solo orquesta los pasos.
    """

    def __init__(
        self,
        follower_repository: IFollowerRepository,
        json_repository: JsonFollowerRepository,
    ):
        # Inyección de dependencias — cumple DIP (Dependency Inversion Principle)
        self._follower_repo = follower_repository
        self._json_repo = json_repository

    def execute(self, target: str, limit: int) -> FetchFollowersResult:
        """
        Ejecuta el caso de uso completo.

        Args:
            target : Username de la cuenta a scrapear (sin @).
            limit  : Número máximo de seguidores a obtener.

        Returns:
            FetchFollowersResult con los seguidores y ruta del archivo generado.
        """
        logger.info(
            f"🚀 [CasoDeUso] FetchFollowers → @{target} (límite: {limit})"
        )

        # Paso 1: Obtener seguidores desde la fuente de datos
        followers = self._follower_repo.get_followers(target=target, limit=limit)

        # Paso 2: Persistir en JSON
        output_path = self._json_repo.save(target=target, followers=followers)

        result = FetchFollowersResult(
            target=target,
            total=len(followers),
            output_path=output_path,
            followers=followers,
        )

        logger.info(
            f"✅ [CasoDeUso] Completado: {result.total} seguidores "
            f"de @{target} guardados en {output_path.name}"
        )
        return result
