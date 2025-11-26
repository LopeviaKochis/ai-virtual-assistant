import pandas as pd
from typing import Optional, Tuple
from models.user_profile import UserProfile
from clients.azure_client import search_debt_by_dni, search_otp_by_phone
import logging

logger = logging.getLogger(__name__)

class MatchingService:
    """Servicio para hacer matching entre perfiles y Azure Search."""
    
    def find_debt_info(self, profile: UserProfile) -> Optional[pd.DataFrame]:
        """Busca información de deuda usando DNI del perfil."""
        if not profile.dni:
            logger.warning(f"Profile {profile.contactId} has no DNI")
            return None
        
        df = search_debt_by_dni(profile.dni)
        
        if df.empty:
            logger.info(f"No debt found for DNI {profile.dni}")
            return None
        
        logger.info(f"Debt info found for {profile.dni}: {len(df)} records")
        return df
    
    def find_otp_code(self, profile: UserProfile) -> Optional[pd.DataFrame]:
        """Busca código OTP usando teléfono del perfil."""
        if not profile.phone:
            logger.warning(f"Profile {profile.contactId} has no phone")
            return None
        
        df = search_otp_by_phone(profile.phone)
        
        if df.empty:
            logger.info(f"No OTP found for phone {profile.phone}")
            return None
        
        logger.info(f"OTP found for {profile.phone}")
        return df
    
    def auto_match_profile(self, profile: UserProfile) -> Tuple[bool, str]:
        """
        Intenta hacer matching automático.
        
        Returns:
            (success, message)
        """
        if profile.dni:
            df = self.find_debt_info(profile)
            if df is not None and not df.empty:
                return (True, "debt_found")
        
        if profile.phone:
            df = self.find_otp_code(profile)
            if df is not None and not df.empty:
                return (True, "otp_found")
        
        return (False, "no_match")

matching_service = MatchingService()
