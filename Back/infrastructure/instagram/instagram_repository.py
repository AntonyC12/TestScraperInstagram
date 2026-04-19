"""
infrastructure/instagram/instagram_repository.py
==================================================
Implementación concreta del repositorio de seguidores usando instagrapi.
Esta clase traduce entre el dominio (entidad Follower) y la API de Instagram.
"""

import logging
import random
import time
from typing import List

from instagrapi import Client

from domain.entities.follower import Follower
from domain.repositories.follower_repository import IFollowerRepository

logger = logging.getLogger(__name__)


class InstagramFollowerRepository(IFollowerRepository):
    """
    Implementación del IFollowerRepository que usa instagrapi para
    obtener seguidores directamente desde la API privada de Instagram.

    Anti-detección implementada:
    - Pausa aleatoria cada 50 seguidores para simular scroll humano.
    - El cliente ya viene pre-configurado con delays entre requests.
    """

    def __init__(self, client: Client):
        self._client = client

    def get_followers(self, target: str, limit: int) -> List[Follower]:
        """
        Obtiene los seguidores de una cuenta pública de Instagram.

        Args:
            target : Username de la cuenta a scrapear (sin @).
            limit  : Número máximo de seguidores a obtener.

        Returns:
            Lista de entidades Follower ordenadas por username.
        """
        logger.info(f"🔍 Resolviendo user_id para: @{target} ...")
        user_id = self._client.user_id_from_username(target)
        logger.info(
            f"📋 user_id: {user_id} — "
            f"Solicitando hasta {limit} seguidores en bloques..."
        )

        # instagrapi pagina internamente usando end_cursor (GraphQL)
        # amount=0 significa "todos los seguidores disponibles"
        followers_raw = self._client.user_followers(user_id, amount=limit)

        followers: List[Follower] = []
        for pk, user in followers_raw.items():
            followers.append(
                Follower(
                    pk=str(user.pk),
                    username=user.username,
                    full_name=user.full_name or "",
                    is_private=user.is_private,
                    profile_pic_url=(
                        str(user.profile_pic_url)
                        if user.profile_pic_url
                        else None
                    ),
                )
            )

            # Pausa anti-detección cada 50 seguidores (simula scroll humano)
            if len(followers) % 50 == 0 and len(followers) < limit:
                pause = round(random.uniform(1.5, 4.0), 2)
                logger.info(
                    f"⏳ Pausa anti-bot: {pause}s "
                    f"[{len(followers)}/{limit} recopilados]"
                )
                time.sleep(pause)

        logger.info(f"✅ Total obtenidos: {len(followers)} seguidores de @{target}.")
        return followers
