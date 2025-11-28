"""
Compliance & AML AI Agent
Automated AML/KYC compliance monitoring and regulatory reporting
"""
from typing import Dict, Any, Optional, List
from decimal import Decimal
from datetime import datetime, timedelta
import logging
import uuid
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from agents.base_agent import BaseAgent
from database.models import Customer, KYCDocument, ComplianceCheck, Transaction
from utils.llm_client import llm_client

logger = logging.getLogger(__name__)


class ComplianceAgent(BaseAgent):
    """
    AI-powered compliance and AML monitoring
    Handles KYC verification, sanctions screening, and suspicious activity monitoring
    """
    
    # Sanctions lists (simplified - in production use OFAC, UN, EU lists)
    SANCTIONS_LIST = {
        "countries": ["DPRK", "IRN", "SYR"],  # Simplified sanctioned countries
        "entities": []  # Would include sanctioned individuals/entities
    }
    
    # PEP (Politically Exposed Persons) indicators
    PEP_KEYWORDS = [
        "minister", "senator", "governor", "ambassador", "general",
        "president", "prime minister", "chairman", "director general"
    ]
    
    # Suspicious activity patterns
    SUSPICIOUS_PATTERNS = {
        "structuring": {
            "threshold": Decimal("10000.00"),
            "window_days": 7,
            "min_transactions": 3
        },
        "large_cash": {
            "threshold": Decimal("10000.00")
        },
        "rapid_movement": {
            "threshold": Decimal("25000.00"),
            "window_hours": 24
        }
    }
    
    def __init__(self):
        super().__init__(
            name="ComplianceAgent",
            description="AI agent specialized in AML/KYC compliance and regulatory monitoring"
        )
    
    def process(
        self,
        query: str,
        context: Dict[str, any],
        session_id: str
    ) -> Dict[str, Any]:
        """Process compliance check request"""
        
        check_type = context.get("check_type", "kyc")
        customer_id = context.get("customer_id")
        
        if not customer_id:
            return self.create_response(
                answer="I need a customer ID to perform compliance checks.",
                success=False
            )
        
        try:
            db = context.get("db")
            if not db:
                raise ValueError("Database session not available")
            
            if check_type == "kyc":
                result = self.verify_kyc(db, uuid.UUID(customer_id))
                response = self._format_kyc_response(result)
            elif check_type == "sanctions":
                result = self.screen_sanctions(db, uuid.UUID(customer_id))
                response = self._format_sanctions_response(result)
            elif check_type == "aml":
                result = self.monitor_aml(db, uuid.UUID(customer_id))
                response = self._format_aml_response(result)
            else:
                result = self.comprehensive_compliance_check(db, uuid.UUID(customer_id))
                response = self._format_comprehensive_response(result)
            
            self.log_decision(
                decision=check_type,
                entity_type="customer",
                entity_id=customer_id,
                reasoning=result.get("summary", ""),
                confidence=result.get("confidence", 0.8),
                details=result,
                db=db
            )
            
            return self.create_response(
                answer=response,
                success=True,
                data=result
            )
            
        except Exception as e:
            return self.handle_error(e, query)
    
    def verify_kyc(
        self,
        db: Session,
        customer_id: uuid.UUID
    ) -> Dict[str, Any]:
        """
        Verify KYC documentation and status
        Checks for completeness and validity of customer documents
        """
        customer = db.query(Customer).filter(Customer.id == customer_id).first()
        if not customer:
            raise ValueError(f"Customer not found: {customer_id}")
        
        # Get KYC documents
        documents = db.query(KYCDocument).filter(
            KYCDocument.customer_id == customer_id
        ).all()
        
        # Required document types
        required_docs = ["id_proof", "address_proof", "photo"]
        
        # Check document completeness
        submitted_types = {doc.document_type for doc in documents}
        missing_docs = set(required_docs) - submitted_types
        
        # Check document verification status
        verified_docs = [
            doc for doc in documents 
            if doc.verification_status == "verified"
        ]
        
        pending_docs = [
            doc for doc in documents 
            if doc.verification_status == "pending"
        ]
        
        rejected_docs = [
            doc for doc in documents 
            if doc.verification_status == "rejected"
        ]
        
        # Calculate KYC score
        kyc_score = self._calculate_kyc_score(
            len(verified_docs), len(required_docs), len(rejected_docs)
        )
        
        # Determine KYC status
        if len(verified_docs) == len(required_docs):
            kyc_status = "verified"
            risk_level = "low"
        elif len(verified_docs) >= len(required_docs) * 0.66:
            kyc_status = "partial"
            risk_level = "medium"
        else:
            kyc_status = "pending"
            risk_level = "high"
        
        # Update customer KYC status
        customer.kyc_status = kyc_status
        if kyc_status == "verified":
            customer.kyc_verified_at = datetime.utcnow()
        
        # Create compliance check record
        check = ComplianceCheck(
            check_id=f"KYC{uuid.uuid4().hex[:12].upper()}",
            customer_id=customer_id,
            check_type="kyc_verification",
            check_category="identity",
            status="completed",
            result=kyc_status,
            risk_level=risk_level,
            score=kyc_score,
            details={
                "verified_docs": len(verified_docs),
                "pending_docs": len(pending_docs),
                "rejected_docs": len(rejected_docs),
                "missing_docs": list(missing_docs)
            },
            checked_by="ComplianceAgent",
            checked_at=datetime.utcnow()
        )
        db.add(check)
        db.commit()
        
        return {
            "kyc_status": kyc_status,
            "kyc_score": float(kyc_score),
            "risk_level": risk_level,
            "verified_documents": len(verified_docs),
            "pending_documents": len(pending_docs),
            "rejected_documents": len(rejected_docs),
            "missing_documents": list(missing_docs),
            "confidence": 0.9
        }
    
    def screen_sanctions(
        self,
        db: Session,
        customer_id: uuid.UUID
    ) -> Dict[str, Any]:
        """
        Screen customer against sanctions lists
        Checks OFAC, UN, and other watchlists
        """
        customer = db.query(Customer).filter(Customer.id == customer_id).first()
        if not customer:
            raise ValueError(f"Customer not found: {customer_id}")
        
        # Sanctions screening (simplified)
        sanctions_hit = False
        pep_match = False
        adverse_media = False
        matches = []
        
        # Check country sanctions
        if customer.nationality in self.SANCTIONS_LIST["countries"]:
            sanctions_hit = True
            matches.append({
                "type": "country",
                "value": customer.nationality,
                "list": "OFAC SDN"
            })
        
        # Check PEP indicators (simplified name matching)
        full_name = f"{customer.first_name} {customer.last_name}".lower()
        for keyword in self.PEP_KEYWORDS:
            if keyword in full_name:
                pep_match = True
                matches.append({
                    "type": "pep",
                    "value": keyword,
                    "list": "PEP Database"
                })
        
        # Determine result
        if sanctions_hit:
            result = "hit"
            risk_level = "critical"
        elif pep_match:
            result = "pep"
            risk_level = "high"
        else:
            result = "clear"
            risk_level = "low"
        
        # Create compliance check
        check = ComplianceCheck(
            check_id=f"SAN{uuid.uuid4().hex[:12].upper()}",
            customer_id=customer_id,
            check_type="sanctions_screening",
            check_category="compliance",
            status="completed",
            result=result,
            risk_level=risk_level,
            score=Decimal("1.0") if sanctions_hit else Decimal("0.0"),
            details={"matches": matches},
            sanctions_hit=sanctions_hit,
            pep_match=pep_match,
            adverse_media=adverse_media,
            checked_by="ComplianceAgent",
            checked_at=datetime.utcnow()
        )
        db.add(check)
        db.commit()
        
        return {
            "result": result,
            "sanctions_hit": sanctions_hit,
            "pep_match": pep_match,
            "adverse_media": adverse_media,
            "risk_level": risk_level,
            "matches": matches,
            "confidence": 0.85
        }
    
    def monitor_aml(
        self,
        db: Session,
        customer_id: uuid.UUID
    ) -> Dict[str, Any]:
        """
        Monitor for suspicious activity and AML violations
        Detects structuring, large cash transactions, rapid fund movement
        """
        customer = db.query(Customer).filter(Customer.id == customer_id).first()
        if not customer:
            raise ValueError(f"Customer not found: {customer_id}")
        
        # Get customer accounts
        from database.models import Account
        accounts = db.query(Account).filter(Account.customer_id == customer_id).all()
        account_ids = [acc.id for acc in accounts]
        
        suspicious_patterns = []
        
        # Check for structuring (multiple transactions under reporting threshold)
        structuring = self._detect_structuring(db, account_ids)
        if structuring["detected"]:
            suspicious_patterns.append(structuring)
        
        # Check for large cash transactions
        large_cash = self._detect_large_cash(db, account_ids)
        if large_cash["detected"]:
            suspicious_patterns.append(large_cash)
        
        # Check for rapid fund movement
        rapid_movement = self._detect_rapid_movement(db, account_ids)
        if rapid_movement["detected"]:
            suspicious_patterns.append(rapid_movement)
        
        # Determine if SAR (Suspicious Activity Report) is needed
        sar_required = len(suspicious_patterns) > 0
        risk_level = "high" if sar_required else "low"
        
        # Create compliance check
        check = ComplianceCheck(
            check_id=f"AML{uuid.uuid4().hex[:12].upper()}",
            customer_id=customer_id,
            check_type="aml_monitoring",
            check_category="transaction_monitoring",
            status="completed",
            result="suspicious" if sar_required else "normal",
            risk_level=risk_level,
            score=Decimal(str(len(suspicious_patterns) * 0.3)),
            details={
                "patterns": suspicious_patterns,
                "sar_required": sar_required
            },
            checked_by="ComplianceAgent",
            checked_at=datetime.utcnow()
        )
        db.add(check)
        db.commit()
        
        return {
            "sar_required": sar_required,
            "risk_level": risk_level,
            "suspicious_patterns": suspicious_patterns,
            "pattern_count": len(suspicious_patterns),
            "confidence": 0.8
        }
    
    def comprehensive_compliance_check(
        self,
        db: Session,
        customer_id: uuid.UUID
    ) -> Dict[str, Any]:
        """Run all compliance checks"""
        kyc_result = self.verify_kyc(db, customer_id)
        sanctions_result = self.screen_sanctions(db, customer_id)
        aml_result = self.monitor_aml(db, customer_id)
        
        # Determine overall compliance status
        issues = []
        if kyc_result["kyc_status"] != "verified":
            issues.append("KYC not verified")
        if sanctions_result["sanctions_hit"]:
            issues.append("Sanctions hit")
        if sanctions_result["pep_match"]:
            issues.append("PEP match")
        if aml_result["sar_required"]:
            issues.append("Suspicious activity detected")
        
        overall_status = "compliant" if not issues else "non_compliant"
        risk_level = max(
            kyc_result["risk_level"],
            sanctions_result["risk_level"],
            aml_result["risk_level"],
            key=lambda x: ["low", "medium", "high", "critical"].index(x)
        )
        
        return {
            "overall_status": overall_status,
            "risk_level": risk_level,
            "issues": issues,
            "kyc": kyc_result,
            "sanctions": sanctions_result,
            "aml": aml_result,
            "confidence": 0.85,
            "summary": f"Customer compliance status: {overall_status}. Risk level: {risk_level}."
        }
    
    def _calculate_kyc_score(
        self,
        verified_count: int,
        required_count: int,
        rejected_count: int
    ) -> Decimal:
        """Calculate KYC completeness score"""
        if required_count == 0:
            return Decimal("0.0")
        
        base_score = Decimal(str(verified_count)) / Decimal(str(required_count))
        penalty = Decimal(str(rejected_count)) * Decimal("0.1")
        
        return max(Decimal("0.0"), min(Decimal("1.0"), base_score - penalty))
    
    def _detect_structuring(
        self,
        db: Session,
        account_ids: List[uuid.UUID]
    ) -> Dict[str, Any]:
        """Detect structuring (smurfing) patterns"""
        threshold = self.SUSPICIOUS_PATTERNS["structuring"]["threshold"]
        window = self.SUSPICIOUS_PATTERNS["structuring"]["window_days"]
        min_txns = self.SUSPICIOUS_PATTERNS["structuring"]["min_transactions"]
        
        cutoff_date = datetime.utcnow() - timedelta(days=window)
        
        # Find transactions just below reporting threshold
        potential_structuring = db.query(Transaction).filter(
            and_(
                Transaction.account_id.in_(account_ids),
                Transaction.amount < threshold,
                Transaction.amount > threshold * Decimal("0.8"),
                Transaction.transaction_date >= cutoff_date
            )
        ).all()
        
        if len(potential_structuring) >= min_txns:
            return {
                "detected": True,
                "pattern": "structuring",
                "transaction_count": len(potential_structuring),
                "total_amount": float(sum(t.amount for t in potential_structuring)),
                "description": "Multiple transactions just below reporting threshold"
            }
        
        return {"detected": False}
    
    def _detect_large_cash(
        self,
        db: Session,
        account_ids: List[uuid.UUID]
    ) -> Dict[str, Any]:
        """Detect large cash transactions"""
        threshold = self.SUSPICIOUS_PATTERNS["large_cash"]["threshold"]
        
        large_txns = db.query(Transaction).filter(
            and_(
                Transaction.account_id.in_(account_ids),
                Transaction.amount >= threshold,
                Transaction.transaction_date >= datetime.utcnow() - timedelta(days=30)
            )
        ).all()
        
        if large_txns:
            return {
                "detected": True,
                "pattern": "large_cash",
                "transaction_count": len(large_txns),
                "total_amount": float(sum(t.amount for t in large_txns)),
                "description": f"Large cash transactions exceeding ${threshold:,.2f}"
            }
        
        return {"detected": False}
    
    def _detect_rapid_movement(
        self,
        db: Session,
        account_ids: List[uuid.UUID]
    ) -> Dict[str, Any]:
        """Detect rapid fund movement"""
        threshold = self.SUSPICIOUS_PATTERNS["rapid_movement"]["threshold"]
        window = self.SUSPICIOUS_PATTERNS["rapid_movement"]["window_hours"]
        
        cutoff = datetime.utcnow() - timedelta(hours=window)
        
        rapid_txns = db.query(Transaction).filter(
            and_(
                Transaction.account_id.in_(account_ids),
                Transaction.transaction_date >= cutoff
            )
        ).all()
        
        total_amount = sum(float(t.amount) for t in rapid_txns)
        
        if Decimal(str(total_amount)) >= threshold and len(rapid_txns) >= 2:
            return {
                "detected": True,
                "pattern": "rapid_movement",
                "transaction_count": len(rapid_txns),
                "total_amount": total_amount,
                "description": f"Rapid fund movement of ${total_amount:,.2f} within {window} hours"
            }
        
        return {"detected": False}
    
    def _format_kyc_response(self, result: Dict[str, Any]) -> str:
        """Format KYC verification response"""
        if result["kyc_status"] == "verified":
            return f"""✅ **KYC Verification Complete**

**Status:** Verified
**Score:** {result['kyc_score']:.2f}/1.00
**Risk Level:** {result['risk_level'].title()}

All required documents have been verified. Customer identity confirmed."""
        else:
            missing = ", ".join(result["missing_documents"]) if result["missing_documents"] else "None"
            return f"""⚠️ **KYC Verification Incomplete**

**Status:** {result['kyc_status'].title()}
**Score:** {result['kyc_score']:.2f}/1.00
**Risk Level:** {result['risk_level'].title()}

**Verified:** {result['verified_documents']} documents
**Pending:** {result['pending_documents']} documents
**Missing:** {missing}

Please complete KYC verification to proceed."""
    
    def _format_sanctions_response(self, result: Dict[str, Any]) -> str:
        """Format sanctions screening response"""
        if result["sanctions_hit"]:
            return f"""🚨 **SANCTIONS HIT**

**Result:** Sanctions Match Detected
**Risk Level:** CRITICAL

This customer matches sanctioned entities. Account activity must be blocked immediately.
Immediate escalation to compliance officer required."""
        elif result["pep_match"]:
            return f"""⚠️ **PEP Match Detected**

**Result:** Politically Exposed Person
**Risk Level:** High

Enhanced due diligence required for this customer."""
        else:
            return f"""✅ **Sanctions Screening Clear**

No matches found in sanctions lists. Customer cleared for normal operations."""
    
    def _format_aml_response(self, result: Dict[str, Any]) -> str:
        """Format AML monitoring response"""
