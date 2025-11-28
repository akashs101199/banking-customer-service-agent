"""
Verification Script for Agent-Driven Banking System
Simulates a user session to verify all agents including the new Investment Agent.
"""
import asyncio
import uuid
import logging
import sys
import os

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.orchestrator import orchestrator
from database.connection import init_database, db_manager
from database.models import Customer, Account

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("verification")

async def run_verification():
    print("🚀 Starting System Verification...")
    
    # Initialize DB
    init_database()
    
    # Create test customer
    customer_id = f"TEST{uuid.uuid4().hex[:8].upper()}"
    with db_manager.get_session() as db:
        customer = Customer(
            customer_id=customer_id,
            first_name="Test",
            last_name="User",
            email=f"test.{uuid.uuid4().hex[:4]}@example.com",
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
        
        customer_db_id = str(customer.id)
        print(f"✅ Created test customer: {customer_id}")

    # Context for agents
    context = {
        "customer_info": {
            "customer_id": customer_db_id,
            "first_name": "Test",
            "last_name": "User"
        }
    }
    
    session_id = str(uuid.uuid4())
    
    # Test Cases
    test_queries = [
        "What is my account balance?",
        "I want to buy 10 shares of AAPL",
        "Show me my investment portfolio",
        "I need a loan for $5000 for home improvement",
        "Check my transaction history",
        "Add beneficiary John Doe with account number 1234567890",
        "Pay bill to Electric Company for $150",
        "Generate my account statement",
        "Change my card PIN to 1234",
        "Set my card spending limit to 2000",
        "Transfer $1000000 to John" # Should fail with InsufficientFundsError
    ]
    
    for query in test_queries:
        print(f"\n📝 Query: {query}")
        try:
            response = orchestrator.process_query(
                query=query,
                session_id=session_id,
                context=context
            )
            
            agent = response.get("agent", "unknown")
            success = response.get("success", False)
            answer = response.get("answer", "")[:100] + "..."
            
            print(f"   🤖 Agent: {agent}")
            print(f"   ✅ Success: {success}")
            print(f"   📄 Response: {answer}")
            
            if not success:
                print(f"   ❌ FAILED: {response.get('error')}")
                
        except Exception as e:
            print(f"   ❌ EXCEPTION: {e}")
            import traceback
            traceback.print_exc()

    print("\n✅ Verification Complete!")

if __name__ == "__main__":
    asyncio.run(run_verification())
