"""
Payment Processing System
Supports ACH, Wire, Card payments, and Real-Time Payments (RTP)
"""
from typing import Dict, Any, Optional, List
from decimal import Decimal
from datetime import datetime, date, timedelta
import logging
import uuid
from sqlalchemy.orm import Session
from enum import Enum

from database.models import (
    Transaction, Account, PaymentInstruction, GeneralLedger,
    Biller, BillPayment, Beneficiary
)
from core_banking.engine import transaction_engine

logger = logging.getLogger(__name__)


class PaymentMethod(Enum):
    """Supported payment methods"""
    ACH = "ach"
    WIRE = "wire"
    CARD = "card"
    RTP = "rtp"  # Real-Time Payments
    INTERNAL = "internal"


class PaymentType(Enum):
    """Payment types"""
    TRANSFER = "transfer"
    BILL_PAYMENT = "bill_payment"
    PAYROLL = "payroll"
    VENDOR_PAYMENT = "vendor_payment"
    LOAN_PAYMENT = "loan_payment"


class PaymentProcessor:
    """
    Multi-channel payment processing system
    Handles various payment methods with proper validation and routing
    """
    
    # Processing times by method (in business days)
    PROCESSING_TIMES = {
        PaymentMethod.ACH: 1,
        PaymentMethod.WIRE: 0,  # Same day
        PaymentMethod.CARD: 0,  # Instant
        PaymentMethod.RTP: 0,   # Instant
        PaymentMethod.INTERNAL: 0  # Instant
    }
    
    # Fee structure (in USD)
    FEES = {
        PaymentMethod.ACH: Decimal("0.25"),
        PaymentMethod.WIRE: Decimal("25.00"),
        PaymentMethod.CARD: Decimal("0.00"),  # Percentage-based
        PaymentMethod.RTP: Decimal("0.50"),
        PaymentMethod.INTERNAL: Decimal("0.00")
    }
    
    def __init__(self):
        self.logger = logging.getLogger("payment_processor")
    
    def initiate_payment(
        self,
        db: Session,
        account_id: uuid.UUID,
        payment_type: str,
        payment_method: str,
        amount: Decimal,
        beneficiary_name: str,
        beneficiary_account: Optional[str] = None,
        beneficiary_bank: Optional[str] = None,
        routing_number: Optional[str] = None,
        swift_code: Optional[str] = None,
        reference: Optional[str] = None,
        description: Optional[str] = None,
        scheduled_date: Optional[date] = None
    ) -> PaymentInstruction:
        """
        Initiate a payment instruction
        
        Args:
            db: Database session
            account_id: Source account UUID
            payment_type: Type of payment
            payment_method: Payment method (ACH, Wire, etc.)
            amount: Payment amount
            beneficiary_name: Beneficiary name
            beneficiary_account: Beneficiary account number
            beneficiary_bank: Beneficiary bank name
            routing_number: Bank routing number
            swift_code: SWIFT code for international wires
            reference: Payment reference
            description: Payment description
            scheduled_date: Future payment date (optional)
            
        Returns:
            PaymentInstruction object
        """
        # Validate account
        account = db.query(Account).filter(Account.id == account_id).first()
        if not account:
            raise ValueError(f"Account not found: {account_id}")
        
        if account.status != "active":
            raise ValueError(f"Account is not active: {account.status}")
        
        # Validate sufficient funds
        total_amount = amount + self._calculate_fee(payment_method, amount)
        if account.available_balance < total_amount:
            raise ValueError(f"Insufficient funds. Required: {total_amount}, Available: {account.available_balance}")
        
        # Validate payment method specific requirements
        self._validate_payment_requirements(
            payment_method, beneficiary_account, routing_number, swift_code
        )
        
        # Create payment instruction
        payment_id = f"PMT{uuid.uuid4().hex[:12].upper()}"
        scheduled_date = scheduled_date or date.today()
        
        payment = PaymentInstruction(
            payment_id=payment_id,
            account_id=account_id,
            payment_type=payment_type,
            payment_method=payment_method,
            amount=amount,
            currency=account.currency,
            beneficiary_name=beneficiary_name,
            beneficiary_account=beneficiary_account,
            beneficiary_bank=beneficiary_bank,
            routing_number=routing_number,
            swift_code=swift_code,
            reference=reference or payment_id,
            description=description or f"{payment_type} payment",
            status="pending",
            scheduled_date=scheduled_date
        )
        
        db.add(payment)
        db.commit()
        
        self.logger.info(
            f"Payment initiated: {payment_id}, Method: {payment_method}, "
            f"Amount: {amount}, Beneficiary: {beneficiary_name}"
        )
        
        # Execute immediately if scheduled for today and method supports it
        if scheduled_date == date.today():
            self.execute_payment(db, payment.id)
        
        return payment
    
    def execute_payment(
        self,
        db: Session,
        payment_id: uuid.UUID
    ) -> PaymentInstruction:
        """
        Execute a payment instruction
        Processes the actual payment and updates account balances
        """
        payment = db.query(PaymentInstruction).filter(
            PaymentInstruction.id == payment_id
        ).first()
        
        if not payment:
            raise ValueError(f"Payment instruction not found: {payment_id}")
        
        if payment.status != "pending":
            raise ValueError(f"Payment not in pending status: {payment.status}")
        
        try:
            # Calculate total with fees
            fee = self._calculate_fee(payment.payment_method, payment.amount)
            total_amount = payment.amount + fee
            
            # Process payment based on method
            if payment.payment_method == PaymentMethod.INTERNAL.value:
                # Internal transfer - instant
                self._process_internal_transfer(db, payment)
            elif payment.payment_method == PaymentMethod.ACH.value:
                self._process_ach_payment(db, payment)
            elif payment.payment_method == PaymentMethod.WIRE.value:
                self._process_wire_payment(db, payment)
            elif payment.payment_method == PaymentMethod.CARD.value:
                self._process_card_payment(db, payment)
            elif payment.payment_method == PaymentMethod.RTP.value:
                self._process_rtp_payment(db, payment)
            else:
                raise ValueError(f"Unsupported payment method: {payment.payment_method}")
            
            # Debit account
            transaction_engine.process_transaction(
                db=db,
                account_id=payment.account_id,
                transaction_type="payment",
                amount=total_amount,
                description=f"{payment.description} (Fee: {fee})",
                counterparty_name=payment.beneficiary_name,
                counterparty_account=payment.beneficiary_account
            )
            
            # Update payment status
            payment.status = "completed"
            payment.execution_date = datetime.utcnow()
            payment.settlement_date = self._calculate_settlement_date(payment.payment_method)
            payment.confirmation_number = f"CONF{uuid.uuid4().hex[:12].upper()}"
            
            db.commit()
            
            self.logger.info(f"Payment executed successfully: {payment.payment_id}")
            return payment
            
        except Exception as e:
            payment.status = "failed"
            payment.failure_reason = str(e)
            db.commit()
            self.logger.error(f"Payment execution failed: {payment.payment_id}, Error: {e}")
            raise
    
    def cancel_payment(
        self,
        db: Session,
        payment_id: uuid.UUID,
        reason: str = ""
    ) -> PaymentInstruction:
        """Cancel a pending payment"""
        payment = db.query(PaymentInstruction).filter(
            PaymentInstruction.id == payment_id
        ).first()
        
        if not payment:
            raise ValueError(f"Payment not found: {payment_id}")
        
        if payment.status != "pending":
            raise ValueError(f"Cannot cancel payment with status: {payment.status}")
        
        payment.status = "cancelled"
        payment.failure_reason = f"Cancelled: {reason}"
        db.commit()
        
        self.logger.info(f"Payment cancelled: {payment.payment_id}")
        return payment
    
    def _calculate_fee(self, payment_method: str, amount: Decimal) -> Decimal:
        """Calculate payment processing fee"""
        try:
            method = PaymentMethod(payment_method)
            if method == PaymentMethod.CARD:
                # 2.9% for card payments
                return amount * Decimal("0.029")
            return self.FEES.get(method, Decimal("0.00"))
        except ValueError:
            return Decimal("0.00")
    
    def _calculate_settlement_date(self, payment_method: str) -> date:
        """Calculate settlement date based on payment method"""
        try:
            method = PaymentMethod(payment_method)
            business_days = self.PROCESSING_TIMES.get(method, 0)
            return date.today() + timedelta(days=business_days)
        except ValueError:
            return date.today()
    
    def _validate_payment_requirements(
        self,
        payment_method: str,
        beneficiary_account: Optional[str],
        routing_number: Optional[str],
        swift_code: Optional[str]
    ):
        """Validate payment method specific requirements"""
        if payment_method == PaymentMethod.ACH.value:
            if not beneficiary_account or not routing_number:
                raise ValueError("ACH payments require beneficiary account and routing number")
        elif payment_method == PaymentMethod.WIRE.value:
            if not beneficiary_account:
                raise ValueError("Wire transfers require beneficiary account")
            # SWIFT code required for international wires (simplified check)
            if swift_code and len(swift_code) not in [8, 11]:
                raise ValueError("Invalid SWIFT code format")
    
    def _process_internal_transfer(self, db: Session, payment: PaymentInstruction):
        """Process internal bank transfer"""
        # For internal transfers, find the beneficiary account
        if payment.beneficiary_account:
            beneficiary = db.query(Account).filter(
                Account.account_number == payment.beneficiary_account
            ).first()
            if beneficiary:
                # Credit beneficiary account
                transaction_engine.process_transaction(
                    db=db,
                    account_id=beneficiary.id,
                    transaction_type="deposit",
                    amount=payment.amount,
                    description=f"Transfer from {payment.beneficiary_name}",
                    counterparty_account=str(payment.account_id)
                )
    
    def _process_ach_payment(self, db: Session, payment: PaymentInstruction):
        """Process ACH payment (mock implementation)"""
        # In production, integrate with ACH network (Nacha)
        self.logger.info(f"ACH payment queued: {payment.payment_id}")
        # Simulate ACH processing
        pass
    
    def _process_wire_payment(self, db: Session, payment: PaymentInstruction):
        """Process wire transfer (mock implementation)"""
        # In production, integrate with Fedwire or SWIFT
        self.logger.info(f"Wire transfer queued: {payment.payment_id}")
        # Simulate wire processing
        pass
    
    def _process_card_payment(self, db: Session, payment: PaymentInstruction):
        """Process card payment (mock implementation)"""
        # In production, integrate with card networks
        self.logger.info(f"Card payment processed: {payment.payment_id}")
        # Simulate card processing
        pass
    
    def _process_rtp_payment(self, db: Session, payment: PaymentInstruction):
        """Process real-time payment (mock implementation)"""
        # In production, integrate with RTP network
        self.logger.info(f"RTP payment processed: {payment.payment_id}")
        # Simulate RTP processing
        pass
    
    def get_payment_status(
        self,
        db: Session,
        payment_id: str
    ) -> Dict[str, Any]:
        """Get payment status and details"""
        payment = db.query(PaymentInstruction).filter(
            PaymentInstruction.payment_id == payment_id
        ).first()
        
        if not payment:
            raise ValueError(f"Payment not found: {payment_id}")
        
        return {
            "payment_id": payment.payment_id,
            "status": payment.status,
            "amount": float(payment.amount),
            "currency": payment.currency,
            "beneficiary": payment.beneficiary_name,
            "payment_method": payment.payment_method,
            "scheduled_date": payment.scheduled_date.isoformat() if payment.scheduled_date else None,
            "execution_date": payment.execution_date.isoformat() if payment.execution_date else None,
            "settlement_date": payment.settlement_date.isoformat() if payment.settlement_date else None,
            "confirmation_number": payment.confirmation_number,
            "failure_reason": payment.failure_reason
        }


    def pay_bill(
        self,
        db: Session,
        account_id: uuid.UUID,
        biller_name: str,
        amount: Decimal,
        reference: str = None
    ) -> Dict[str, Any]:
        """
        Process a bill payment
        """
        # Find or create biller (simplified for demo)
        biller = db.query(Biller).filter(Biller.name == biller_name).first()
        if not biller:
            biller = Biller(
                biller_id=f"BILL{uuid.uuid4().hex[:8].upper()}",
                name=biller_name,
                category="Utility",
                status="active"
            )
            db.add(biller)
            db.commit()
            
        # Process transaction
        transaction = transaction_engine.process_transaction(
            db=db,
            account_id=account_id,
            transaction_type="debit",
            amount=amount,
            description=f"Bill Payment to {biller_name}",
            category="Bill Payment",
            reference=reference
        )
        
        # Record bill payment
        payment = BillPayment(
            payment_id=f"BP{uuid.uuid4().hex[:10].upper()}",
            account_id=account_id,
            biller_id=biller.id,
            amount=amount,
            reference_number=reference,
            status="completed"
        )
        db.add(payment)
        db.commit()
        
        self.logger.info(f"Bill payment processed: {amount} to {biller_name}")
        
        return {
            "payment_id": payment.payment_id,
            "transaction_id": transaction.transaction_id,
            "status": "completed",
            "biller": biller_name,
            "amount": float(amount)
        }

    def add_beneficiary(
        self,
        db: Session,
        customer_id: uuid.UUID,
        name: str,
        account_number: str,
        bank_name: str,
        routing_number: str = None,
        nickname: str = None
    ) -> Dict[str, Any]:
        """Add a new beneficiary"""
        beneficiary = Beneficiary(
            customer_id=customer_id,
            name=name,
            account_number=account_number,
            bank_name=bank_name,
            routing_number=routing_number,
            nickname=nickname
        )
        db.add(beneficiary)
        db.commit()
        
        return {
            "id": str(beneficiary.id),
            "name": beneficiary.name,
            "nickname": beneficiary.nickname,
            "status": "active"
        }

    def get_beneficiaries(
        self,
        db: Session,
        customer_id: uuid.UUID
    ) -> List[Dict[str, Any]]:
        """Get list of beneficiaries"""
        beneficiaries = db.query(Beneficiary).filter(
            Beneficiary.customer_id == customer_id,
            Beneficiary.status == "active"
        ).all()
        
        return [
            {
                "id": str(b.id),
                "name": b.name,
                "account_number": f"****{b.account_number[-4:]}",
                "bank_name": b.bank_name,
                "nickname": b.nickname
            }
            for b in beneficiaries
        ]


# Global instance
payment_processor = PaymentProcessor()
