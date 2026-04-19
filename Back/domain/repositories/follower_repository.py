"""
domain/repositories/follower_repository.py
===========================================
Interfaz abstracta del repositorio de seguidores.
Define el CONTRATO que deben cumplir todas las implementaciones concretas
(Instagram API, mock de testing, etc.), sin acoplarse a ninguna tecnología.
"""

from abc import ABC, abstractmethod
from typing import List

from domain.entities.follower import Follower


class IFollowerRepository(ABC):
    """
    Contrato (puerto) del repositorio de seguidores.

    Cualquier fuente de datos que quiera proveer seguidores debe implementar
    esta interfaz. Esto permite intercambiar la implementación sin modificar
    la lógica de negocio (Principio de Inversión de Dependencias — SOLID).
    """

    @abstractmethod
    def get_followers(self, target: str, limit: int) -> List[Follower]:
        """
        Obtiene la lista de seguidores de una cuenta pública.

        Args:
            target  : Nombre de usuario de la cuenta objetivo (sin @).
            limit   : Cantidad máxima de seguidores a obtener.

        Returns:
            Lista de entidades Follower.

        Raises:
            UserNotFoundError  : Si la cuenta no existe.
            PrivateAccountError: Si la cuenta es privada.
        """
        ...
