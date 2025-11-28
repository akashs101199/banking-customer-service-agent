"""
Loan Engine
Loan origination, servicing, amortization, and payment processing
"""
from typing import Dict, Any, Optional, List
from decimal import Decimal
from datetime import datetime, date
from dateutil.relativedelta import relativedelta
import logging
import uuid
import math
from sqlalchemy.orm import Session

from database.models import Loan, LoanPayment, Customer, Account
from core_banking.engine import transaction_engine

logger = logging.getLogger(__name__)


class LoanEngine:
    """
    Complete loan lifecycle management system
    Handles loan origination, servicing, amortization schedules, and payments
    """
    
    # Loan types and default parameters
    LOAN_TYPES = {
        "personal": {
            "max_amount": Decimal("50000"),
            "max_tenure_months": 60,
            "default_rate": Decimal("0.0899")  # 8.99% APR
        },
        "auto": {
            "max_amount": Decimal("75000"),
            "max_tenure_months": 72,
            "default_rate": Decimal("0.0499")  # 4.99% APR
        },
        "home": {
            "max_amount": Decimal("1000000"),
            "max_tenure_months": 360,  # 30 years
            "default_rate": Decimal("0.0349")  # 3.49% APR
        },
        "business": {
            "max_amount": Decimal("500000"),
            "max_tenure_months": 120,  # 10 years
            "default_rate": Decimal("0.0699")  # 6.99% APR
        }
    }
    
    def __init__(self):
        self.logger = logging.getLogger("loan_engine")
    
    def create_loan_application(
        self,
        db: Session,
        customer_id: uuid.UUID,
        loan_type: str,
        principal_amount: Decimal,
        tenure_months: int,
        interest_rate: Optional[Decimal] = None,
        account_id: Optional[uuid.UUID] = None
    ) -> Loan:
        """
        Create a new loan application
        
        Args:
            db: Database session
            customer_id: Customer UUID
            loan_type: Type of loan (personal, auto, home, business)
            principal_amount: Requested loan amount
            tenure_months: Loan tenure in months
            interest_rate: Annual interest rate (optional, uses default if not provided)
            account_id: Associated account for disbursement
            
        Returns:
            Loan object
        """
        # Validate loan type
        if loan_type not in self.LOAN_TYPES:
            raise ValueError(f"Invalid loan type: {loan_type}. Must be one of {list(self.LOAN_TYPES.keys())}")
        
        loan_config = self.LOAN_TYPES[loan_type]
        
        # Validate amount and tenure
        if principal_amount > loan_config["max_amount"]:
            raise ValueError(
                f"Loan amount {principal_amount} exceeds maximum {loan_config['max_amount']} for {loan_type} loans"
            )
        
        if tenure_months > loan_config["max_tenure_months"]:
            raise ValueError(
                f"Tenure {tenure_months} months exceeds maximum {loan_config['max_tenure_months']} for {loan_type} loans"
            )
        
        # Use default rate if not provided
        if not interest_rate:
            interest_rate = loan_config["default_rate"]
        
        # Calculate EMI
        emi_amount = self.calculate_emi(principal_amount, interest_rate, tenure_months)
        
        # Create loan record
        loan_id = f"LOAN{uuid.uuid4().hex[:10].upper()}"
        loan = Loan(
            loan_id=loan_id,
            customer_id=customer_id,
            account_id=account_id,
            loan_type=loan_type,
            principal_amount=principal_amount,
            interest_rate=interest_rate,
            tenure_months=tenure_months,
            emi_amount=emi_amount,
            outstanding_balance=principal_amount,
            status="pending",
            application_date=datetime.utcnow()
        )
        
        db.add(loan)
        db.commit()
        
        self.logger.info(
            f"Loan application created: {loan_id}, Type: {loan_type}, "
            f"Amount: {principal_amount}, EMI: {emi_amount}"
        )
        
        return loan
    
    def calculate_emi(
        self,
        principal: Decimal,
        annual_rate: Decimal,
        tenure_months: int
    ) -> Decimal:
        """
        Calculate Equated Monthly Installment (EMI)
        Formula: EMI = P * r * (1 + r)^n / ((1 + r)^n - 1)
        Where:
            P = Principal amount
            r = Monthly interest rate
            n = Number of months
        """
        # Convert annual rate to monthly rate
        monthly_rate = annual_rate / Decimal("12")
        
        if monthly_rate == 0:
            # For 0% interest, EMI is simply principal / tenure
            return principal / Decimal(tenure_months)
        
        # Calculate EMI using formula
        monthly_rate_float = float(monthly_rate)
        rate_power = math.pow(1 + monthly_rate_float, tenure_months)
        emi = float(principal) * monthly_rate_float * rate_power / (rate_power - 1)
        
        return Decimal(str(round(emi, 2)))
    
    def approve_loan(
        self,
        db: Session,
        loan_id: uuid.UUID,
        approval_notes: str = "",
        disburse_immediately: bool = True
    ) -> Loan:
        """
        Approve a loan application
        Optionally disburse funds immediately
        """
        loan = db.query(Loan).filter(Loan.id == loan_id).first()
        
        if not loan:
            raise ValueError(f"Loan not found: {loan_id}")
        
        if loan.status != "pending":
            raise ValueError(f"Loan not in pending status: {loan.status}")
        
        loan.status = "approved"
        loan.approval_date = datetime.utcnow()
        db.commit()
        
        self.logger.info(f"Loan approved: {loan.loan_id}")
        
        # Generate payment schedule
        self.generate_payment_schedule(db, loan_id)
        
        # Disburse if requested and account is linked
        if disburse_immediately and loan.account_id:
            self.disburse_loan(db, loan_id)
        
        return loan
    
    def disburse_loan(
        self,
        db: Session,
        loan_id: uuid.UUID
    ) -> Loan:
        """
        Disburse approved loan funds to linked account
        """
        loan = db.query(Loan).filter(Loan.id == loan_id).first()
        
        if not loan:
            raise ValueError(f"Loan not found: {loan_id}")
        
        if loan.status != "approved":
            raise ValueError(f"Loan must be approved before disbursement: {loan.status}")
        
        if not loan.account_id:
            raise ValueError("Loan must have an associated account for disbursement")
        
        if loan.disbursement_date:
            raise ValueError("Loan already disbursed")
        
        # Credit the account with loan amount
        transaction_engine.process_transaction(
            db=db,
            account_id=loan.account_id,
            transaction_type="credit",
            amount=loan.principal_amount,
            description=f"Loan disbursement - {loan.loan_id}"
        )
        
        # Update loan status
        loan.status = "active"
        loan.disbursement_date = datetime.utcnow()
        
        # Calculate maturity date
        loan.maturity_date = (
            date.today() + relativedelta(months=loan.tenure_months)
        )
        
        db.commit()
        
        self.logger.info(f"Loan disbursed: {loan.loan_id}, Amount: {loan.principal_amount}")
        
        return loan
    
    def generate_payment_schedule(
        self,
        db: Session,
        loan_id: uuid.UUID
    ) -> List[LoanPayment]:
        """
        Generate amortization schedule with payment breakdown
        """
        loan = db.query(Loan).filter(Loan.id == loan_id).first()
        
        if not loan:
            raise ValueError(f"Loan not found: {loan_id}")
        
        # Clear existing schedule if any
        db.query(LoanPayment).filter(LoanPayment.loan_id == loan_id).delete()
        
        monthly_rate = loan.interest_rate / Decimal("12")
        outstanding = loan.principal_amount
        payment_schedule = []
        
        start_date = loan.disbursement_date.date() if loan.disbursement_date else date.today()
        
        for month in range(1, loan.tenure_months + 1):
            # Calculate interest for this period
            interest_amount = outstanding * monthly_rate
            principal_amount = loan.emi_amount - interest_amount
            outstanding -= principal_amount
            
            # Due date is one month from start/previous payment
            due_date = start_date + relativedelta(months=month)
            
            # Create payment record
            payment = LoanPayment(
                payment_id=f"LP{uuid.uuid4().hex[:12].upper()}",
                loan_id=loan.id,
                payment_number=month,
                due_date=due_date,
                scheduled_amount=loan.emi_amount,
                principal_amount=principal_amount,
                interest_amount=interest_amount,
                outstanding_balance=max(outstanding, Decimal("0.00")),
                status="pending"
            )
            db.add(payment)
            payment_schedule.append(payment)
        
        db.commit()
        
        self.logger.info(
            f"Payment schedule generated for loan {loan.loan_id}: "
            f"{len(payment_schedule)} payments"
        )
        
        return payment_schedule
    
    def process_loan_payment(
        self,
        db: Session,
        loan_payment_id: uuid.UUID,
        amount: Decimal,
        payment_method: str = "auto_debit"
    ) -> LoanPayment:
        """
        Process a loan payment
        """
        payment = db.query(LoanPayment).filter(
            LoanPayment.id == loan_payment_id
        ).first()
        
        if not payment:
            raise ValueError(f"Loan payment not found: {loan_payment_id}")
        
        if payment.status == "paid":
            raise ValueError("Payment already processed")
        
        loan = db.query(Loan).filter(Loan.id == payment.loan_id).first()
        
        # Calculate late fee if payment is overdue
        late_fee = Decimal("0.00")
        if date.today() > payment.due_date and payment.status == "pending":
            days_overdue = (date.today() - payment.due_date).days
            late_fee = Decimal("25.00") * Decimal(math.ceil(days_overdue / 30))  # $25 per month
        
        total_due = payment.scheduled_amount + late_fee
        
        if amount < total_due:
            # Partial payment
            payment.paid_amount = amount
            payment.status = "partial"
        else:
            # Full payment
            payment.paid_amount = total_due
            payment.status = "paid"
            payment.payment_date = date.today()
        
        payment.late_fee = late_fee
        payment.payment_method = payment_method
        
        # Update loan outstanding balance
        if payment.principal_amount:
            loan.outstanding_balance -= payment.principal_amount
        
        # Check if loan is fully paid
        if loan.outstanding_balance <= 0:
            loan.status = "closed"
            loan.outstanding_balance = Decimal("0.00")
        
        db.commit()
        
        self.logger.info(
            f"Loan payment processed: {payment.payment_id}, "
            f"Amount: {amount}, Status: {payment.status}"
        )
        
        return payment
    
    def get_loan_details(
        self,
        db: Session,
        loan_id: str
    ) -> Dict[str, Any]:
        """Get comprehensive loan details"""
        loan = db.query(Loan).filter(Loan.loan_id == loan_id).first()
        
        if not loan:
            raise ValueError(f"Loan not found: {loan_id}")
        
        # Get payment schedule
        payments = db.query(LoanPayment).filter(
            LoanPayment.loan_id == loan.id
        ).order_by(LoanPayment.payment_number).all()
        
        total_paid = sum(p.paid_amount or Decimal("0.00") for p in payments)
        total_interest = sum(
            p.interest_amount for p in payments 
            if p.interest_amount and p.status in ["paid", "partial"]
        )
        
        return {
            "loan_id": loan.loan_id,
            "loan_type": loan.loan_type,
            "status": loan.status,
            "principal_amount": float(loan.principal_amount),
            "interest_rate": float(loan.interest_rate),
            "tenure_months": loan.tenure_months,
            "emi_amount": float(loan.emi_amount),
            "outstanding_balance": float(loan.outstanding_balance),
            "total_paid": float(total_paid),
            "total_interest_paid": float(total_interest),
            "application_date": loan.application_date.isoformat() if loan.application_date else None,
            "approval_date": loan.approval_date.isoformat() if loan.approval_date else None,
            "disbursement_date": loan.disbursement_date.isoformat() if loan.disbursement_date else None,
            "maturity_date": loan.maturity_date.isoformat() if loan.maturity_date else None,
            "next_payment": self._get_next_payment(payments),
            "payment_history": [
                {
                    "payment_number": p.payment_number,
                    "due_date": p.due_date.isoformat(),
                    "amount": float(p.scheduled_amount),
                    "status": p.status,
                    "paid_amount": float(p.paid_amount) if p.paid_amount else 0.0,
                    "late_fee": float(p.late_fee) if p.late_fee else 0.0
                }
                for p in payments
            ]
        }
    
    def _get_next_payment(self, payments: List[LoanPayment]) -> Optional[Dict[str, Any]]:
        """Get next pending payment"""
        for payment in payments:
            if payment.status in ["pending", "overdue"]:
                return {
                    "payment_number": payment.payment_number,
                    "due_date": payment.due_date.isoformat(),
                    "amount": float(payment.scheduled_amount),
                    "principal": float(payment.principal_amount) if payment.principal_amount else 0.0,
                    "interest": float(payment.interest_amount) if payment.interest_amount else 0.0
                }
        return None


# Global instance
loan_engine = LoanEngine()
