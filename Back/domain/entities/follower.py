"""
domain/entities/follower.py
============================
Entidad de dominio: Follower
Representa un seguidor de Instagram dentro del dominio del negocio.
No depende de ningún framework externo — es Python puro.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class Follower:
    """
    Entidad de dominio que representa un seguidor de una cuenta de Instagram.

    Atributos:
        pk          : Identificador único del usuario en Instagram.
        username    : Nombre de usuario (@handle).
        full_name   : Nombre completo del perfil.
        is_private  : True si la cuenta es privada.
        profile_pic_url : URL de la foto de perfil (puede ser None).
    """

    pk: str
    username: str
    full_name: str
    is_private: bool
    profile_pic_url: Optional[str] = None

    def to_dict(self) -> dict:
        """Serializa la entidad a un diccionario apto para JSON."""
        return {
            "pk": self.pk,
            "username": self.username,
            "full_name": self.full_name,
            "is_private": self.is_private,
            "profile_pic_url": self.profile_pic_url,
        }

    def __str__(self) -> str:
        privacy = "🔒 Privada" if self.is_private else "🌍 Pública"
        return f"@{self.username} | {self.full_name} | {privacy}"
