-- Banking Customer Service AI - Database Schema
-- PostgreSQL Database Schema

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Customers Table
CREATE TABLE customers (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    customer_id VARCHAR(50) UNIQUE NOT NULL,
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    phone VARCHAR(20),
    date_of_birth DATE,
    nationality VARCHAR(50),
    address_line1 VARCHAR(255),
    address_line2 VARCHAR(255),
    city VARCHAR(100),
    state VARCHAR(100),
    postal_code VARCHAR(20),
    country VARCHAR(100),
    kyc_status VARCHAR(20) DEFAULT 'pending', -- pending, verified, rejected
    kyc_verified_at TIMESTAMP,
    risk_score DECIMAL(3, 2) DEFAULT 0.0,
    status VARCHAR(20) DEFAULT 'active', -- active, suspended, closed
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Accounts Table
CREATE TABLE accounts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    account_number VARCHAR(50) UNIQUE NOT NULL,
    customer_id UUID REFERENCES customers(id) ON DELETE CASCADE,
    account_type VARCHAR(20) NOT NULL, -- savings, checking, business
    currency VARCHAR(3) DEFAULT 'USD',
    balance DECIMAL(15, 2) DEFAULT 0.00,
    available_balance DECIMAL(15, 2) DEFAULT 0.00,
    overdraft_limit DECIMAL(15, 2) DEFAULT 0.00,
    interest_rate DECIMAL(5, 4) DEFAULT 0.0000,
    status VARCHAR(20) DEFAULT 'active', -- active, frozen, closed
    opened_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    closed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Transactions Table
CREATE TABLE transactions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    transaction_id VARCHAR(50) UNIQUE NOT NULL,
    account_id UUID REFERENCES accounts(id) ON DELETE CASCADE,
    transaction_type VARCHAR(20) NOT NULL, -- debit, credit, transfer
    amount DECIMAL(15, 2) NOT NULL,
    currency VARCHAR(3) DEFAULT 'USD',
    balance_after DECIMAL(15, 2),
    description TEXT,
    category VARCHAR(50), -- groceries, utilities, salary, etc.
    reference_number VARCHAR(100),
    counterparty_name VARCHAR(255),
    counterparty_account VARCHAR(50),
    status VARCHAR(20) DEFAULT 'completed', -- pending, completed, failed, reversed
    fraud_score DECIMAL(3, 2) DEFAULT 0.0,
    is_flagged BOOLEAN DEFAULT FALSE,
    transaction_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Cards Table
CREATE TABLE cards (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    card_number VARCHAR(16) UNIQUE NOT NULL,
    card_type VARCHAR(20) NOT NULL, -- debit, credit
    account_id UUID REFERENCES accounts(id) ON DELETE CASCADE,
    customer_id UUID REFERENCES customers(id) ON DELETE CASCADE,
    card_holder_name VARCHAR(255) NOT NULL,
    expiry_date DATE NOT NULL,
    cvv VARCHAR(4) NOT NULL, -- Encrypted in application
    credit_limit DECIMAL(15, 2), -- For credit cards
    available_credit DECIMAL(15, 2), -- For credit cards
    pin_hash VARCHAR(255), -- Hashed PIN
    status VARCHAR(20) DEFAULT 'pending', -- pending, active, blocked, expired, cancelled
    issued_at TIMESTAMP,
    activated_at TIMESTAMP,
    blocked_at TIMESTAMP,
    block_reason TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- KYC Documents Table
CREATE TABLE kyc_documents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    customer_id UUID REFERENCES customers(id) ON DELETE CASCADE,
    document_type VARCHAR(50) NOT NULL, -- id_proof, address_proof, photo
    document_number VARCHAR(100),
    file_path VARCHAR(500),
    file_name VARCHAR(255),
    file_size_kb INTEGER,
    mime_type VARCHAR(100),
    ocr_text TEXT,
    verification_status VARCHAR(20) DEFAULT 'pending', -- pending, verified, rejected
    verification_score DECIMAL(3, 2),
    verified_by VARCHAR(50), -- agent_name or 'system'
    verified_at TIMESTAMP,
    rejection_reason TEXT,
    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Loans Table
CREATE TABLE loans (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    loan_id VARCHAR(50) UNIQUE NOT NULL,
    customer_id UUID REFERENCES customers(id) ON DELETE CASCADE,
    account_id UUID REFERENCES accounts(id),
    loan_type VARCHAR(50) NOT NULL, -- personal, home, auto, business
    principal_amount DECIMAL(15, 2) NOT NULL,
    interest_rate DECIMAL(5, 4) NOT NULL,
    tenure_months INTEGER NOT NULL,
    emi_amount DECIMAL(15, 2) NOT NULL,
    outstanding_balance DECIMAL(15, 2),
    status VARCHAR(20) DEFAULT 'pending', -- pending, approved, disbursed, active, closed, defaulted
    application_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    approval_date TIMESTAMP,
    disbursement_date TIMESTAMP,
    maturity_date DATE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Audit Logs Table
CREATE TABLE audit_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    event_type VARCHAR(100) NOT NULL,
    entity_type VARCHAR(50), -- customer, account, transaction, card
    entity_id UUID,
    user_id UUID,
    agent_name VARCHAR(100),
    action VARCHAR(100) NOT NULL,
    details JSONB,
    ip_address VARCHAR(45),
    user_agent TEXT,
    status VARCHAR(20), -- success, failure
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Conversation History Table
CREATE TABLE conversation_history (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id VARCHAR(100) NOT NULL,
    customer_id UUID REFERENCES customers(id) ON DELETE SET NULL,
    message_type VARCHAR(20) NOT NULL, -- user, agent, system
    agent_name VARCHAR(100),
    message TEXT NOT NULL,
    intent VARCHAR(100),
    entities JSONB,
    confidence_score DECIMAL(3, 2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Fraud Alerts Table
CREATE TABLE fraud_alerts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    alert_type VARCHAR(50) NOT NULL,
    entity_type VARCHAR(50), -- transaction, account, card
    entity_id UUID,
    customer_id UUID REFERENCES customers(id) ON DELETE CASCADE,
    fraud_score DECIMAL(3, 2) NOT NULL,
    risk_level VARCHAR(20), -- low, medium, high, critical
    description TEXT,
    rules_triggered JSONB,
    status VARCHAR(20) DEFAULT 'open', -- open, investigating, resolved, false_positive
    resolved_at TIMESTAMP,
    resolution_notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for Performance
CREATE INDEX idx_customers_email ON customers(email);
CREATE INDEX idx_customers_customer_id ON customers(customer_id);
CREATE INDEX idx_customers_kyc_status ON customers(kyc_status);

CREATE INDEX idx_accounts_customer_id ON accounts(customer_id);
CREATE INDEX idx_accounts_account_number ON accounts(account_number);
CREATE INDEX idx_accounts_status ON accounts(status);

CREATE INDEX idx_transactions_account_id ON transactions(account_id);
CREATE INDEX idx_transactions_transaction_date ON transactions(transaction_date);
CREATE INDEX idx_transactions_status ON transactions(status);
CREATE INDEX idx_transactions_is_flagged ON transactions(is_flagged);

CREATE INDEX idx_cards_customer_id ON cards(customer_id);
CREATE INDEX idx_cards_account_id ON cards(account_id);
CREATE INDEX idx_cards_status ON cards(status);

CREATE INDEX idx_kyc_documents_customer_id ON kyc_documents(customer_id);
CREATE INDEX idx_kyc_documents_verification_status ON kyc_documents(verification_status);

CREATE INDEX idx_loans_customer_id ON loans(customer_id);
CREATE INDEX idx_loans_status ON loans(status);

CREATE INDEX idx_audit_logs_entity_type_id ON audit_logs(entity_type, entity_id);
CREATE INDEX idx_audit_logs_created_at ON audit_logs(created_at);

CREATE INDEX idx_conversation_history_session_id ON conversation_history(session_id);
CREATE INDEX idx_conversation_history_customer_id ON conversation_history(customer_id);

CREATE INDEX idx_fraud_alerts_customer_id ON fraud_alerts(customer_id);
CREATE INDEX idx_fraud_alerts_status ON fraud_alerts(status);
CREATE INDEX idx_fraud_alerts_created_at ON fraud_alerts(created_at);

-- Triggers for updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_customers_updated_at BEFORE UPDATE ON customers
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_accounts_updated_at BEFORE UPDATE ON accounts
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_cards_updated_at BEFORE UPDATE ON cards
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_loans_updated_at BEFORE UPDATE ON loans
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
