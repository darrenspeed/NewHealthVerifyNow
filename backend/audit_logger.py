"""
HIPAA-Compliant Audit Logging System for Health Verify Now
Comprehensive activity tracking and monitoring
"""

import uuid
from datetime import datetime
from typing import Optional, Dict, Any, List
import logging
from enum import Enum
import json

logger = logging.getLogger(__name__)

class AuditEventType(str, Enum):
    # Authentication Events
    USER_LOGIN = "user_login"
    USER_LOGOUT = "user_logout"
    LOGIN_FAILED = "login_failed"
    MFA_SETUP = "mfa_setup"
    MFA_VERIFICATION = "mfa_verification"
    
    # PHI Access Events
    PHI_ACCESS = "phi_access"
    PHI_MODIFICATION = "phi_modification"
    PHI_CREATION = "phi_creation"
    PHI_DELETION = "phi_deletion"
    PHI_EXPORT = "phi_export"
    
    # Employee Management
    EMPLOYEE_CREATED = "employee_created"
    EMPLOYEE_UPDATED = "employee_updated"
    EMPLOYEE_DELETED = "employee_deleted"
    EMPLOYEE_VIEWED = "employee_viewed"
    
    # Verification Events
    VERIFICATION_PERFORMED = "verification_performed"
    VERIFICATION_RESULTS_ACCESSED = "verification_results_accessed"
    BATCH_VERIFICATION = "batch_verification"
    
    # Administrative Events
    ADMIN_ACTION = "admin_action"
    USER_CREATED = "user_created"
    USER_UPDATED = "user_updated"
    USER_DELETED = "user_deleted"
    ROLE_CHANGED = "role_changed"
    
    # System Events
    SYSTEM_ACCESS = "system_access"
    DATA_BACKUP = "data_backup"
    DATA_RESTORE = "data_restore"
    CONFIGURATION_CHANGE = "configuration_change"
    
    # Security Events
    UNAUTHORIZED_ACCESS_ATTEMPT = "unauthorized_access_attempt"
    SUSPICIOUS_ACTIVITY = "suspicious_activity"
    SECURITY_ALERT = "security_alert"
    PASSWORD_CHANGED = "password_changed"

class AuditOutcome(str, Enum):
    SUCCESS = "success"
    FAILURE = "failure"
    WARNING = "warning"
    ERROR = "error"

