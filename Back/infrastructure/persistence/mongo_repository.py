"""
infrastructure/persistence/mongo_repository.py
==============================================
Implementación del repositorio para MongoDB Atlas.
Sigue el patrón Repository para desacoplar la base de datos del caso de uso.
"""

import logging
from typing import Any, Dict
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, OperationFailure

logger = logging.getLogger(__name__)

class MongoRepository:
    def __init__(self, uri: str, db_name: str):
        self.uri = uri
        self.db_name = db_name
        self.client = None
        self.db = None
        self._connect()

    def _connect(self):
        try:
            self.client = MongoClient(self.uri)
            # Validar conexión
            self.client.admin.command('ping')
            self.db = self.client[self.db_name]
            logger.info(f"✅ Conexión exitosa a MongoDB Atlas (DB: {self.db_name})")
        except (ConnectionFailure, OperationFailure) as e:
            logger.error(f"❌ Error conectando a MongoDB: {e}")
            self.client = None
            self.db = None

    def save_analysis(self, collection_name: str, data: Dict[str, Any]) -> bool:
        """Guarda un reporte completo en la colección especificada."""
        if self.db is None:
            logger.warning("⚠️ No hay conexión a DB. El guardado en Mongo será omitido.")
            return False
            
        try:
            collection = self.db[collection_name]
            # Usamos update_one con upsert para evitar duplicados si se re-escanea el mismo usuario
            # Basado en username y fecha (o solo username si quieres el más reciente)
            result = collection.update_one(
                {"profile.username": data.get("profile", {}).get("username")},
                {"$set": data},
                upsert=True
            )
            
            if result.upserted_id:
                logger.info(f"🆕 Nuevo registro creado en Mongo Atlas: {result.upserted_id}")
            else:
                logger.info(f"🔄 Registro existente actualizado en Mongo Atlas.")
            return True
        except Exception as e:
            logger.error(f"❌ Error guardando en Mongo: {e}")
            return False

    def close(self):
        if self.client:
            self.client.close()
