"""
Demo Script for Banking AI
Demonstrates various banking operations without human intervention
"""
import asyncio
import time
from typing import List, Dict, Any
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.orchestrator import orchestrator
from database.connection import init_database
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class BankingAIDemo:
    """Demo class for banking AI operations"""
    
    def __init__(self):
        self.session_id = "demo_session_001"
        self.demo_context = {}
    
    def print_section(self, title: str):
        """Print section header"""
        print("\n" + "="*80)
        print(f"  {title}")
        print("="*80 + "\n")
    
    def print_interaction(self, user_message: str, ai_response: Dict[str, Any]):
        """Print user-AI interaction"""
        print(f"👤 User: {user_message}")
        print(f"🤖 AI ({ai_response.get('agent', 'Unknown')}): {ai_response.get('answer', 'No response')}")
        
        if ai_response.get('data'):
            print(f"   📊 Data: {ai_response['data']}")
        
        if ai_response.get('next_steps'):
            print(f"   ➡️  Next Steps: {', '.join(ai_response['next_steps'])}")
        
        print()
        time.sleep(1)  # Pause for readability
    
    def run_demo(self):
        """Run complete demo"""
        
        print("\n" + "🏦"*40)
        print("  BANKING CUSTOMER SERVICE AGENTIC AI - DEMO")
        print("  Fully Autonomous Banking Operations")
        print("🏦"*40 + "\n")
        
        # Initialize database
        try:
            init_database()
            logger.info("Database initialized")
        except Exception as e:
            logger.warning(f"Database initialization: {e}")
        
        # Demo scenarios
        self.demo_account_creation()
        self.demo_kyc_verification()
        self.demo_balance_inquiry()
        self.demo_card_application()
        self.demo_transaction_history()
        self.demo_fund_transfer()
        self.demo_card_management()
        self.demo_general_inquiry()
        
        print("\n" + "="*80)
        print("  DEMO COMPLETE")
        print("="*80 + "\n")
    
    def demo_account_creation(self):
        """Demo: Account Creation"""
        self.print_section("SCENARIO 1: Account Creation")
        
        queries = [
            "Hi, I want to open a new savings account",
            "My name is Sarah Johnson, email sarah.johnson@email.com, phone +1-555-0123",
        ]
        
        for query in queries:
            response = orchestrator.process_query(
                query=query,
                session_id=self.session_id,
                context={
                    "first_name": "Sarah",
                    "last_name": "Johnson",
                    "email": "sarah.johnson@email.com",
                    "phone": "+1-555-0123",
                    "account_type": "savings",
                    "ready_to_create": True  # Trigger account creation
                }
            )
            self.print_interaction(query, response)
            
            # Store account number if created
            if response.get('data', {}).get('account_number'):
                self.demo_context['account_number'] = response['data']['account_number']
                self.demo_context['customer_id'] = response['data'].get('customer_id')
    
    def demo_kyc_verification(self):
        """Demo: KYC Verification"""
        self.print_section("SCENARIO 2: KYC Verification Status")
        
        query = "What's my KYC verification status?"
        response = orchestrator.process_query(
            query=query,
            session_id=self.session_id,
            context=self.demo_context
        )
        self.print_interaction(query, response)
    
    def demo_balance_inquiry(self):
        """Demo: Balance Inquiry"""
        self.print_section("SCENARIO 3: Balance Inquiry")
        
        query = "What's my account balance?"
        response = orchestrator.process_query(
            query=query,
            session_id=self.session_id,
            context=self.demo_context
        )
        self.print_interaction(query, response)
    
    def demo_card_application(self):
        """Demo: Card Application"""
        self.print_section("SCENARIO 4: Credit Card Application")
        
        query = "I want to apply for a credit card"
        response = orchestrator.process_query(
            query=query,
            session_id=self.session_id,
            context=self.demo_context
        )
        self.print_interaction(query, response)
        
        # Store card info if created
        if response.get('data', {}).get('card_id'):
            self.demo_context['card_number'] = response['data'].get('masked_card_number', '')
    
    def demo_transaction_history(self):
        """Demo: Transaction History"""
        self.print_section("SCENARIO 5: Transaction History")
        
        query = "Show me my recent transactions"
        response = orchestrator.process_query(
            query=query,
            session_id=self.session_id,
            context=self.demo_context
        )
        self.print_interaction(query, response)
    
    def demo_fund_transfer(self):
        """Demo: Fund Transfer"""
        self.print_section("SCENARIO 6: Fund Transfer")
        
        query = "I want to transfer $500 to account ACC9876543210"
        response = orchestrator.process_query(
            query=query,
            session_id=self.session_id,
            context={
                **self.demo_context,
                "from_account": self.demo_context.get('account_number', 'ACC1234567890'),
                "to_account": "ACC9876543210",
                "amount": 500,
                "description": "Demo transfer"
            }
        )
        self.print_interaction(query, response)
    
    def demo_card_management(self):
        """Demo: Card Management"""
        self.print_section("SCENARIO 7: Card Inquiry")
        
        query = "Show me my cards"
        response = orchestrator.process_query(
            query=query,
            session_id=self.session_id,
            context=self.demo_context
        )
        self.print_interaction(query, response)
    
    def demo_general_inquiry(self):
        """Demo: General Inquiry"""
        self.print_section("SCENARIO 8: General Banking Inquiry")
        
        queries = [
            "What types of accounts do you offer?",
            "How do I set up direct deposit?",
            "What are your customer service hours?"
        ]
        
        for query in queries:
            response = orchestrator.process_query(
                query=query,
                session_id=self.session_id,
                context=self.demo_context
            )
            self.print_interaction(query, response)


def main():
    """Main entry point"""
    print("\n🚀 Starting Banking AI Demo...\n")
    
    try:
        demo = BankingAIDemo()
        demo.run_demo()
        
        print("\n✅ Demo completed successfully!")
        print("\n💡 Tip: Start the API server with 'python api/main.py' to interact via REST API")
        print("   Then visit http://localhost:8000/docs for interactive API documentation\n")
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Demo interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Demo error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