class HIPAAAuditLogger:
    """HIPAA-compliant audit logging system"""
    
    def __init__(self, db):
        self.db = db
        self.collection = "audit_logs"
    
    async def log_event(
        self,
        event_type: AuditEventType,
        user_id: Optional[str] = None,
        outcome: AuditOutcome = AuditOutcome.SUCCESS,
        details: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        session_id: Optional[str] = None,
        resource_id: Optional[str] = None,
        resource_type: Optional[str] = None
    ):
        """Log HIPAA audit event"""
        try:
            audit_record = {
                "id": str(uuid.uuid4()),
                "timestamp": datetime.utcnow(),
                "event_type": event_type.value,
                "user_id": user_id,
                "outcome": outcome.value,
                "ip_address": ip_address,
                "user_agent": user_agent,
                "session_id": session_id,
                "resource_id": resource_id,
                "resource_type": resource_type,
                "details": details or {},
                "created_at": datetime.utcnow()
            }
            
            # Store in audit collection
            await self.db[self.collection].insert_one(audit_record)
            
            # Check for suspicious activity
            await self._check_suspicious_activity(audit_record)
            
            # Log to system logger for real-time monitoring
            logger.info(f"AUDIT: {event_type.value} - User: {user_id} - Outcome: {outcome.value}")
            
        except Exception as e:
            # Audit logging failures are critical - log to system
            logger.critical(f"AUDIT LOG FAILURE: {e} - Event: {event_type.value}")
            raise
    
    async def log_phi_access(
        self,
        user_id: str,
        employee_id: str,
        fields_accessed: List[str],
        action: str,
        outcome: AuditOutcome = AuditOutcome.SUCCESS,
        ip_address: Optional[str] = None,
        session_id: Optional[str] = None
    ):
        """Log PHI access events with detailed field tracking"""
        await self.log_event(
            event_type=AuditEventType.PHI_ACCESS,
            user_id=user_id,
            outcome=outcome,
            details={
                "employee_id": employee_id,
                "fields_accessed": fields_accessed,
                "action": action,
                "phi_fields_count": len(fields_accessed)
            },
            ip_address=ip_address,
            session_id=session_id,
            resource_id=employee_id,
            resource_type="employee"
        )
    
    async def log_verification_event(
        self,
        user_id: str,
        employee_id: str,
        verification_types: List[str],
        outcome: AuditOutcome = AuditOutcome.SUCCESS,
        results_summary: Optional[Dict] = None,
        ip_address: Optional[str] = None,
        session_id: Optional[str] = None
    ):
        """Log employee verification events"""
        await self.log_event(
            event_type=AuditEventType.VERIFICATION_PERFORMED,
            user_id=user_id,
            outcome=outcome,
            details={
                "employee_id": employee_id,
                "verification_types": verification_types,
                "verification_count": len(verification_types),
                "results_summary": results_summary or {}
            },
            ip_address=ip_address,
            session_id=session_id,
            resource_id=employee_id,
            resource_type="verification"
        )
    
    async def log_authentication_event(
        self,
        event_type: AuditEventType,
        user_id: Optional[str],
        outcome: AuditOutcome,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        details: Optional[Dict] = None
    ):
        """Log authentication-related events"""
        await self.log_event(
            event_type=event_type,
            user_id=user_id,
            outcome=outcome,
            details=details or {},
            ip_address=ip_address,
            user_agent=user_agent
        )
    
    async def log_admin_action(
        self,
        admin_user_id: str,
        action: str,
        target_resource: Optional[str] = None,
        changes: Optional[Dict] = None,
        outcome: AuditOutcome = AuditOutcome.SUCCESS,
        ip_address: Optional[str] = None,
        session_id: Optional[str] = None
    ):
        """Log administrative actions"""
        await self.log_event(
            event_type=AuditEventType.ADMIN_ACTION,
            user_id=admin_user_id,
            outcome=outcome,
            details={
                "action": action,
                "target_resource": target_resource,
                "changes": changes or {},
                "admin_level_action": True
            },
            ip_address=ip_address,
            session_id=session_id,
            resource_id=target_resource,
            resource_type="admin"
        )
    
    async def _check_suspicious_activity(self, audit_record: Dict):
        """Check for suspicious activity patterns"""
        try:
            user_id = audit_record.get("user_id")
            if not user_id:
                return
            
            # Check for multiple failed logins
            if audit_record["event_type"] == AuditEventType.LOGIN_FAILED.value:
                recent_failures = await self._count_recent_failures(user_id)
                if recent_failures >= 5:
                    await self._trigger_security_alert(
                        "Multiple failed login attempts",
                        user_id,
                        {"failure_count": recent_failures}
                    )
            
            # Check for unusual access patterns
            if audit_record["event_type"] == AuditEventType.PHI_ACCESS.value:
                await self._check_unusual_phi_access(user_id, audit_record)
            
            # Check for after-hours access
            current_hour = datetime.utcnow().hour
            if current_hour < 6 or current_hour > 22:  # Outside business hours
                await self._trigger_security_alert(
                    "After-hours system access",
                    user_id,
                    {"access_time": audit_record["timestamp"].isoformat()}
                )
        
        except Exception as e:
            logger.error(f"Suspicious activity check failed: {e}")
    
    async def _count_recent_failures(self, user_id: str, minutes: int = 30) -> int:
        """Count recent login failures for user"""
        try:
            since_time = datetime.utcnow() - timedelta(minutes=minutes)
            count = await self.db[self.collection].count_documents({
                "user_id": user_id,
                "event_type": AuditEventType.LOGIN_FAILED.value,
                "timestamp": {"$gte": since_time}
            })
            return count
        except Exception as e:
            logger.error(f"Failed to count recent failures: {e}")
            return 0
    
    async def _check_unusual_phi_access(self, user_id: str, audit_record: Dict):
        """Check for unusual PHI access patterns"""
        try:
            # Check if user is accessing more PHI than usual
            recent_access_count = await self._count_recent_phi_access(user_id)
            if recent_access_count > 50:  # Configurable threshold
                await self._trigger_security_alert(
                    "Unusual PHI access volume",
                    user_id,
                    {"access_count": recent_access_count}
                )
        except Exception as e:
            logger.error(f"PHI access pattern check failed: {e}")
    
    async def _count_recent_phi_access(self, user_id: str, hours: int = 1) -> int:
        """Count recent PHI access events for user"""
        try:
            since_time = datetime.utcnow() - timedelta(hours=hours)
            count = await self.db[self.collection].count_documents({
                "user_id": user_id,
                "event_type": AuditEventType.PHI_ACCESS.value,
                "timestamp": {"$gte": since_time}
            })
            return count
        except Exception as e:
            logger.error(f"Failed to count recent PHI access: {e}")
            return 0
    
    async def _trigger_security_alert(self, alert_type: str, user_id: str, details: Dict):
        """Trigger security alert"""
        try:
            # Log security alert
            await self.log_event(
                event_type=AuditEventType.SECURITY_ALERT,
                user_id=user_id,
                outcome=AuditOutcome.WARNING,
                details={
                    "alert_type": alert_type,
                    "alert_details": details,
                    "requires_investigation": True
                }
            )
            
            # In production, also send to security monitoring system
            logger.warning(f"SECURITY ALERT: {alert_type} - User: {user_id} - Details: {details}")
            
        except Exception as e:
            logger.error(f"Security alert failed: {e}")
    
    async def get_audit_trail(
        self,
        user_id: Optional[str] = None,
        event_type: Optional[AuditEventType] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100
    ) -> List[Dict]:
        """Retrieve audit trail with filters"""
        try:
            query = {}
            
            if user_id:
                query["user_id"] = user_id
            
            if event_type:
                query["event_type"] = event_type.value
            
            if start_date or end_date:
                timestamp_filter = {}
                if start_date:
                    timestamp_filter["$gte"] = start_date
                if end_date:
                    timestamp_filter["$lte"] = end_date
                query["timestamp"] = timestamp_filter
            
            cursor = self.db[self.collection].find(query).sort("timestamp", -1).limit(limit)
            return await cursor.to_list(length=limit)
            
        except Exception as e:
            logger.error(f"Audit trail retrieval failed: {e}")
            return []
    
    async def get_security_alerts(self, limit: int = 50) -> List[Dict]:
        """Get recent security alerts"""
        try:
            cursor = self.db[self.collection].find({
                "event_type": AuditEventType.SECURITY_ALERT.value
            }).sort("timestamp", -1).limit(limit)
            
            return await cursor.to_list(length=limit)
            
        except Exception as e:
            logger.error(f"Security alerts retrieval failed: {e}")
            return []

# Make datetime import available
from datetime import timedelta