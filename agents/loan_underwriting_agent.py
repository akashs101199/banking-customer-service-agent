"""
Loan Underwriting AI Agent
Automated loan approval with credit assessment and risk scoring
"""
from typing import Dict, Any, Optional
from decimal import Decimal
import logging
import uuid
from datetime import datetime
from sqlalchemy.orm import Session

from agents.base_agent import BaseAgent
from database.models import Customer, Loan, Account
from utils.llm_client import llm_client
from core_banking.loan_engine import loan_engine

logger = logging.getLogger(__name__)


class LoanUnderwritingAgent(BaseAgent):
    """
    AI-powered loan underwriting agent
    Performs credit assessment, risk scoring, and automated approval decisions
    """
    
    # Credit score ranges
    CREDIT_SCORE_RANGES = {
        "excellent": (750, 850),
        "good": (700, 749),
        "fair": (650, 699),
        "poor": (600, 649),
        "bad": (300, 599)
    }
    
    # Approval thresholds by loan type
    APPROVAL_CRITERIA = {
        "personal": {
            "min_credit_score": 650,
            "max_dti_ratio": 0.43,  # Debt-to-income
            "min_income": 25000
        },
        "auto": {
            "min_credit_score": 640,
            "max_dti_ratio": 0.45,
            "min_income": 20000
        },
        "home": {
            "min_credit_score": 700,
            "max_dti_ratio": 0.36,
            "min_income": 50000
        },
        "business": {
            "min_credit_score": 680,
            "max_dti_ratio": 0.50,
            "min_income": 75000
        }
    }
    
    def __init__(self):
        super().__init__(
            name="LoanUnderwritingAgent",
            description="AI agent specialized in loan underwriting and credit assessment"
        )
    
    def process(
        self,
        query: str,
        context: Dict[str, Any],
        session_id: str
    ) -> Dict[str, Any]:
        """Process loan underwriting request"""
        
        # Extract loan details from context
        loan_id = context.get("loan_id")
        customer_id = context.get("customer_id")
        amount = context.get("amount")
        loan_type = context.get("loan_type")
        
        if not all([loan_id, customer_id, amount, loan_type]):
            return self.create_response(
                answer="I need more information to process this loan application. Please provide the loan type, amount, and customer details.",
                success=False,
                requires_action=True
            )
        
        try:
            # Get database session from context
            db = context.get("db")
            if not db:
                raise ValueError("Database session not available")
            
            # Perform underwriting analysis
            underwriting_result = self.underwrite_loan(
                db=db,
                loan_id=uuid.UUID(loan_id),
                customer_id=uuid.UUID(customer_id),
                amount=Decimal(str(amount)),
                loan_type=loan_type
            )
            
            if underwriting_result["approved"]:
                response = f"""✅ **Loan Application Approved!**

**Loan Details:**
- Loan Type: {loan_type.title()}
- Amount: ${amount:,.2f}
- Interest Rate: {underwriting_result['interest_rate']:.2f}% APR
- Credit Score: {underwriting_result['credit_score']}
- Risk Category: {underwriting_result['risk_category']}

**Approval Reasoning:**
{underwriting_result['reasoning']}

**Next Steps:**
1. Review and sign loan agreement
2. Funds will be disbursed to your account within 1 business day
3. First payment due in 30 days

Would you like to proceed with the loan?"""
            else:
                response = f"""❌ **Loan Application Declined**

Unfortunately, we're unable to approve your loan application at this time.

**Reason:** {underwriting_result['reasoning']}

**What You Can Do:**
{underwriting_result['recommendations']}

If you have questions, please feel free to ask."""
            
            self.log_decision(
                decision="approve" if underwriting_result["approved"] else "decline",
                entity_type="loan",
                entity_id=loan_id,
                reasoning=underwriting_result["reasoning"],
                confidence=underwriting_result["confidence"],
                details=underwriting_result,
                db=db
            )
            
            return self.create_response(
                answer=response,
                success=True,
                data=underwriting_result
            )
            
        except Exception as e:
            return self.handle_error(e, query)
    
    def underwrite_loan(
        self,
        db: Session,
        loan_id: uuid.UUID,
        customer_id: uuid.UUID,
        amount: Decimal,
        loan_type: str
    ) -> Dict[str, Any]:
        """
        Perform comprehensive loan underwriting analysis
        
        Returns:
            Underwriting decision with reasoning
        """
        # Get customer data
        customer = db.query(Customer).filter(Customer.id == customer_id).first()
        if not customer:
            raise ValueError(f"Customer not found: {customer_id}")
        
        # Get loan criteria
        criteria = self.APPROVAL_CRITERIA.get(loan_type, self.APPROVAL_CRITERIA["personal"])
        
        # Mock credit score (in production, fetch from credit bureau)
        credit_score = self._get_credit_score(customer)
        
        # Mock income and debt data (in production, verify from documents)
        annual_income = self._estimate_annual_income(customer)
        monthly_debt = self._calculate_monthly_debt(db, customer_id, amount, loan_type)
        dti_ratio = monthly_debt / (annual_income / 12) if annual_income > 0 else 1.0
        
        # Calculate risk score
        risk_score, risk_category = self._calculate_risk_score(
            credit_score, dti_ratio, annual_income, amount
        )
        
        # Determine interest rate based on risk
        interest_rate = self._determine_interest_rate(loan_type, risk_category, credit_score)
        
        # Apply approval logic
        approved = self._evaluate_approval(
            credit_score, dti_ratio, annual_income, amount, criteria
        )
        
        # Generate AI reasoning
        reasoning = self._generate_approval_reasoning(
            approved, credit_score, dti_ratio, annual_income, risk_category
        )
        
        # Generate recommendations if declined
        recommendations = ""
        if not approved:
            recommendations = self._generate_recommendations(
                credit_score, dti_ratio, annual_income, criteria
            )
        
        # Calculate confidence
        confidence = self._calculate_confidence(credit_score, dti_ratio, risk_score)
        
        return {
            "approved": approved,
            "credit_score": credit_score,
            "annual_income": float(annual_income),
            "dti_ratio": float(dti_ratio),
            "risk_score": float(risk_score),
            "risk_category": risk_category,
            "interest_rate": float(interest_rate),
            "reasoning": reasoning,
            "recommendations": recommendations,
            "confidence": float(confidence)
        }
    
    def _get_credit_score(self, customer: Customer) -> int:
        """
        Get or estimate credit score
        In production: integrate with Equifax/Experian/TransUnion APIs
        """
        # Mock credit score based on customer risk score
        if customer.risk_score:
            # Convert 0-1 risk score to 300-850 credit score (inverse)
            risk = float(customer.risk_score)
            credit_score = int(850 - (risk * 550))
        else:
            # Default to fair credit
            credit_score = 680
        
        return max(300, min(850, credit_score))
    
    def _estimate_annual_income(self, customer: Customer) -> Decimal:
        """
        Estimate annual income
        In production: verify from tax documents, pay stubs
        """
        # Mock income based on customer tier
        # In reality, this would come from verified documents
        return Decimal("60000.00")  # Default
    
    def _calculate_monthly_debt(
        self,
        db: Session,
        customer_id: uuid.UUID,
        new_loan_amount: Decimal,
        loan_type: str
    ) -> Decimal:
        """Calculate total monthly debt including new loan"""
        # Get existing active loans
        existing_loans = db.query(Loan).filter(
            Loan.customer_id == customer_id,
            Loan.status.in_(["active", "approved"])
        ).all()
        
        existing_monthly = sum(
            float(loan.emi_amount) for loan in existing_loans
        )
        
        # Estimate new loan EMI (simplified)
        # Use loan engine for accurate calculation
        from core_banking.loan_engine import LoanEngine
        engine = LoanEngine()
        loan_config = engine.LOAN_TYPES.get(loan_type, engine.LOAN_TYPES["personal"])
        new_emi = float(engine.calculate_emi(
            new_loan_amount,
            loan_config["default_rate"],
            loan_config["max_tenure_months"] // 2  # Assume mid-term
        ))
        
        return Decimal(str(existing_monthly + new_emi))
    
    def _calculate_risk_score(
        self,
        credit_score: int,
        dti_ratio: float,
        annual_income: Decimal,
        loan_amount: Decimal
    ) -> tuple[Decimal, str]:
        """
        Calculate overall risk score (0-1, lower is better)
        Returns: (risk_score, risk_category)
        """
        # Credit score component (0-1, weighted 40%)
        credit_component = (850 - credit_score) / 550 * 0.4
        
        # DTI component (0-1, weighted 30%)
        dti_component = min(dti_ratio / 0.5, 1.0) * 0.3
        
        # Loan-to-income ratio (0-1, weighted 30%)
        lti_ratio = float(loan_amount) / float(annual_income) if annual_income > 0 else 1.0
        lti_component = min(lti_ratio / 2.0, 1.0) * 0.3
        
        risk_score = Decimal(str(credit_component + dti_component + lti_component))
        
        # Categorize risk
        if risk_score <= 0.2:
            category = "low"
        elif risk_score <= 0.4:
            category = "medium"
        elif risk_score <= 0.6:
            category = "high"
        else:
            category = "very_high"
        
        return risk_score, category
    
    def _determine_interest_rate(
        self,
        loan_type: str,
        risk_category: str,
        credit_score: int
    ) -> Decimal:
        """Determine interest rate based on risk"""
        from core_banking.loan_engine import LoanEngine
        engine = LoanEngine()
        base_rate = engine.LOAN_TYPES.get(loan_type, engine.LOAN_TYPES["personal"])["default_rate"]
        
        # Risk-based pricing adjustments
        risk_adjustments = {
            "low": Decimal("-0.01"),      # -1% discount
            "medium": Decimal("0.00"),     # Base rate
            "high": Decimal("0.02"),       # +2% premium
            "very_high": Decimal("0.04")   # +4% premium
        }
        
        adjustment = risk_adjustments.get(risk_category, Decimal("0.00"))
        final_rate = base_rate + adjustment
        
        return max(Decimal("0.0299"), min(final_rate, Decimal("0.2999")))  # Cap between 2.99% and 29.99%
    
    def _evaluate_approval(
        self,
        credit_score: int,
        dti_ratio: float,
        annual_income: Decimal,
        amount: Decimal,
        criteria: Dict[str, Any]
    ) -> bool:
        """Evaluate loan approval based on criteria"""
        if credit_score < criteria["min_credit_score"]:
            return False
        
        if dti_ratio > criteria["max_dti_ratio"]:
            return False
        
        if annual_income < criteria["min_income"]:
            return False
        
        # Additional check: loan amount shouldn't exceed 3x annual income
        if amount > annual_income * 3:
            return False
        
        return True
    
    def _generate_approval_reasoning(
        self,
        approved: bool,
        credit_score: int,
        dti_ratio: float,
        annual_income: Decimal,
        risk_category: str
    ) -> str:
        """Generate AI-powered approval reasoning"""
        if approved:
            return f"""Based on our comprehensive analysis:
- Credit Score ({credit_score}): {"Excellent" if credit_score >= 750 else "Good" if credit_score >= 700 else "Fair"}
- Debt-to-Income Ratio ({dti_ratio:.1%}): Acceptable
- Income Verification: Confirmed
- Risk Assessment: {risk_category.title()} risk profile

Your application meets our lending criteria and demonstrates good creditworthiness."""
        else:
            reasons = []
            if credit_score < 650:
                reasons.append(f"Credit score ({credit_score}) below minimum threshold")
            if dti_ratio > 0.43:
                reasons.append(f"Debt-to-income ratio ({dti_ratio:.1%}) exceeds our limit")
            if annual_income < 25000:
                reasons.append("Income below minimum requirement")
            
            return " • ".join(reasons) if reasons else "Application does not meet current lending criteria"
    
    def _generate_recommendations(
        self,
        credit_score: int,
        dti_ratio: float,
        annual_income: Decimal,
        criteria: Dict[str, Any]
    ) -> str:
        """Generate recommendations for declined applications"""
        recommendations = []
        
        if credit_score < criteria["min_credit_score"]:
            recommendations.append(
                f"1. Improve your credit score to at least {criteria['min_credit_score']} (current: {credit_score})"
            )
            recommendations.append("2. Check your credit report for errors")
            recommendations.append("3. Pay down existing debts")
        
        if dti_ratio > criteria["max_dti_ratio"]:
            recommendations.append(
                f"4. Reduce your debt-to-income ratio to below {criteria['max_dti_ratio']:.0%} (current: {dti_ratio:.1%})"
            )
        
        recommendations.append("5. Consider applying for a smaller loan amount")
        recommendations.append("6. Add a co-applicant with good credit")
        
        return "\n".join(recommendations)
    
    def _calculate_confidence(
        self,
        credit_score: int,
        dti_ratio: float,
        risk_score: Decimal
    ) -> Decimal:
        """Calculate decision confidence (0-1)"""
        # Higher confidence for clear approvals/denials
        # Lower confidence for borderline cases
        
        if credit_score >= 750 and dti_ratio <= 0.3:
            return Decimal("0.95")  # High confidence approval
        elif credit_score < 600 or dti_ratio > 0.50:
            return Decimal("0.90")  # High confidence denial
        else:
            # Borderline case
            return Decimal("0.70")


# Global instance
loan_underwriting_agent = LoanUnderwritingAgent()
