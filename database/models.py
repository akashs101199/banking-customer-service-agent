"""
Database Models using SQLAlchemy ORM
"""
from sqlalchemy import (
    Column, String, Integer, Float, Boolean, DateTime, Date, 
    ForeignKey, Text, DECIMAL, JSON
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid

Base = declarative_base()


class Customer(Base):
    """Customer model"""
    __tablename__ = "customers"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    customer_id = Column(String(50), unique=True, nullable=False, index=True)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    email = Column(String(255), unique=True, nullable=False, index=True)
    phone = Column(String(20))
    date_of_birth = Column(Date)
    nationality = Column(String(50))
    address_line1 = Column(String(255))
    address_line2 = Column(String(255))
    city = Column(String(100))
    state = Column(String(100))
    postal_code = Column(String(20))
    country = Column(String(100))
    kyc_status = Column(String(20), default="pending", index=True)
    kyc_verified_at = Column(DateTime)
    risk_score = Column(DECIMAL(3, 2), default=0.0)
    status = Column(String(20), default="active")
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    # Relationships
    accounts = relationship("Account", back_populates="customer", cascade="all, delete-orphan")
    cards = relationship("Card", back_populates="customer", cascade="all, delete-orphan")
    kyc_documents = relationship("KYCDocument", back_populates="customer", cascade="all, delete-orphan")
    loans = relationship("Loan", back_populates="customer", cascade="all, delete-orphan")
    fraud_alerts = relationship("FraudAlert", back_populates="customer", cascade="all, delete-orphan")


class Account(Base):
    """Account model"""
    __tablename__ = "accounts"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    account_number = Column(String(50), unique=True, nullable=False, index=True)
    customer_id = Column(UUID(as_uuid=True), ForeignKey("customers.id", ondelete="CASCADE"), index=True)
    account_type = Column(String(20), nullable=False)
    currency = Column(String(3), default="USD")
    balance = Column(DECIMAL(15, 2), default=0.00)
    available_balance = Column(DECIMAL(15, 2), default=0.00)
    overdraft_limit = Column(DECIMAL(15, 2), default=0.00)
    interest_rate = Column(DECIMAL(5, 4), default=0.0000)
    status = Column(String(20), default="active", index=True)
    opened_at = Column(DateTime, server_default=func.now())
    closed_at = Column(DateTime)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    # Relationships
    customer = relationship("Customer", back_populates="accounts")
    transactions = relationship("Transaction", back_populates="account", cascade="all, delete-orphan")
    cards = relationship("Card", back_populates="account", cascade="all, delete-orphan")


class Transaction(Base):
    """Transaction model"""
    __tablename__ = "transactions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    transaction_id = Column(String(50), unique=True, nullable=False)
    account_id = Column(UUID(as_uuid=True), ForeignKey("accounts.id", ondelete="CASCADE"), index=True)
    transaction_type = Column(String(20), nullable=False)
    amount = Column(DECIMAL(15, 2), nullable=False)
    currency = Column(String(3), default="USD")
    balance_after = Column(DECIMAL(15, 2))
    description = Column(Text)
    category = Column(String(50))
    reference_number = Column(String(100))
    counterparty_name = Column(String(255))
    counterparty_account = Column(String(50))
    status = Column(String(20), default="completed", index=True)
    fraud_score = Column(DECIMAL(3, 2), default=0.0)
    is_flagged = Column(Boolean, default=False, index=True)
    transaction_date = Column(DateTime, server_default=func.now(), index=True)
    created_at = Column(DateTime, server_default=func.now())
    
    # Relationships
    account = relationship("Account", back_populates="transactions")


class Card(Base):
    """Card model"""
    __tablename__ = "cards"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    card_number = Column(String(16), unique=True, nullable=False)
    card_type = Column(String(20), nullable=False)
    account_id = Column(UUID(as_uuid=True), ForeignKey("accounts.id", ondelete="CASCADE"), index=True)
    customer_id = Column(UUID(as_uuid=True), ForeignKey("customers.id", ondelete="CASCADE"), index=True)
    card_holder_name = Column(String(255), nullable=False)
    expiry_date = Column(Date, nullable=False)
    cvv = Column(String(4), nullable=False)
    credit_limit = Column(DECIMAL(15, 2))
    available_credit = Column(DECIMAL(15, 2))
    pin_hash = Column(String(255))
    status = Column(String(20), default="pending", index=True)
    issued_at = Column(DateTime)
    activated_at = Column(DateTime)
    blocked_at = Column(DateTime)
    block_reason = Column(Text)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    # Relationships
    customer = relationship("Customer", back_populates="cards")
    account = relationship("Account", back_populates="cards")


class KYCDocument(Base):
    """KYC Document model"""
    __tablename__ = "kyc_documents"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    customer_id = Column(UUID(as_uuid=True), ForeignKey("customers.id", ondelete="CASCADE"), index=True)
    document_type = Column(String(50), nullable=False)
    document_number = Column(String(100))
    file_path = Column(String(500))
    file_name = Column(String(255))
    file_size_kb = Column(Integer)
    mime_type = Column(String(100))
    ocr_text = Column(Text)
    verification_status = Column(String(20), default="pending", index=True)
    verification_score = Column(DECIMAL(3, 2))
    verified_by = Column(String(50))
    verified_at = Column(DateTime)
    rejection_reason = Column(Text)
    uploaded_at = Column(DateTime, server_default=func.now())
    created_at = Column(DateTime, server_default=func.now())
    
    # Relationships
    customer = relationship("Customer", back_populates="kyc_documents")


class Loan(Base):
    """Loan model"""
    __tablename__ = "loans"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    loan_id = Column(String(50), unique=True, nullable=False)
    customer_id = Column(UUID(as_uuid=True), ForeignKey("customers.id", ondelete="CASCADE"), index=True)
    account_id = Column(UUID(as_uuid=True), ForeignKey("accounts.id"))
    loan_type = Column(String(50), nullable=False)
    principal_amount = Column(DECIMAL(15, 2), nullable=False)
    interest_rate = Column(DECIMAL(5, 4), nullable=False)
    tenure_months = Column(Integer, nullable=False)
    emi_amount = Column(DECIMAL(15, 2), nullable=False)
    outstanding_balance = Column(DECIMAL(15, 2))
    status = Column(String(20), default="pending", index=True)
    application_date = Column(DateTime, server_default=func.now())
    approval_date = Column(DateTime)
    disbursement_date = Column(DateTime)
    maturity_date = Column(Date)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    # Relationships
    customer = relationship("Customer", back_populates="loans")


class AuditLog(Base):
    """Audit Log model"""
    __tablename__ = "audit_logs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_type = Column(String(100), nullable=False)
    entity_type = Column(String(50), index=True)
    entity_id = Column(UUID(as_uuid=True), index=True)
    user_id = Column(UUID(as_uuid=True))
    agent_name = Column(String(100))
    action = Column(String(100), nullable=False)
    details = Column(JSON)
    ip_address = Column(String(45))
    user_agent = Column(Text)
    status = Column(String(20))
    error_message = Column(Text)
    created_at = Column(DateTime, server_default=func.now(), index=True)


class ConversationHistory(Base):
    """Conversation History model"""
    __tablename__ = "conversation_history"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(String(100), nullable=False, index=True)
    customer_id = Column(UUID(as_uuid=True), ForeignKey("customers.id", ondelete="SET NULL"), index=True)
    message_type = Column(String(20), nullable=False)
    agent_name = Column(String(100))
    message = Column(Text, nullable=False)
    intent = Column(String(100))
    entities = Column(JSON)
    confidence_score = Column(DECIMAL(3, 2))
    created_at = Column(DateTime, server_default=func.now())


class FraudAlert(Base):
    """Fraud Alert model"""
    __tablename__ = "fraud_alerts"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    alert_type = Column(String(50), nullable=False)
    entity_type = Column(String(50))
    entity_id = Column(UUID(as_uuid=True))
    customer_id = Column(UUID(as_uuid=True), ForeignKey("customers.id", ondelete="CASCADE"), index=True)
    fraud_score = Column(DECIMAL(3, 2), nullable=False)
    risk_level = Column(String(20))
    description = Column(Text)
    rules_triggered = Column(JSON)
    status = Column(String(20), default="open", index=True)
    resolved_at = Column(DateTime)
    resolution_notes = Column(Text)
    created_at = Column(DateTime, server_default=func.now(), index=True)
    
    # Relationships
    customer = relationship("Customer", back_populates="fraud_alerts")


class GeneralLedger(Base):
    """General Ledger for double-entry bookkeeping"""
    __tablename__ = "general_ledger"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    entry_id = Column(String(50), unique=True, nullable=False)
    transaction_id = Column(UUID(as_uuid=True), ForeignKey("transactions.id", ondelete="CASCADE"), index=True)
    account_code = Column(String(20), nullable=False, index=True)
    account_name = Column(String(100), nullable=False)
    debit_amount = Column(DECIMAL(15, 2), default=0.00)
    credit_amount = Column(DECIMAL(15, 2), default=0.00)
    currency = Column(String(3), default="USD")
    description = Column(Text)
    reference_number = Column(String(100))
    posting_date = Column(Date, nullable=False, index=True)
    created_at = Column(DateTime, server_default=func.now())


class LoanPayment(Base):
    """Loan Payment Schedule and History"""
    __tablename__ = "loan_payments"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    payment_id = Column(String(50), unique=True, nullable=False)
    loan_id = Column(UUID(as_uuid=True), ForeignKey("loans.id", ondelete="CASCADE"), index=True)
    payment_number = Column(Integer, nullable=False)
    due_date = Column(Date, nullable=False, index=True)
    payment_date = Column(Date, index=True)
    scheduled_amount = Column(DECIMAL(15, 2), nullable=False)
    paid_amount = Column(DECIMAL(15, 2), default=0.00)
    principal_amount = Column(DECIMAL(15, 2))
    interest_amount = Column(DECIMAL(15, 2))
    late_fee = Column(DECIMAL(15, 2), default=0.00)
    outstanding_balance = Column(DECIMAL(15, 2))
    status = Column(String(20), default="pending", index=True)
    payment_method = Column(String(50))
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    # Relationships
    loan = relationship("Loan", backref="payments")


class Investment(Base):
    """Investment Account and Holdings"""
    __tablename__ = "investments"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    investment_id = Column(String(50), unique=True, nullable=False)
    customer_id = Column(UUID(as_uuid=True), ForeignKey("customers.id", ondelete="CASCADE"), index=True)
    account_id = Column(UUID(as_uuid=True), ForeignKey("accounts.id"))
    investment_type = Column(String(50), nullable=False)
    symbol = Column(String(20), index=True)
    security_name = Column(String(255))
    quantity = Column(DECIMAL(15, 6), default=0.00)
    average_cost = Column(DECIMAL(15, 4))
    current_price = Column(DECIMAL(15, 4))
    market_value = Column(DECIMAL(15, 2))
    unrealized_gain_loss = Column(DECIMAL(15, 2))
    currency = Column(String(3), default="USD")
    status = Column(String(20), default="active", index=True)
    opened_at = Column(DateTime, server_default=func.now())
    closed_at = Column(DateTime)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    # Relationships
    customer = relationship("Customer", backref="investments")
    trades = relationship("Trade", back_populates="investment", cascade="all, delete-orphan")


class Trade(Base):
    """Securities Trades"""
    __tablename__ = "trades"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    trade_id = Column(String(50), unique=True, nullable=False)
    investment_id = Column(UUID(as_uuid=True), ForeignKey("investments.id", ondelete="CASCADE"), index=True)
    trade_type = Column(String(20), nullable=False)
    symbol = Column(String(20), nullable=False)
    quantity = Column(DECIMAL(15, 6), nullable=False)
    price = Column(DECIMAL(15, 4), nullable=False)
    total_amount = Column(DECIMAL(15, 2), nullable=False)
    commission = Column(DECIMAL(15, 2), default=0.00)
    fees = Column(DECIMAL(15, 2), default=0.00)
    currency = Column(String(3), default="USD")
    status = Column(String(20), default="pending", index=True)
    order_date = Column(DateTime, server_default=func.now())
    execution_date = Column(DateTime)
    settlement_date = Column(Date)
    created_at = Column(DateTime, server_default=func.now())
    
    # Relationships
    investment = relationship("Investment", back_populates="trades")


class PaymentInstruction(Base):
    """Payment Instructions and Orders"""
    __tablename__ = "payment_instructions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    payment_id = Column(String(50), unique=True, nullable=False)
    account_id = Column(UUID(as_uuid=True), ForeignKey("accounts.id", ondelete="CASCADE"), index=True)
    payment_type = Column(String(50), nullable=False)
    payment_method = Column(String(50), nullable=False)
    amount = Column(DECIMAL(15, 2), nullable=False)
    currency = Column(String(3), default="USD")
    beneficiary_name = Column(String(255), nullable=False)
    beneficiary_account = Column(String(100))
    beneficiary_bank = Column(String(255))
    routing_number = Column(String(50))
    swift_code = Column(String(20))
    reference = Column(String(255))
    description = Column(Text)
    status = Column(String(20), default="pending", index=True)
    scheduled_date = Column(Date)
    execution_date = Column(DateTime)
    settlement_date = Column(Date)
    confirmation_number = Column(String(100))
    failure_reason = Column(Text)
    created_at = Column(DateTime, server_default=func.now(), index=True)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    # Relationships
    account = relationship("Account", backref="payment_instructions")


class ComplianceCheck(Base):
    """AML/KYC Compliance Checks"""
    __tablename__ = "compliance_checks"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    check_id = Column(String(50), unique=True, nullable=False)
    customer_id = Column(UUID(as_uuid=True), ForeignKey("customers.id", ondelete="CASCADE"), index=True)
    check_type = Column(String(50), nullable=False)
    check_category = Column(String(50))
    status = Column(String(20), default="pending", index=True)
    result = Column(String(20))
    risk_level = Column(String(20))
    score = Column(DECIMAL(3, 2))
    details = Column(JSON)
    sanctions_hit = Column(Boolean, default=False, index=True)
    pep_match = Column(Boolean, default=False, index=True)
    adverse_media = Column(Boolean, default=False)
    checked_by = Column(String(100))
    checked_at = Column(DateTime)
    review_notes = Column(Text)
    created_at = Column(DateTime, server_default=func.now(), index=True)
    
    # Relationships
    customer = relationship("Customer", backref="compliance_checks")


class FraudScore(Base):
    """ML-based Fraud Detection Scores"""
    __tablename__ = "fraud_scores"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    entity_type = Column(String(50), nullable=False)
    entity_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    model_name = Column(String(100), nullable=False)
    model_version = Column(String(20))
    fraud_score = Column(DECIMAL(5, 4), nullable=False)
    risk_category = Column(String(20))
    features = Column(JSON)
    anomaly_indicators = Column(JSON)
    contributing_factors = Column(JSON)
    confidence_score = Column(DECIMAL(3, 2))
    threshold_exceeded = Column(Boolean, default=False, index=True)
    action_taken = Column(String(50))
    created_at = Column(DateTime, server_default=func.now(), index=True)


class Biller(Base):
    """Biller/Utility Company model"""
    __tablename__ = "billers"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    biller_id = Column(String(50), unique=True, nullable=False)
    name = Column(String(255), nullable=False)
    category = Column(String(50))  # Utility, Telecom, Insurance, etc.
    status = Column(String(20), default="active")
    created_at = Column(DateTime, server_default=func.now())


class BillPayment(Base):
    """Bill Payment model"""
    __tablename__ = "bill_payments"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    payment_id = Column(String(50), unique=True, nullable=False)
    account_id = Column(UUID(as_uuid=True), ForeignKey("accounts.id", ondelete="CASCADE"), index=True)
    biller_id = Column(UUID(as_uuid=True), ForeignKey("billers.id"), index=True)
    amount = Column(DECIMAL(15, 2), nullable=False)
    currency = Column(String(3), default="USD")
    reference_number = Column(String(100))
    status = Column(String(20), default="pending", index=True)
    payment_date = Column(DateTime, server_default=func.now())
    created_at = Column(DateTime, server_default=func.now())
    
    # Relationships
    account = relationship("Account", backref="bill_payments")
    biller = relationship("Biller", backref="payments")


class Beneficiary(Base):
    """Beneficiary/Payee model"""
    __tablename__ = "beneficiaries"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    customer_id = Column(UUID(as_uuid=True), ForeignKey("customers.id", ondelete="CASCADE"), index=True)
    name = Column(String(255), nullable=False)
    account_number = Column(String(50), nullable=False)
    bank_name = Column(String(255))
    routing_number = Column(String(50))
    nickname = Column(String(100))
    status = Column(String(20), default="active")
    created_at = Column(DateTime, server_default=func.now())
    
    # Relationships
    customer = relationship("Customer", backref="beneficiaries")

