"""
Production Banking AI System Demo
Comprehensive demonstration of all banking features and AI agents
"""
import asyncio
from decimal import Decimal
import uuid
from datetime import datetime, date
from sqlalchemy.orm import Session

# Core banking
from core_banking.engine import banking_engine, transaction_engine
from core_banking.payment_processor import payment_processor
from core_banking.loan_engine import loan_engine
from core_banking.investment_manager import investment_manager

# AI Agents
from agents.loan_underwriting_agent import loan_underwriting_agent
from agents.fraud_detection_agent import fraud_detection_agent
from agents.compliance_agent import compliance_agent
from agents.account_agent import account_agent
from agents.transaction_agent import transaction_agent
from agents.card_agent import card_agent

# Database
from database.connection import get_db
from database.models import Customer, Account, Loan

print("=" * 80)
print("🏦  PRODUCTION-LEVEL AI-MANAGED BANK DEMONSTRATION")
print("=" * 80)
print()


def demo_section(title: str):
    """Print formatted section header"""
    print()
    print("─" * 80)
    print(f"📋 {title}")
    print("─" * 80)
    print()


async def main():
    """Run comprehensive banking system demonstration"""
    
    # Get database session
    db = next(get_db())
    
    try:
        # ============================================================================
        # SECTION 1: Account Creation & KYC
        # ============================================================================
        demo_section("SECTION 1: Customer Onboarding & KYC Verification")
        
        print("Creating new customer: Sarah Johnson")
        
        # Create customer
        customer = Customer(
            customer_id=f"CUST{uuid.uuid4().hex[:8].upper()}",
            first_name="Sarah",
            last_name="Johnson",
            email="sarah.johnson@example.com",
            phone="+1-555-0123",
            date_of_birth=date(1990, 5, 15),
            nationality="USA",
            address_line1="123 Main Street",
            city="New York",
            state="NY",
            postal_code="10001",
            country="USA",
            kyc_status="pending",
            risk_score=Decimal("0.2")
        )
        db.add(customer)
        db.flush()
        
        print(f"✅ Customer created: {customer.customer_id}")
        print(f"   Name: {customer.first_name} {customer.last_name}")
        print(f"   Email: {customer.email}")
        
        # Run KYC verification
        print("\n🔍 Running KYC verification...")
        kyc_result = compliance_agent.verify_kyc(db, customer.id)
        print(f"   KYC Status: {kyc_result['kyc_status']}")
        print(f"   Risk Level: {kyc_result['risk_level']}")
        
        # Run sanctions screening
        print("\n🔍 Running sanctions screening...")
        sanctions_result = compliance_agent.screen_sanctions(db, customer.id)
        print(f"   Sanctions Check: {sanctions_result['result']}")
        print(f"   PEP Match: {sanctions_result['pep_match']}")
        
        # ============================================================================
        # SECTION 2: Account Opening & Initial Deposit
        # ============================================================================
        demo_section("SECTION 2: Account Opening & Core Banking")
        
        print("Opening savings account with initial deposit...")
        
        # Create account with initial deposit
        account = banking_engine.create_account(
            db=db,
            customer_id=customer.id,
            account_type="savings",
            currency="USD",
            initial_deposit=Decimal("10000.00")
        )
        
        print(f"✅ Account opened: {account.account_number}")
        print(f"   Type: {account.account_type}")
        print(f"   Initial Balance: ${account.balance:,.2f}")
        
        # Process additional deposit
        print("\n💰 Processing additional deposit...")
        deposit_txn = transaction_engine.process_transaction(
            db=db,
            account_id=account.id,
            transaction_type="deposit",
            amount=Decimal("5000.00"),
            description="Additional deposit"
        )
        
        print(f"✅ Deposit completed: {deposit_txn.transaction_id}")
        print(f"   Amount: ${deposit_txn.amount:,.2f}")
        print(f"   New Balance: ${deposit_txn.balance_after:,.2f}")
        
        # ============================================================================
        # SECTION 3: Payment Processing
        # ============================================================================
        demo_section("SECTION 3: Payment Processing")
        
        print("Initiating ACH payment...")
        
        payment = payment_processor.initiate_payment(
            db=db,
            account_id=account.id,
            payment_type="bill_payment",
            payment_method="ach",
            amount=Decimal("250.00"),
            beneficiary_name="Electric Company",
            beneficiary_account="123456789",
            routing_number="021000021",
            description="Monthly electricity bill"
        )
        
        print(f"✅ Payment initiated: {payment.payment_id}")
        print(f"   Method: {payment.payment_method.upper()}")
        print(f"   Amount: ${payment.amount:,.2f}")
        print(f"   Beneficiary: {payment.beneficiary_name}")
        print(f"   Status: {payment.status}")
        
        # ============================================================================
        # SECTION 4: Investment Trading
        # ============================================================================
        demo_section("SECTION 4: Investment Management")
        
        print("Placing stock trade order...")
        
        # Buy Apple stock
        trade = investment_manager.place_order(
            db=db,
            customer_id=customer.id,
            trade_type="buy",
            symbol="AAPL",
            quantity=Decimal("10"),
            price=Decimal("175.50"),
            investment_type="stock"
        )
        
        print(f"✅ Trade executed: {trade.trade_id}")
        print(f"   Type: {trade.trade_type.upper()}")
        print(f"   Symbol: {trade.symbol}")
        print(f"   Quantity: {trade.quantity}")
        print(f"   Price: ${trade.price:,.2f}")
        print(f"   Total: ${trade.total_amount:,.2f}")
        
        # Update market price (simulate price change)
        investment_manager.update_market_prices(db, "AAPL", Decimal("180.25"))
        
        # Get portfolio
        portfolio = investment_manager.get_portfolio(db, customer.id)
        print(f"\n📊 Portfolio Summary:")
        print(f"   Total Market Value: ${portfolio['total_market_value']:,.2f}")
        print(f"   Total Gain/Loss: ${portfolio['total_gain_loss']:,.2f}")
        print(f"   Return: {portfolio['total_return_pct']:.2f}%")
        
        # ============================================================================
        # SECTION 5: Loan Application & Underwriting
        # ============================================================================
        demo_section("SECTION 5: AI Loan Underwriting")
        
        print("Applying for personal loan...")
        
        # Create loan application
        loan = loan_engine.create_loan_application(
            db=db,
            customer_id=customer.id,
            loan_type="personal",
            principal_amount=Decimal("25000.00"),
            tenure_months=36,
            account_id=account.id
        )
        
        print(f"✅ Loan application created: {loan.loan_id}")
        print(f"   Type: {loan.loan_type}")
        print(f"   Amount: ${loan.principal_amount:,.2f}")
        print(f"   Tenure: {loan.tenure_months} months")
        print(f"   EMI: ${loan.emi_amount:,.2f}")
        
        # Run AI underwriting
        print("\n🤖 Running AI underwriting analysis...")
        underwriting = loan_underwriting_agent.underwrite_loan(
            db=db,
            loan_id=loan.id,
            customer_id=customer.id,
            amount=loan.principal_amount,
            loan_type=loan.loan_type
        )
        
        print(f"   Decision: {'APPROVED ✅' if underwriting['approved'] else 'DECLINED ❌'}")
        print(f"   Credit Score: {underwriting['credit_score']}")
        print(f"   DTI Ratio: {underwriting['dti_ratio']:.2%}")
        print(f"   Risk Category: {underwriting['risk_category']}")
        print(f"   Interest Rate: {underwriting['interest_rate']:.2%} APR")
        print(f"   Confidence: {underwriting['confidence']:.2f}")
        
        if underwriting['approved']:
            # Approve and disburse loan
            loan_engine.approve_loan(db, loan.id)
            print(f"\n✅ Loan approved and disbursed!")
            
            # Get loan details
            loan_details = loan_engine.get_loan_details(db, loan.loan_id)
            print(f"   Disbursement Date: {loan_details['disbursement_date']}")
            print(f"   Maturity Date: {loan_details['maturity_date']}")
            next_payment = loan_details.get('next_payment')
            if next_payment:
                print(f"   Next Payment: ${next_payment['amount']:,.2f} on {next_payment['due_date']}")
        
        # ============================================================================
        # SECTION 6: Fraud Detection
        # ============================================================================
        demo_section("SECTION 6: AI Fraud Detection")
        
        print("Simulating high-risk transaction...")
        
        # Create suspicious transaction
        suspicious_txn = transaction_engine.process_transaction(
            db=db,
            account_id=account.id,
            transaction_type="withdrawal",
            amount=Decimal("8500.00"),
            description="Large ATM withdrawal"
        )
        
        print(f"✅ Transaction created: {suspicious_txn.transaction_id}")
        print(f"   Amount: ${suspicious_txn.amount:,.2f}")
        
        # Run fraud detection
        print("\n🔍 Running AI fraud detection...")
        fraud_analysis = fraud_detection_agent.analyze_transaction(
            db=db,
            transaction_id=suspicious_txn.id
        )
        
        print(f"   Fraud Score: {fraud_analysis['fraud_score']:.3f}")
        print(f"   Risk Level: {fraud_analysis['risk_level'].upper()}")
        print(f"   Rule-Based Score: {fraud_analysis['rule_based_score']:.3f}")
        print(f"   ML Score: {fraud_analysis['ml_score']:.3f}")
        print(f"   Action: {fraud_analysis['action_taken']}")
        
        if fraud_analysis['indicators']:
            print(f"\n   🚨 Red Flags Detected:")
            for indicator in fraud_analysis['indicators']:
                print(f"      • {indicator['description']} ({indicator['severity']})")
        
        # ============================================================================
        # SECTION 7: AML Monitoring
        # ============================================================================
        demo_section("SECTION 7: AML Compliance Monitoring")
        
        print("Running AML monitoring...")
        
        aml_result = compliance_agent.monitor_aml(db, customer.id)
        
        print(f"   SAR Required: {'YES ⚠️' if aml_result['sar_required'] else 'NO ✅'}")
        print(f"   Risk Level: {aml_result['risk_level'].upper()}")
        print(f"   Suspicious Patterns: {aml_result['pattern_count']}")
        
        if aml_result['suspicious_patterns']:
            print(f"\n   📋 Detected Patterns:")
            for pattern in aml_result['suspicious_patterns']:
                print(f"      • {pattern.get('description', 'Unknown pattern')}")
        
        # ============================================================================
        # SECTION 8: Account Summary
        # ============================================================================
        demo_section("SECTION 8: Complete Account Summary")
        
        # Get updated account balance
        balance_info = transaction_engine.get_account_balance(db, account.id)
        
        print(f"👤 Customer: {customer.first_name} {customer.last_name}")
        print(f"   Customer ID: {customer.customer_id}")
        print(f"   KYC Status: {customer.kyc_status}")
        print()
        print(f"💰 Account: {balance_info['account_number']}")
        print(f"   Type: {balance_info['account_type']}")
        print(f"   Balance: ${balance_info['balance']:,.2f}")
        print(f"   Status: {balance_info['status']}")
        print()
        print(f"💳 Active Loans: 1")
        print(f"   Outstanding: ${loan.outstanding_balance:,.2f}")
        print()
        print(f"📈 Investments: 1 holding")
        print(f"   Market Value: ${portfolio['total_market_value']:,.2f}")
        print(f"   Gain/Loss: ${portfolio['total_gain_loss']:,.2f}")
        
        # Commit all changes
        db.commit()
        
        print()
        print("=" * 80)
        print("✅ DEMONSTRATION COMPLETE")
        print("=" * 80)
        print()
        print("Summary:")
        print("  ✓ Customer onboarding with KYC/AML checks")
        print("  ✓ Account creation with real-time balance updates")
        print("  ✓ Payment processing (ACH/Wire/Card)")
        print("  ✓ Investment trading and portfolio management")
        print("  ✓ AI-powered loan underwriting")
        print("  ✓ Real-time fraud detection")
        print("  ✓ AML compliance monitoring")
        print()
        print("🎉 Production-Level AI Bank is fully operational!")
        print()
        
    except Exception as e:
        print(f"\n❌ Error during demonstration: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    asyncio.run(main())
