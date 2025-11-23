"""
Audit Logging System
Comprehensive logging for all banking operations and agent decisions
"""
from datetime import datetime
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
import logging
import json

from database.models import AuditLog
from database.connection import db_manager

logger = logging.getLogger(__name__)


class AuditLogger:
    """Audit logging for banking operations"""
    
    def log_event(
        self,
        event_type: str,
        action: str,
        entity_type: Optional[str] = None,
        entity_id: Optional[str] = None,
        user_id: Optional[str] = None,
        agent_name: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        status: str = "success",
        error_message: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        db: Optional[Session] = None
    ) -> AuditLog:
        """
        Log an audit event
        
        Args:
            event_type: Type of event (e.g., account_creation, transaction, card_application)
            action: Specific action taken
            entity_type: Type of entity affected (customer, account, transaction, card)
            entity_id: ID of the entity
            user_id: ID of the user (if applicable)
            agent_name: Name of the AI agent performing the action
            details: Additional details as JSON
            status: Status of the operation (success, failure)
            error_message: Error message if failed
            ip_address: IP address of the request
            user_agent: User agent string
            db: Database session (optional)
            
        Returns:
            Created AuditLog instance
        """
        try:
            audit_log = AuditLog(
                event_type=event_type,
                entity_type=entity_type,
                entity_id=entity_id,
                user_id=user_id,
                agent_name=agent_name,
                action=action,
                details=details,
                ip_address=ip_address,
                user_agent=user_agent,
                status=status,
                error_message=error_message
            )
            
            # Use provided session or create new one
            if db:
                db.add(audit_log)
                db.flush()
            else:
                with db_manager.get_session() as session:
                    session.add(audit_log)
                    session.flush()
            
            logger.info(f"Audit log created: {event_type} - {action} - {status}")
            return audit_log
            
        except Exception as e:
            logger.error(f"Failed to create audit log: {e}")
            # Don't raise exception - audit logging should not break main flow
            return None
    
    def log_account_creation(
        self,
        account_id: str,
        customer_id: str,
        agent_name: str,
        details: Dict[str, Any],
        db: Optional[Session] = None
    ):
        """Log account creation event"""
        return self.log_event(
            event_type="account_creation",
            action="create_account",
            entity_type="account",
            entity_id=account_id,
            user_id=customer_id,
            agent_name=agent_name,
            details=details,
            db=db
        )
    
    def log_transaction(
        self,
        transaction_id: str,
        account_id: str,
        agent_name: str,
        transaction_type: str,
        amount: float,
        details: Dict[str, Any],
        db: Optional[Session] = None
    ):
        """Log transaction event"""
        return self.log_event(
            event_type="transaction",
            action=f"{transaction_type}_transaction",
            entity_type="transaction",
            entity_id=transaction_id,
            agent_name=agent_name,
            details={
                **details,
                "account_id": account_id,
                "amount": amount,
                "transaction_type": transaction_type
            },
            db=db
        )
    
    def log_card_application(
        self,
        card_id: str,
        customer_id: str,
        agent_name: str,
        card_type: str,
        status: str,
        details: Dict[str, Any],
        db: Optional[Session] = None
    ):
        """Log card application event"""
        return self.log_event(
            event_type="card_application",
            action=f"apply_{card_type}_card",
            entity_type="card",
            entity_id=card_id,
            user_id=customer_id,
            agent_name=agent_name,
            status=status,
            details={
                **details,
                "card_type": card_type
            },
            db=db
        )
    
    def log_kyc_verification(
        self,
        customer_id: str,
        agent_name: str,
        verification_status: str,
        details: Dict[str, Any],
        db: Optional[Session] = None
    ):
        """Log KYC verification event"""
        return self.log_event(
            event_type="kyc_verification",
            action="verify_kyc",
            entity_type="customer",
            entity_id=customer_id,
            agent_name=agent_name,
            status=verification_status,
            details=details,
            db=db
        )
    
    def log_fraud_detection(
        self,
        entity_type: str,
        entity_id: str,
        fraud_score: float,
        risk_level: str,
        details: Dict[str, Any],
        db: Optional[Session] = None
    ):
        """Log fraud detection event"""
        return self.log_event(
            event_type="fraud_detection",
            action="detect_fraud",
            entity_type=entity_type,
            entity_id=entity_id,
            agent_name="FraudDetectionAgent",
            details={
                **details,
                "fraud_score": fraud_score,
                "risk_level": risk_level
            },
            db=db
        )
    
    def log_agent_decision(
        self,
        agent_name: str,
        decision: str,
        entity_type: str,
        entity_id: str,
        reasoning: str,
        confidence: float,
        details: Optional[Dict[str, Any]] = None,
        db: Optional[Session] = None
    ):
        """Log AI agent decision"""
        return self.log_event(
            event_type="agent_decision",
            action=decision,
            entity_type=entity_type,
            entity_id=entity_id,
            agent_name=agent_name,
            details={
                **(details or {}),
                "decision": decision,
                "reasoning": reasoning,
                "confidence": confidence
            },
            db=db
        )


# Global audit logger instance
audit_logger = AuditLogger()


def log_audit_event(
    event_type: str,
    action: str,
    agent_name: str = None,
    **kwargs
):
    """Convenience function to log audit event"""
    return audit_logger.log_event(
        event_type=event_type,
        action=action,
        agent_name=agent_name,
        **kwargs
    )
