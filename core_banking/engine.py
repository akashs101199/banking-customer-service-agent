"""
Core Banking Transaction Engine
Double-entry bookkeeping, ACID transactions, real-time balance updates
"""
from typing import Dict, Any, Optional, List, Tuple
from decimal import Decimal
from datetime import datetime, date
import logging
import uuid
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from contextlib import contextmanager

from database.models import (
    Account, Transaction, GeneralLedger, Customer
)

logger = logging.getLogger(__name__)


class TransactionEngine:
    """
    Core transaction processing engine with ACID compliance
    Implements double-entry bookkeeping and real-time balance management
    """
    
    # Account codes for general ledger
    ACCOUNT_CODES = {
        "cash": "1100",
        "customer_deposits": "2100",
        "loan_assets": "1200",
        "interest_receivable": "1300",
        "interest_payable": "2200",
        "fee_income": "4100",
        "interest_income": "4200",
        "interest_expense": "5100",
    }
    
    def __init__(self):
        self.logger = logging.getLogger("core_banking.engine")
    
    @contextmanager
    def atomic_transaction(self, db: Session):
        """
        Context manager for atomic database transactions
        Ensures all-or-nothing transaction processing
        """
        try:
            yield db
            db.commit()
            self.logger.info("Transaction committed successfully")
        except Exception as e:
            db.rollback()
            self.logger.error(f"Transaction rolled back: {e}")
            raise
    
    def process_transaction(
        self,
        db: Session,
        account_id: uuid.UUID,
        transaction_type: str,
        amount: Decimal,
        description: str = "",
        counterparty_name: Optional[str] = None,
        counterparty_account: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Transaction:
        """
        Process a banking transaction with double-entry bookkeeping
        
        Args:
            db: Database session
            account_id: Account UUID
            transaction_type: Type of transaction (deposit, withdrawal, transfer, etc.)
            amount: Transaction amount
            description: Transaction description
            counterparty_name: Name of other party
            counterparty_account: Account of other party
            metadata: Additional metadata
            
        Returns:
            Created transaction object
        """
        with self.atomic_transaction(db):
            # Get account with row-level lock for balance update
            account = db.query(Account).filter(
                Account.id == account_id
            ).with_for_update().first()
            
            if not account:
                raise ValueError(f"Account not found: {account_id}")
            
            # Validate transaction
            if transaction_type in ["withdrawal", "transfer", "payment"]:
                if account.available_balance < amount:
                    raise ValueError("Insufficient funds")
            
            # Calculate new balance
            if transaction_type in ["deposit", "credit", "refund"]:
                new_balance = account.balance + amount
            elif transaction_type in ["withdrawal", "debit", "payment", "transfer"]:
                new_balance = account.balance - amount
            else:
                raise ValueError(f"Unknown transaction type: {transaction_type}")
            
            # Create transaction record
            transaction = Transaction(
                transaction_id=f"TXN{uuid.uuid4().hex[:12].upper()}",
                account_id=account_id,
                transaction_type=transaction_type,
                amount=amount,
                currency=account.currency,
                balance_after=new_balance,
                description=description,
                counterparty_name=counterparty_name,
                counterparty_account=counterparty_account,
                status="completed",
                transaction_date=datetime.utcnow()
            )
            db.add(transaction)
            db.flush()  # Get transaction ID
            
            # Update account balance
            account.balance = new_balance
            account.available_balance = new_balance
            account.updated_at = datetime.utcnow()
            
            # Create general ledger entries (double-entry)
            self._create_ledger_entries(
                db, transaction, account, transaction_type, amount
            )
            
            self.logger.info(
                f"Transaction processed: {transaction.transaction_id}, "
                f"Type: {transaction_type}, Amount: {amount}, "
                f"New Balance: {new_balance}"
            )
            
            return transaction
    
    def _create_ledger_entries(
        self,
        db: Session,
        transaction: Transaction,
        account: Account,
        transaction_type: str,
        amount: Decimal
    ):
        """Create double-entry general ledger entries"""
        posting_date = date.today()
        
        # Determine debit and credit accounts based on transaction type
        if transaction_type == "deposit":
            # Debit: Cash, Credit: Customer Deposits
            entries = [
                {
                    "account_code": self.ACCOUNT_CODES["cash"],
                    "account_name": "Cash",
                    "debit_amount": amount,
                    "credit_amount": Decimal("0.00")
                },
                {
                    "account_code": self.ACCOUNT_CODES["customer_deposits"],
                    "account_name": "Customer Deposits",
                    "debit_amount": Decimal("0.00"),
                    "credit_amount": amount
                }
            ]
        elif transaction_type in ["withdrawal", "payment"]:
            # Debit: Customer Deposits, Credit: Cash
            entries = [
                {
                    "account_code": self.ACCOUNT_CODES["customer_deposits"],
                    "account_name": "Customer Deposits",
                    "debit_amount": amount,
                    "credit_amount": Decimal("0.00")
                },
                {
                    "account_code": self.ACCOUNT_CODES["cash"],
                    "account_name": "Cash",
                    "debit_amount": Decimal("0.00"),
                    "credit_amount": amount
                }
            ]
        else:
            # Generic entry
            entries = [
                {
                    "account_code": "9999",
                    "account_name": "Miscellaneous",
                    "debit_amount": amount,
                    "credit_amount": Decimal("0.00")
                }
            ]
        
        # Create ledger entries
        for entry in entries:
            ledger_entry = GeneralLedger(
                entry_id=f"GL{uuid.uuid4().hex[:12].upper()}",
                transaction_id=transaction.id,
                account_code=entry["account_code"],
                account_name=entry["account_name"],
                debit_amount=entry["debit_amount"],
                credit_amount=entry["credit_amount"],
                currency=account.currency,
                description=transaction.description,
                reference_number=transaction.transaction_id,
                posting_date=posting_date
            )
            db.add(ledger_entry)
    
    def transfer_funds(
        self,
        db: Session,
        from_account_id: uuid.UUID,
        to_account_id: uuid.UUID,
        amount: Decimal,
        description: str = "Fund Transfer"
    ) -> Tuple[Transaction, Transaction]:
        """
        Transfer funds between two accounts atomically
        
        Returns:
            Tuple of (debit_transaction, credit_transaction)
        """
        with self.atomic_transaction(db):
            # Process debit from source account
            debit_txn = self.process_transaction(
                db=db,
                account_id=from_account_id,
                transaction_type="transfer",
                amount=amount,
                description=f"{description} - Debit",
                counterparty_account=str(to_account_id)
            )
            
            # Process credit to destination account
            credit_txn = self.process_transaction(
                db=db,
                account_id=to_account_id,
                transaction_type="deposit",
                amount=amount,
                description=f"{description} - Credit",
                counterparty_account=str(from_account_id)
            )
            
            return (debit_txn, credit_txn)
    
    def reverse_transaction(
        self,
        db: Session,
        transaction_id: uuid.UUID,
        reason: str = "Transaction reversal"
    ) -> Transaction:
        """
        Reverse a transaction
        Creates a new transaction with opposite amount
        """
        with self.atomic_transaction(db):
            # Get original transaction
            original = db.query(Transaction).filter(
                Transaction.id == transaction_id
            ).first()
            
            if not original:
                raise ValueError(f"Transaction not found: {transaction_id}")
            
            if original.status != "completed":
                raise ValueError("Can only reverse completed transactions")
            
            # Determine reversal type
            reversal_type_map = {
                "deposit": "withdrawal",
                "withdrawal": "deposit",
                "credit": "debit",
                "debit": "credit"
            }
            reversal_type = reversal_type_map.get(
                original.transaction_type, "reversal"
            )
            
            # Create reversal transaction
            reversal = self.process_transaction(
                db=db,
                account_id=original.account_id,
                transaction_type=reversal_type,
                amount=original.amount,
                description=f"REVERSAL: {reason} (Original: {original.transaction_id})",
                counterparty_name=original.counterparty_name,
                counterparty_account=original.counterparty_account
            )
            
            # Mark original as reversed
            original.status = "reversed"
            
            self.logger.info(f"Transaction reversed: {original.transaction_id}")
            
            return reversal
    
    def get_account_balance(
        self,
        db: Session,
        account_id: uuid.UUID
    ) -> Dict[str, Any]:
        """Get current account balance and details"""
        account = db.query(Account).filter(Account.id == account_id).first()
        
        if not account:
            raise ValueError(f"Account not found: {account_id}")
        
        return {
            "account_number": account.account_number,
            "account_type": account.account_type,
            "balance": float(account.balance),
            "available_balance": float(account.available_balance),
            "currency": account.currency,
            "status": account.status
        }


class BankingEngine:
    """
    High-level banking engine orchestrating all core banking operations
    """
    
    def __init__(self):
        self.transaction_engine = TransactionEngine()
        self.logger = logging.getLogger("core_banking")
    
    def create_account(
        self,
        db: Session,
        customer_id: uuid.UUID,
        account_type: str,
        currency: str = "USD",
        initial_deposit: Optional[Decimal] = None
    ) -> Account:
        """Create a new banking account"""
        # Generate account number
        account_number = f"ACC{uuid.uuid4().hex[:10].upper()}"
        
        # Create account
        account = Account(
            account_number=account_number,
            customer_id=customer_id,
            account_type=account_type,
            currency=currency,
            balance=Decimal("0.00"),
            available_balance=Decimal("0.00"),
            status="active",
            opened_at=datetime.utcnow()
        )
        db.add(account)
        db.flush()
        
        # Process initial deposit if provided
        if initial_deposit and initial_deposit > 0:
            self.transaction_engine.process_transaction(
                db=db,
                account_id=account.id,
                transaction_type="deposit",
                amount=initial_deposit,
                description="Initial deposit"
            )
        
        db.commit()
        self.logger.info(f"Account created: {account_number}")
        
        return account
    
    def close_account(
        self,
        db: Session,
        account_id: uuid.UUID,
        reason: str = ""
    ):
        """Close a banking account"""
        account = db.query(Account).filter(Account.id == account_id).first()
        
        if not account:
            raise ValueError(f"Account not found: {account_id}")
        
        if account.balance != 0:
            raise ValueError("Cannot close account with non-zero balance")
        
        account.status = "closed"
        account.closed_at = datetime.utcnow()
        db.commit()
        
        self.logger.info(f"Account closed: {account.account_number}, Reason: {reason}")


# Global instances
transaction_engine = TransactionEngine()
banking_engine = BankingEngine()
