from azure.cosmos import CosmosClient, PartitionKey, exceptions
from azure.cosmos.container import ContainerProxy
from typing import Optional, Dict, Any, List
from config.settings import settings
import logging

logger = logging.getLogger(__name__)

class CosmosDBClient:
    """
    Cliente para gestionar perfiles de usuario en Cosmos DB.
    
    Partition Key: contactId (Contact ID de Respond.io)
    Database: assistantdb
    Container: user_profiles
    """
    
    def __init__(self):
        """Inicializa cliente y valida configuración."""
        if not all([settings.COSMOS_ENDPOINT, settings.COSMOS_KEY]):
            logger.warning("Cosmos DB credentials not configured")
            self.client = None
            self.container = None
            return
        
        try:
            self.client = CosmosClient(
                settings.COSMOS_ENDPOINT, 
                credential=settings.COSMOS_KEY
            )
            self.database = self.client.get_database_client(settings.COSMOS_DATABASE)
            self.container: ContainerProxy = self.database.get_container_client(
                settings.COSMOS_CONTAINER
            )
            logger.info("Cosmos DB client initialized successfully")
        except Exception as e:
            logger.exception(f"Failed to initialize Cosmos DB client: {e}")
            self.client = None
            self.container = None
    
    def _is_configured(self) -> bool:
        """Verifica si el cliente está configurado correctamente."""
        return self.container is not None
    
    def get_profile(self, contact_id: str) -> Optional[Dict[str, Any]]:
        """
        Obtiene perfil por Contact ID.
        
        Args:
            contact_id: Contact ID de Respond.io (partition key)
            
        Returns:
            Diccionario con datos del perfil o None si no existe
        """
        if not self._is_configured():
            logger.warning("Cosmos DB not configured, skipping get_profile")
            return None
        
        try:
            # read_item requiere el ID y la partition key
            item = self.container.read_item(
                item=contact_id,
                partition_key=contact_id
            )
            logger.debug(f"Profile retrieved for contactId: {contact_id}")
            return item
        
        except exceptions.CosmosResourceNotFoundError:
            logger.debug(f"Profile not found for contactId: {contact_id}")
            return None
        
        except Exception as e:
            logger.exception(f"Error retrieving profile for {contact_id}: {e}")
            return None
    
    def upsert_profile(self, profile: Dict[str, Any]) -> Dict[str, Any]:
        """
        Crea o actualiza perfil usando upsert.
        
        Args:
            profile: Diccionario con datos del perfil (debe incluir 'id' y 'contactId')
            
        Returns:
            Perfil actualizado con metadata de Cosmos DB
            
        Raises:
            ValueError: Si falta contactId en el perfil
        """
        if not self._is_configured():
            logger.warning("Cosmos DB not configured, skipping upsert_profile")
            return profile
        
        contact_id = profile.get("contactId")
        if not contact_id:
            raise ValueError("Profile must include 'contactId' field")
        
        # Asegurar que 'id' esté presente (Cosmos DB requirement)
        if "id" not in profile:
            profile["id"] = contact_id

        serializable_profile = self._serialize_for_cosmos(profile)
        
        try:
            result = self.container.upsert_item(body=serializable_profile)
            logger.info(f"Profile upserted for contactId: {contact_id}")
            return result
        
        except Exception as e:
            logger.exception(f"Error upserting profile for {contact_id}: {e}")
            raise
    
    def _serialize_for_cosmos(self, profile: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convierte campos datetime a ISO string para Cosmos DB
        Args:
            profile: Perfil con campos datetime
        Returns:
            Perfil con datetimes convertidos a string
        """
        from datetime import datetime

        serialized = {}
        for key, value in profile.items():
            if isinstance(value, datetime):
                serialized[key] = value.isoformat()
            else:
                serialized[key] = value
                
        return serialized
    
    def find_by_dni(self, dni: str) -> Optional[Dict[str, Any]]:
        """
        Busca perfil por DNI usando query SQL.
        
        Args:
            dni: DNI del usuario (8 dígitos)
            
        Returns:
            Primer perfil que coincida o None
        """
        if not self._is_configured():
            logger.warning("Cosmos DB not configured, skipping find_by_dni")
            return None
        
        try:
            query = "SELECT * FROM c WHERE c.dni = @dni"
            parameters = [{"name": "@dni", "value": dni}]
            
            items = list(self.container.query_items(
                query=query,
                parameters=parameters,
                enable_cross_partition_query=True
            ))
            
            if items:
                logger.debug(f"Profile found for DNI: {dni}")
                return items[0]
            
            logger.debug(f"No profile found for DNI: {dni}")
            return None
        
        except Exception as e:
            logger.exception(f"Error searching by DNI {dni}: {e}")
            return None
    
    def find_by_phone(self, phone: str) -> Optional[Dict[str, Any]]:
        """
        Busca perfil por teléfono usando query SQL.
        
        Args:
            phone: Teléfono del usuario (9 dígitos)
            
        Returns:
            Primer perfil que coincida o None
        """
        if not self._is_configured():
            logger.warning("Cosmos DB not configured, skipping find_by_phone")
            return None
        
        try:
            query = "SELECT * FROM c WHERE c.phone = @phone"
            parameters = [{"name": "@phone", "value": phone}]
            
            items = list(self.container.query_items(
                query=query,
                parameters=parameters,
                enable_cross_partition_query=True
            ))
            
            if items:
                logger.debug(f"Profile found for phone: {phone}")
                return items[0]
            
            logger.debug(f"No profile found for phone: {phone}")
            return None
        
        except Exception as e:
            logger.exception(f"Error searching by phone {phone}: {e}")
            return None
    
    def delete_profile(self, contact_id: str) -> bool:
        """
        Elimina un perfil (útil para testing).
        
        Args:
            contact_id: Contact ID del perfil a eliminar
            
        Returns:
            True si se eliminó correctamente
        """
        if not self._is_configured():
            logger.warning("Cosmos DB not configured, skipping delete_profile")
            return False
        
        try:
            self.container.delete_item(
                item=contact_id,
                partition_key=contact_id
            )
            logger.info(f"Profile deleted for contactId: {contact_id}")
            return True
        
        except exceptions.CosmosResourceNotFoundError:
            logger.warning(f"Profile not found for deletion: {contact_id}")
            return False
        
        except Exception as e:
            logger.exception(f"Error deleting profile {contact_id}: {e}")
            return False
    
    def list_all_profiles(self, max_items: int = 100) -> List[Dict[str, Any]]:
        """
        Lista todos los perfiles (útil para debugging).
        
        Args:
            max_items: Límite de perfiles a retornar
            
        Returns:
            Lista de perfiles
        """
        if not self._is_configured():
            logger.warning("Cosmos DB not configured, skipping list_all_profiles")
            return []
        
        try:
            query = "SELECT * FROM c"
            items = list(self.container.query_items(
                query=query,
                enable_cross_partition_query=True,
                max_item_count=max_items
            ))
            logger.debug(f"Retrieved {len(items)} profiles")
            return items
        
        except Exception as e:
            logger.exception(f"Error listing profiles: {e}")
            return []

# Cliente singleton
cosmos_client = CosmosDBClient()
