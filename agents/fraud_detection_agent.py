"""
Fraud Detection AI Agent
Real-time fraud detection using ML models and rule-based systems
"""
from typing import Dict, Any, Optional, List
from decimal import Decimal
from datetime import datetime, timedelta
import logging
import uuid
from sqlalchemy.orm import Session
from sqlalchemy import func, and_

from agents.base_agent import BaseAgent
from database.models import Transaction, Account, Customer, FraudAlert, FraudScore
from utils.llm_client import llm_client

logger = logging.getLogger(__name__)


class FraudDetectionAgent(BaseAgent):
    """
    AI-powered fraud detection and prevention
    Uses ML models and rule-based systems for real-time fraud scoring
    """
    
    # Fraud rules and thresholds
    RULES = {
        "high_amount": {
            "threshold": Decimal("1000.00"),
            "weight": 0.3
        },
        "velocity": {
            "max_transactions_per_hour": 10,
            "max_amount_per_hour": Decimal("5000.00"),
            "weight": 0.4
        },
        "unusual_time": {
            "night_hours": (0, 5),  # 12 AM - 5 AM
            "weight": 0.1
        },
        "geographic_anomaly": {
            "weight": 0.2
        }
    }
    
    # Risk thresholds
    RISK_THRESHOLDS = {
        "low": 0.3,
        "medium": 0.5,
        "high": 0.7,
        "critical": 0.9
    }
    
    def __init__(self):
        super().__init__(
            name="FraudDetectionAgent",
            description="AI agent specialized in fraud detection and prevention"
        )
    
    def process(
        self,
        query: str,
        context: Dict[str, Any],
        session_id: str
    ) -> Dict[str, Any]:
        """Process fraud detection request"""
        
        transaction_id = context.get("transaction_id")
        if not transaction_id:
            return self.create_response(
                answer="I need a transaction ID to analyze for fraud.",
                success=False
            )
        
        try:
            db = context.get("db")
            if not db:
                raise ValueError("Database session not available")
            
            # Analyze transaction for fraud
            fraud_analysis = self.analyze_transaction(
                db=db,
                transaction_id=uuid.UUID(transaction_id)
            )
            
            # Generate response based on fraud score
            if fraud_analysis["fraud_score"] >= self.RISK_THRESHOLDS["high"]:
                response = f"""🚨 **High Fraud Risk Detected**

**Transaction ID:** {transaction_id}
**Fraud Score:** {fraud_analysis['fraud_score']:.2f} (Critical)
**Risk Level:** {fraud_analysis['risk_level']}

**Red Flags:**
{self._format_red_flags(fraud_analysis['indicators'])}

**Action Taken:** Transaction has been blocked and flagged for review.

Please contact us immediately if this was a legitimate transaction."""
            
            elif fraud_analysis["fraud_score"] >= self.RISK_THRESHOLDS["medium"]:
                response = f"""⚠️ **Moderate Fraud Risk**

**Transaction ID:** {transaction_id}
**Fraud Score:** {fraud_analysis['fraud_score']:.2f}
**Risk Level:** {fraud_analysis['risk_level']}

**Potential Issues:**
{self._format_red_flags(fraud_analysis['indicators'])}

**Verification Required:** Please confirm this transaction is legitimate."""
            
            else:
                response = f"""✅ **Transaction Verified**

**Transaction ID:** {transaction_id}
**Fraud Score:** {fraud_analysis['fraud_score']:.2f} (Low Risk)

This transaction appears legitimate based on our analysis."""
            
            # Log fraud check
            self.log_decision(
                decision="fraud_check",
                entity_type="transaction",
                entity_id=transaction_id,
                reasoning=f"Fraud score: {fraud_analysis['fraud_score']:.2f}",
                confidence=fraud_analysis["confidence"],
                details=fraud_analysis,
                db=db
            )
            
            return self.create_response(
                answer=response,
                success=True,
                data=fraud_analysis
            )
            
        except Exception as e:
            return self.handle_error(e, query)
    
    def analyze_transaction(
        self,
        db: Session,
        transaction_id: uuid.UUID
    ) -> Dict[str, Any]:
        """
        Comprehensive fraud analysis of a transaction
        Combines rule-based and ML-based detection
        """
        transaction = db.query(Transaction).filter(
            Transaction.id == transaction_id
        ).first()
        
        if not transaction:
            raise ValueError(f"Transaction not found: {transaction_id}")
        
        # Get account and customer
        account = db.query(Account).filter(Account.id == transaction.account_id).first()
        customer = db.query(Customer).filter(Customer.id == account.customer_id).first()
        
        # Apply fraud detection rules
        rule_scores = {}
        indicators = []
        
        # Rule 1: High amount transaction
        high_amount_score = self._check_high_amount(transaction)
        if high_amount_score > 0:
            rule_scores["high_amount"] = high_amount_score
            indicators.append({
                "rule": "high_amount",
                "description": f"Transaction amount ${transaction.amount:,.2f} exceeds normal threshold",
                "severity": "medium" if high_amount_score < 0.7 else "high"
            })
        
        # Rule 2: Velocity check (rapid transactions)
        velocity_score = self._check_velocity(db, account.id, transaction)
        if velocity_score > 0:
            rule_scores["velocity"] = velocity_score
            indicators.append({
                "rule": "velocity",
                "description": "Unusual number of transactions in short time period",
                "severity": "high"
            })
        
        # Rule 3: Unusual time
        time_score = self._check_unusual_time(transaction)
        if time_score > 0:
            rule_scores["unusual_time"] = time_score
            indicators.append({
                "rule": "unusual_time",
                "description": "Transaction occurred during unusual hours",
                "severity": "low"
            })
        
        # Rule 4: Account behavior anomaly
        behavior_score = self._check_behavior_anomaly(db, account.id, transaction)
        if behavior_score > 0:
            rule_scores["behavior_anomaly"] = behavior_score
            indicators.append({
                "rule": "behavior_anomaly",
                "description": "Transaction deviates from normal account behavior pattern",
                "severity": "medium"
            })
        
        # Calculate composite fraud score
        fraud_score = self._calculate_fraud_score(rule_scores)
        
        # Determine risk level
        risk_level = self._determine_risk_level(fraud_score)
        
        # ML model prediction (simplified - in production use actual ML model)
        ml_features = self._extract_ml_features(db, transaction, account, customer)
        ml_score = self._ml_predict(ml_features)
        
        # Combine rule-based and ML scores
        final_score = (fraud_score * Decimal("0.6")) + (ml_score * Decimal("0.4"))
        
        # Save fraud score to database
        fraud_score_record = FraudScore(
            entity_type="transaction",
            entity_id=transaction.id,
            model_name="hybrid_fraud_detector_v1",
            model_version="1.0",
            fraud_score=final_score,
            risk_category=risk_level,
            features=ml_features,
            anomaly_indicators=[ind for ind in indicators],
            contributing_factors=rule_scores,
            confidence_score=Decimal("0.85"),
            threshold_exceeded=(final_score >= self.RISK_THRESHOLDS["high"]),
            action_taken="blocked" if final_score >= self.RISK_THRESHOLDS["high"] else "monitored"
        )
        db.add(fraud_score_record)
        
        # Create fraud alert if high risk
        if final_score >= self.RISK_THRESHOLDS["medium"]:
            alert = FraudAlert(
                alert_type="transaction_fraud",
                entity_type="transaction",
                entity_id=transaction.id,
                customer_id=customer.id,
                fraud_score=final_score,
                risk_level=risk_level,
                description=f"Potential fraud detected on transaction {transaction.transaction_id}",
                rules_triggered=list(rule_scores.keys()),
                status="open"
            )
            db.add(alert)
            
            # Update transaction flag
            transaction.is_flagged = True
            transaction.fraud_score = final_score
            if final_score >= self.RISK_THRESHOLDS["high"]:
                transaction.status = "blocked"
        
        db.commit()
        
        return {
            "fraud_score": float(final_score),
            "risk_level": risk_level,
            "rule_based_score": float(fraud_score),
            "ml_score": float(ml_score),
            "indicators": indicators,
            "confidence": 0.85,
            "action_taken": "blocked" if final_score >= self.RISK_THRESHOLDS["high"] else "monitored"
        }
    
    def _check_high_amount(self, transaction: Transaction) -> Decimal:
        """Check if transaction amount is unusually high"""
        threshold = self.RULES["high_amount"]["threshold"]
        if transaction.amount > threshold:
            # Score increases with amount
            excess_ratio = transaction.amount / threshold
            return min(Decimal("1.0"), excess_ratio / Decimal("10.0"))
        return Decimal("0.0")
    
    def _check_velocity(
        self,
        db: Session,
        account_id: uuid.UUID,
        transaction: Transaction
    ) -> Decimal:
        """Check for rapid succession of transactions"""
        hour_ago = datetime.utcnow() - timedelta(hours=1)
        
        # Count recent transactions
        recent_txns = db.query(Transaction).filter(
            and_(
                Transaction.account_id == account_id,
                Transaction.transaction_date >= hour_ago,
                Transaction.id != transaction.id
            )
        ).all()
        
        txn_count = len(recent_txns)
        total_amount = sum(float(t.amount) for t in recent_txns) + float(transaction.amount)
        
        # Check velocity rules
        velocity_rule = self.RULES["velocity"]
        count_violation = txn_count > velocity_rule["max_transactions_per_hour"]
        amount_violation = Decimal(str(total_amount)) > velocity_rule["max_amount_per_hour"]
        
        if count_violation or amount_violation:
            return Decimal("0.8")
        
        return Decimal("0.0")
    
    def _check_unusual_time(self, transaction: Transaction) -> Decimal:
        """Check if transaction occurred at unusual time"""
        hour = transaction.transaction_date.hour
        night_start, night_end = self.RULES["unusual_time"]["night_hours"]
        
        if night_start <= hour < night_end:
            return Decimal("0.5")
        
        return Decimal("0.0")
    
    def _check_behavior_anomaly(
        self,
        db: Session,
        account_id: uuid.UUID,
        transaction: Transaction
    ) -> Decimal:
        """Check if transaction deviates from normal behavior"""
        # Get historical average transaction amount
        recent_avg = db.query(func.avg(Transaction.amount)).filter(
            and_(
                Transaction.account_id == account_id,
                Transaction.status == "completed",
                Transaction.transaction_date >= datetime.utcnow() - timedelta(days=30)
            )
        ).scalar()
        
        if not recent_avg:
            return Decimal("0.0")
        
        # If transaction is significantly higher than average
        if transaction.amount > Decimal(str(recent_avg)) * Decimal("3.0"):
            return Decimal("0.6")
        
        return Decimal("0.0")
    
    def _calculate_fraud_score(self, rule_scores: Dict[str, Decimal]) -> Decimal:
        """Calculate weighted fraud score from rules"""
        total_score = Decimal("0.0")
        
        for rule_name, score in rule_scores.items():
            weight = Decimal(str(self.RULES.get(rule_name, {}).get("weight", 0.1)))
            total_score += score * weight
        
        return min(Decimal("1.0"), total_score)
    
    def _determine_risk_level(self, fraud_score: Decimal) -> str:
        """Determine risk level from fraud score"""
        if fraud_score >= self.RISK_THRESHOLDS["critical"]:
            return "critical"
        elif fraud_score >= self.RISK_THRESHOLDS["high"]:
            return "high"
        elif fraud_score >= self.RISK_THRESHOLDS["medium"]:
            return "medium"
        elif fraud_score >= self.RISK_THRESHOLDS["low"]:
            return "low"
        else:
            return "minimal"
    
    def _extract_ml_features(
        self,
        db: Session,
        transaction: Transaction,
        account: Account,
        customer: Customer
    ) -> Dict[str, Any]:
        """Extract features for ML model"""
        # Calculate historical features
        txn_count_30d = db.query(func.count(Transaction.id)).filter(
            and_(
                Transaction.account_id == account.id,
                Transaction.transaction_date >= datetime.utcnow() - timedelta(days=30)
            )
        ).scalar() or 0
        
        avg_amount_30d = db.query(func.avg(Transaction.amount)).filter(
            and_(
                Transaction.account_id == account.id,
                Transaction.transaction_date >= datetime.utcnow() - timedelta(days=30)
            )
        ).scalar() or 0
        
        return {
            "transaction_amount": float(transaction.amount),
            "account_balance": float(account.balance),
            "account_age_days": (datetime.utcnow() - account.opened_at).days,
            "customer_risk_score": float(customer.risk_score) if customer.risk_score else 0.0,
            "txn_count_30d": txn_count_30d,
            "avg_amount_30d": float(avg_amount_30d),
            "is_weekend": transaction.transaction_date.weekday() >= 5,
            "hour_of_day": transaction.transaction_date.hour,
            "amount_to_balance_ratio": float(transaction.amount / account.balance) if account.balance > 0 else 0
        }
    
    def _ml_predict(self, features: Dict[str, Any]) -> Decimal:
        """
        ML model prediction (simplified)
        In production: Load trained model (RandomForest, XGBoost, Neural Network)
        """
        # Simple heuristic model for demo
        score = Decimal("0.0")
        
        # High amount relative to balance
        if features["amount_to_balance_ratio"] > 0.5:
            score += Decimal("0.3")
        
        # High customer risk
        if features["customer_risk_score"] > 0.6:
            score += Decimal("0.2")
        
        # Unusual hour
        if features["hour_of_day"] < 6 or features["hour_of_day"] > 22:
            score += Decimal("0.1")
        
        # New account
        if features["account_age_days"] < 30:
            score += Decimal("0.2")
        
        return min(Decimal("1.0"), score)
    
    def _format_red_flags(self, indicators: List[Dict[str, Any]]) -> str:
        """Format fraud indicators for display"""
        if not indicators:
            return "None detected"
        
        formatted = []
        for ind in indicators:
            severity_emoji = {
                "low": "⚪",
                "medium": "🟡",
                "high": "🔴"
            }
            emoji = severity_emoji.get(ind["severity"], "⚪")
            formatted.append(f"{emoji} {ind['description']}")
        
        return "\n".join(formatted)


# Global instance
fraud_detection_agent = FraudDetectionAgent()
