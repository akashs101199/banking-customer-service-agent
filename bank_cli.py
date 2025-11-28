#!/usr/bin/env python3
"""
Agent-Driven Banking System - CLI Interface
"""
import asyncio
import sys
import uuid
import logging
import os
from datetime import datetime
from typing import Dict, Any

# Disable noisy logs
logging.getLogger("sqlalchemy").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from agents.banking_crew import banking_crew
from agents.orchestrator import orchestrator # Keep for fallback or hybrid if needed
from database.connection import init_database, db_manager
from database.models import Customer, Account

# ANSI Colors
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

def print_header():
    print(f"\n{Colors.HEADER}{Colors.BOLD}" + "="*60)
    print("🏦  AGENT-DRIVEN BANKING SYSTEM")
    print("="*60 + f"{Colors.ENDC}\n")

def print_agent_response(response: Dict[str, Any]):
    agent_name = response.get("agent", "System")
    answer = response.get("answer", "")
    
    print(f"\n{Colors.BLUE}{Colors.BOLD}🤖 {agent_name}:{Colors.ENDC}")
    print(f"{answer}\n")
    
    if response.get("next_steps"):
        print(f"{Colors.CYAN}Suggested Actions:{Colors.ENDC}")
        for step in response["next_steps"]:
            print(f"  • {step}")
        print()

async def login_flow():
    """Simple login flow to get customer context"""
    print(f"{Colors.GREEN}Welcome! Please log in to access your account.{Colors.ENDC}")
    print("(For demo purposes, we'll create a new customer if one doesn't exist)")
    
    name = input(f"{Colors.BOLD}Enter your name: {Colors.ENDC}").strip()
    if not name:
        name = "John Doe"
        
    # In a real app, we'd authenticate. Here we just find or create a demo user.
    with db_manager.get_session() as db:
        # Try to find by name (simplified)
        parts = name.split()
        first_name = parts[0]
        last_name = parts[1] if len(parts) > 1 else "User"
        
        customer = db.query(Customer).filter(
            Customer.first_name == first_name,
            Customer.last_name == last_name
        ).first()
        
        if not customer:
            print(f"{Colors.WARNING}Customer not found. Creating new demo customer...{Colors.ENDC}")
            customer_id = f"CUST{uuid.uuid4().hex[:8].upper()}"
            customer = Customer(
                customer_id=customer_id,
                first_name=first_name,
                last_name=last_name,
                email=f"{first_name.lower()}.{last_name.lower()}@example.com",
                phone="+15550000000",
                kyc_status="verified",
                status="active"
            )
            db.add(customer)
            db.commit()
            
            # Create a default account
            account = Account(
                account_number=f"ACC{uuid.uuid4().hex[:10].upper()}",
                customer_id=customer.id,
                account_type="savings",
                currency="USD",
                balance=10000.00,
                available_balance=10000.00,
                status="active"
            )
            db.add(account)
            db.commit()
            print(f"{Colors.GREEN}Created new customer and account with $10,000 balance.{Colors.ENDC}")
            
        return {
            "customer_id": str(customer.id),
            "first_name": customer.first_name,
            "last_name": customer.last_name,
            "email": customer.email
        }

async def main():
    # Initialize system
    print("Initializing system...")
    init_database()
    
    print_header()
    
    # Login
    try:
        customer_info = await login_flow()
    except Exception as e:
        print(f"{Colors.FAIL}Login failed: {e}{Colors.ENDC}")
        return

    session_id = str(uuid.uuid4())
    print(f"\n{Colors.GREEN}✅ Logged in as {customer_info['first_name']} {customer_info['last_name']}{Colors.ENDC}")
    print(f"{Colors.CYAN}You can now chat with your AI banking assistant.{Colors.ENDC}")
    print(f"{Colors.CYAN}Try asking about:{Colors.ENDC}")
    print("  • Bill Payments & Beneficiaries")
    print("  • Account Statements")
    print("  • Card Controls (PIN, Limits)")
    print("  • Investments & Trading")
    print("Type 'exit' or 'quit' to end the session.\n")
    
    # Chat loop
    while True:
        try:
            user_input = input(f"{Colors.BOLD}You: {Colors.ENDC}").strip()
            
            if user_input.lower() in ['exit', 'quit']:
                print(f"\n{Colors.GREEN}Thank you for banking with us. Goodbye! 👋{Colors.ENDC}")
                break
            
            if not user_input:
                continue
                
            # Process query
            with db_manager.get_session() as db:
                # Pass db session in context if needed, though agents usually get their own
                context = {
                    "customer_info": customer_info,
                    "db_session": None # Agents manage their own sessions usually
                }
                
                # Use CrewAI for processing
                print(f"{Colors.CYAN}Thinking... (CrewAI is working){Colors.ENDC}")
                
                # CrewAI returns a string result
                result = banking_crew.run(
                    query=user_input,
                    customer_context=customer_info
                )
                
                # Format as a response dict for the printer
                response = {
                    "agent": "BankingCrew",
                    "answer": str(result),
                    "success": True
                }
                
                print_agent_response(response)
                
        except KeyboardInterrupt:
            print(f"\n{Colors.GREEN}Goodbye! 👋{Colors.ENDC}")
            break
        except Exception as e:
            print(f"{Colors.FAIL}An error occurred: {e}{Colors.ENDC}")

if __name__ == "__main__":
    asyncio.run(main())
