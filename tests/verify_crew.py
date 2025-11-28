"""
Verification Script for CrewAI Banking System
Tests the CrewAI integration with the banking agents.
"""
import sys
import os
import logging

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.banking_crew import banking_crew
from database.connection import init_database, db_manager
from database.models import Customer, Account
import uuid

# Configure logging
logging.basicConfig(level=logging.INFO)

def run_verification():
    print("🚀 Starting CrewAI Verification...")
    
    # Initialize DB
    init_database()
    
    # Create test customer
    customer_id = f"CREW{uuid.uuid4().hex[:8].upper()}"
    with db_manager.get_session() as db:
        customer = Customer(
            customer_id=customer_id,
            first_name="Crew",
            last_name="Tester",
            email=f"crew.{uuid.uuid4().hex[:4]}@example.com",
            phone="+15550000000",
            kyc_status="verified",
            status="active"
        )
        db.add(customer)
        db.commit()
        
        account = Account(
            account_number=f"ACC{uuid.uuid4().hex[:10].upper()}",
            customer_id=customer.id,
            account_type="savings",
            currency="USD",
            balance=50000.00,
            available_balance=50000.00,
            status="active"
        )
        db.add(account)
        db.commit()
        
        print(f"✅ Created test customer: {customer_id}")
        
        customer_context = {
            "customer_id": str(customer.id),
            "first_name": customer.first_name,
            "last_name": customer.last_name,
            "email": customer.email
        }

    # Test Queries
    queries = [
        "What is my account balance?",
        "Transfer $100 to account ACC1234567890",
        "I want to buy 5 shares of MSFT"
    ]
    
    for query in queries:
        print(f"\n📝 Query: {query}")
        try:
            result = banking_crew.run(query, customer_context)
            print(f"   🤖 Crew Response: {result}")
            print("   ✅ Success")
        except Exception as e:
            print(f"   ❌ Failed: {e}")
            import traceback
            traceback.print_exc()

    print("\n✅ CrewAI Verification Complete!")

if __name__ == "__main__":
    run_verification()
