"""
HIPAA-Compliant Multi-Factor Authentication for Health Verify Now
Implements TOTP-based MFA with backup codes
"""

import pyotp
import qrcode
import io
import base64
from datetime import datetime, timedelta
import secrets
import uuid
from typing import Optional, List
import logging

logger = logging.getLogger(__name__)

class MFAManager:
    """Multi-Factor Authentication Manager"""
    
    def __init__(self, db):
        self.db = db
        self.issuer_name = "Health Verify Now"
    
    async def setup_mfa_for_user(self, user_id: str, user_email: str) -> dict:
        """Set up MFA for a user - generates secret and QR code"""
        try:
            # Generate TOTP secret
            secret = pyotp.random_base32()
            
            # Create TOTP instance
            totp = pyotp.TOTP(secret)
            
            # Generate provisioning URI for QR code
            provisioning_uri = totp.provisioning_uri(
                name=user_email,
                issuer_name=self.issuer_name
            )
            
            # Generate QR code
            qr = qrcode.QRCode(version=1, box_size=10, border=5)
            qr.add_data(provisioning_uri)
            qr.make(fit=True)
            
            # Convert QR code to base64 image
            img = qr.make_image(fill_color="black", back_color="white")
            img_buffer = io.BytesIO()
            img.save(img_buffer, format='PNG')
            img_buffer.seek(0)
            qr_code_base64 = base64.b64encode(img_buffer.getvalue()).decode()
            
            # Generate backup codes
            backup_codes = [secrets.token_hex(4).upper() for _ in range(10)]
            
            # Store MFA setup in database (not yet enabled)
            mfa_setup = {
                "user_id": user_id,
                "secret": secret,
                "backup_codes": backup_codes,
                "enabled": False,
                "setup_at": datetime.utcnow(),
                "last_used": None
            }
            
            await self.db.mfa_settings.replace_one(
                {"user_id": user_id},
                mfa_setup,
                upsert=True
            )
            
            logger.info(f"MFA setup initiated for user {user_id}")
            
            return {
                "secret": secret,
                "qr_code": f"data:image/png;base64,{qr_code_base64}",
                "backup_codes": backup_codes,
                "manual_entry_key": secret
            }
            
        except Exception as e:
            logger.error(f"MFA setup failed for user {user_id}: {e}")
            raise
    
    async def verify_and_enable_mfa(self, user_id: str, token: str) -> bool:
        """Verify MFA token and enable MFA for user"""
        try:
            # Get MFA settings
            mfa_settings = await self.db.mfa_settings.find_one({"user_id": user_id})
            if not mfa_settings:
                return False
            
            # Verify token
            if await self.verify_totp_token(user_id, token):
                # Enable MFA
                await self.db.mfa_settings.update_one(
                    {"user_id": user_id},
                    {
                        "$set": {
                            "enabled": True,
                            "enabled_at": datetime.utcnow()
                        }
                    }
                )
                
                # Update user record
                await self.db.users.update_one(
                    {"id": user_id},
                    {"$set": {"mfa_enabled": True}}
                )
                
                logger.info(f"MFA enabled for user {user_id}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"MFA verification failed for user {user_id}: {e}")
            return False
    
    async def verify_totp_token(self, user_id: str, token: str) -> bool:
        """Verify TOTP token"""
        try:
            mfa_settings = await self.db.mfa_settings.find_one({"user_id": user_id})
            if not mfa_settings or not mfa_settings.get("enabled", False):
                return False
            
            # Create TOTP instance
            totp = pyotp.TOTP(mfa_settings["secret"])
            
            # Verify token (allows for 30-second window)
            is_valid = totp.verify(token, valid_window=1)
            
            if is_valid:
                # Update last used timestamp
                await self.db.mfa_settings.update_one(
                    {"user_id": user_id},
                    {"$set": {"last_used": datetime.utcnow()}}
                )
                logger.info(f"Valid MFA token for user {user_id}")
            else:
                logger.warning(f"Invalid MFA token for user {user_id}")
            
            return is_valid
            
        except Exception as e:
            logger.error(f"MFA token verification failed for user {user_id}: {e}")
            return False
    
    async def verify_backup_code(self, user_id: str, backup_code: str) -> bool:
        """Verify and consume backup code"""
        try:
            mfa_settings = await self.db.mfa_settings.find_one({"user_id": user_id})
            if not mfa_settings:
                return False
            
            backup_codes = mfa_settings.get("backup_codes", [])
            backup_code_upper = backup_code.upper()
            
            if backup_code_upper in backup_codes:
                # Remove used backup code
                backup_codes.remove(backup_code_upper)
                
                await self.db.mfa_settings.update_one(
                    {"user_id": user_id},
                    {
                        "$set": {
                            "backup_codes": backup_codes,
                            "last_used": datetime.utcnow()
                        }
                    }
                )
                
                logger.info(f"Backup code used for user {user_id}")
                return True
            
            logger.warning(f"Invalid backup code for user {user_id}")
            return False
            
        except Exception as e:
            logger.error(f"Backup code verification failed for user {user_id}: {e}")
            return False
    
    async def is_mfa_enabled(self, user_id: str) -> bool:
        """Check if MFA is enabled for user"""
        try:
            mfa_settings = await self.db.mfa_settings.find_one({"user_id": user_id})
            return mfa_settings and mfa_settings.get("enabled", False)
        except Exception as e:
            logger.error(f"MFA status check failed for user {user_id}: {e}")
            return False
    
    async def disable_mfa(self, user_id: str) -> bool:
        """Disable MFA for user (admin function)"""
        try:
            await self.db.mfa_settings.update_one(
                {"user_id": user_id},
                {
                    "$set": {
                        "enabled": False,
                        "disabled_at": datetime.utcnow()
                    }
                }
            )
            
            await self.db.users.update_one(
                {"id": user_id},
                {"$set": {"mfa_enabled": False}}
            )
            
            logger.info(f"MFA disabled for user {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"MFA disable failed for user {user_id}: {e}")
            return False
    
    async def regenerate_backup_codes(self, user_id: str) -> List[str]:
        """Regenerate backup codes for user"""
        try:
            new_backup_codes = [secrets.token_hex(4).upper() for _ in range(10)]
            
            await self.db.mfa_settings.update_one(
                {"user_id": user_id},
                {
                    "$set": {
                        "backup_codes": new_backup_codes,
                        "backup_codes_regenerated_at": datetime.utcnow()
                    }
                }
            )
            
            logger.info(f"Backup codes regenerated for user {user_id}")
            return new_backup_codes
            
        except Exception as e:
            logger.error(f"Backup code regeneration failed for user {user_id}: {e}")
            raise