if result["sar_required"]:
            patterns = "\n".join([
                f"• {p['pattern'].replace('_', ' ').title()}: {p['description']}"
                for p in result["suspicious_patterns"]
            ])
            return f"""🚨 **Suspicious Activity Detected**

**SAR Required:** Yes
**Risk Level:** {result['risk_level'].title()}
**Patterns Detected:** {result['pattern_count']}

{patterns}

A Suspicious Activity Report (SAR) must be filed with FinCEN."""
        else:
            return f"""✅ **AML Monitoring Clear**

No suspicious activity patterns detected. Account behavior within normal parameters."""
    
    def _format_comprehensive_response(self, result: Dict[str, Any]) -> str:
        """Format comprehensive compliance check response"""
        if result["overall_status"] == "compliant":
            return f"""✅ **Compliance Check Complete**

**Overall Status:** Compliant
**Risk Level:** {result['risk_level'].title()}

All compliance checks passed successfully."""
        else:
            issues = "\n".join([f"• {issue}" for issue in result["issues"]])
            return f"""⚠️ **Compliance Issues Detected**

**Overall Status:** Non-Compliant
**Risk Level:** {result['risk_level'].title()}

**Issues:**
{issues}

Please address these compliance issues immediately."""


# Global instance
compliance_agent = ComplianceAgent()
