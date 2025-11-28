"""
Account Agent
Handles account creation, KYC verification, and account management
"""
from typing import Dict, Any, Optional
from datetime import datetime, date
import random
import string
from sqlalchemy.orm import Session

from agents.base_agent import BaseAgent
from database.models import Customer, Account, Transaction
from database.connection import db_manager
from security.audit_logger import audit_logger
from config import settings
from agents.exceptions import ResourceNotFoundError

class AccountAgent(BaseAgent):
    """Agent for account-related operations"""
    
    def __init__(self):
        super().__init__(
            name="AccountAgent",
            description="Handles account creation, KYC verification, and account management operations"
        )
    
    def process(
        self,
        query: str,
        context: Dict[str, Any],
        session_id: str
    ) -> Dict[str, Any]:
        """Process account-related queries"""
        try:
            if not self.validate_input(query):
                return self.create_response(
                    answer="I didn't quite understand that. Could you please rephrase your request?",
                    success=False
                )
            
            # Determine specific action
            query_lower = query.lower()
            
            if any(keyword in query_lower for keyword in ["open", "create", "new account"]):
                return self._handle_account_creation(query, context, session_id)
            elif any(keyword in query_lower for keyword in ["account details", "account info", "my account"]):
                return self._handle_account_inquiry(query, context, session_id)
            elif "kyc" in query_lower or "verification" in query_lower:
                return self._handle_kyc_status(query, context, session_id)
            elif "statement" in query_lower:
                return self._handle_statement_request(query, context, session_id)
            else:
                return self._handle_general_account_query(query, context, session_id)
                
        except Exception as e:
            return self.handle_error(e, query)
    
    def _handle_account_creation(
        self,
        query: str,
        context: Dict[str, Any],
        session_id: str
    ) -> Dict[str, Any]:
        """Handle account creation request"""
        
        # Build context for LLM
        context_str = self.format_context_for_llm(context)
        
        system_prompt = f"""{self._get_system_prompt()}

You are helping a customer open a new bank account. 

Process:
1. Collect required information: full name, email, phone, date of birth, address
2. Determine account type (savings, checking, business)
3. Explain KYC requirements
4. Guide through account opening

If information is missing, ask for it politely.
If all information is provided, confirm and proceed with account creation.
"""
        
        prompt = f"""{context_str}

Current Query: {query}

Respond with what information you need or confirm account creation if all details are provided.
Format your response as a helpful banking assistant."""
        
        response = self.generate_response(prompt, system_prompt, temperature=0.7)
        
        # Check if we have enough information to create account
        if self._has_complete_account_info(context):
            # Create account
            account_data = self._create_account(context)
            
            if account_data:
                self.add_to_memory(
                    session_id=session_id,
                    message=f"Account created: {account_data['account_number']}",
                    metadata={"action": "account_created", "account_id": str(account_data['account_id'])}
                )
                
                return self.create_response(
                    answer=f"{response}\n\n✅ Great news! Your account has been created successfully.\n\n"
                           f"Account Number: {account_data['account_number']}\n"
                           f"Account Type: {account_data['account_type']}\n"
                           f"Status: Active\n\n"
                           f"Next steps:\n"
                           f"1. Complete KYC verification by uploading required documents\n"
                           f"2. Set up your online banking credentials\n"
                           f"3. Make your first deposit",
                    success=True,
                    data=account_data,
                    next_steps=[
                        "Complete KYC verification",
                        "Upload identity documents",
                        "Set up online banking"
                    ],
                    requires_action=True
                )
        
        return self.create_response(
            answer=response,
            success=True,
            requires_action=True
        )
    
    def _handle_account_inquiry(
        self,
        query: str,
        context: Dict[str, Any],
        session_id: str
    ) -> Dict[str, Any]:
        """Handle account inquiry"""
        
        customer_info = context.get("customer_info")
        
        if not customer_info:
            return self.create_response(
                answer="I'd be happy to help you with your account information. Could you please provide your customer ID or account number?",
                success=True,
                requires_action=True
            )
        
        # Fetch account details from database
        with db_manager.get_session() as db:
            customer = db.query(Customer).filter(
                Customer.customer_id == customer_info.get("customer_id")
            ).first()
            
            if not customer:
                raise ResourceNotFoundError(
                    "I couldn't find your customer information. Please verify your customer ID.",
                    next_steps=["Check customer ID", "Open a new account"]
                )
            
            accounts = customer.accounts
            
            if not accounts:
                return self.create_response(
                    answer=f"Hello {customer.first_name}! You don't have any active accounts yet. Would you like to open a new account?",
                    success=True,
                    next_steps=["Open a new account"]
                )
            
            # Format account information
            account_info = []
            for acc in accounts:
                account_info.append({
                    "account_number": acc.account_number,
                    "account_type": acc.account_type,
                    "balance": float(acc.balance),
                    "currency": acc.currency,
                    "status": acc.status,
                    "opened_at": acc.opened_at.isoformat() if acc.opened_at else None
                })
            
            response = f"Hello {customer.first_name}! Here are your account details:\n\n"
            for i, acc in enumerate(account_info, 1):
                response += f"{i}. {acc['account_type'].title()} Account\n"
                response += f"   Account Number: {acc['account_number']}\n"
                response += f"   Balance: {acc['currency']} {acc['balance']:,.2f}\n"
                response += f"   Status: {acc['status'].title()}\n\n"
            
            response += "How can I assist you with your accounts today?"
            
            return self.create_response(
                answer=response,
                success=True,
                data={"accounts": account_info}
            )
    
    def _handle_kyc_status(
        self,
        query: str,
        context: Dict[str, Any],
        session_id: str
    ) -> Dict[str, Any]:
        """Handle KYC status inquiry"""
        
        customer_info = context.get("customer_info")
        
        if not customer_info:
            return self.create_response(
                answer="To check your KYC status, I'll need your customer ID. Could you please provide it?",
                success=True,
                requires_action=True
            )
        
        with db_manager.get_session() as db:
            customer = db.query(Customer).filter(
                Customer.customer_id == customer_info.get("customer_id")
            ).first()
            
            if not customer:
                raise ResourceNotFoundError("Customer not found.")
            
            kyc_status = customer.kyc_status
            kyc_docs = customer.kyc_documents
            
            if kyc_status == "verified":
                response = f"✅ Your KYC verification is complete and approved!\n\n"
                response += f"Verified on: {customer.kyc_verified_at.strftime('%Y-%m-%d') if customer.kyc_verified_at else 'N/A'}\n"
                response += f"You have full access to all banking services."
            elif kyc_status == "pending":
                response = f"⏳ Your KYC verification is currently pending.\n\n"
                response += f"Documents submitted: {len(kyc_docs)}\n"
                response += f"Required documents: {', '.join(settings.kyc_required_documents)}\n\n"
                response += f"We're reviewing your documents and will update you soon."
            else:
                response = f"❌ Your KYC verification is incomplete.\n\n"
                response += f"Please upload the following documents:\n"
                for doc_type in settings.kyc_required_documents:
                    response += f"- {doc_type.replace('_', ' ').title()}\n"
                response += f"\nWould you like to start the verification process?"
            
            return self.create_response(
                answer=response,
                success=True,
                data={
                    "kyc_status": kyc_status,
                    "documents_submitted": len(kyc_docs),
                    "required_documents": settings.kyc_required_documents
                }
            )

    def _handle_statement_request(
        self,
        query: str,
        context: Dict[str, Any],
        session_id: str
    ) -> Dict[str, Any]:
        """Handle statement generation request"""
        account_number = context.get("account_number")
        
        if not account_number:
            return self.create_response(
                answer="I can generate a statement for you. Please provide your account number.",
                success=True,
                requires_action=True
            )
            
        with db_manager.get_session() as db:
            account = db.query(Account).filter(Account.account_number == account_number).first()
            if not account:
                raise ResourceNotFoundError("Account not found.")
                
            # Get last 30 days transactions for statement
            txns = db.query(Transaction).filter(
                Transaction.account_id == account.id
            ).order_by(Transaction.transaction_date.desc()).limit(50).all()
            
            # Generate text-based statement
            statement = f"📄 **Account Statement**\n"
            statement += f"Date: {datetime.now().strftime('%Y-%m-%d')}\n"
            statement += f"Account: {account.account_number} ({account.account_type.title()})\n"
            statement += f"Balance: {account.currency} {account.balance:,.2f}\n\n"
            statement += "**Recent Activity:**\n"
            
            for t in txns:
                date_str = t.transaction_date.strftime("%Y-%m-%d")
                amount_str = f"{t.amount:,.2f}"
                type_sym = "+" if t.transaction_type == "credit" else "-"
                statement += f"{date_str} | {type_sym}{amount_str} | {t.description}\n"
                
            return self.create_response(
                answer=f"Here is your generated statement:\n\n{statement}",
                success=True,
                data={"statement_text": statement}
            )
    
    def _handle_general_account_query(
        self,
        query: str,
        context: Dict[str, Any],
        session_id: str
    ) -> Dict[str, Any]:
        """Handle general account queries"""
        
        context_str = self.format_context_for_llm(context)
        
        prompt = f"""{context_str}

Current Query: {query}

Provide a helpful response about account-related matters."""
        
        response = self.generate_response(prompt, temperature=0.7)
        
        return self.create_response(answer=response, success=True)
    
    def _has_complete_account_info(self, context: Dict[str, Any]) -> bool:
        """Check if we have complete information to create account"""
        # This is a simplified check - in production, you'd parse the conversation
        # For demo purposes, we'll create accounts with minimal info
        return context.get("ready_to_create", False)
    
    def _create_account(self, context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Create a new account in the database"""
        try:
            with db_manager.get_session() as db:
                # Create customer first (simplified - in production, collect all details)
                customer_id = f"CUST{random.randint(100000, 999999)}"
                
                customer = Customer(
                    customer_id=customer_id,
                    first_name=context.get("first_name", "John"),
                    last_name=context.get("last_name", "Doe"),
                    email=context.get("email", f"{customer_id.lower()}@example.com"),
                    phone=context.get("phone", "+1234567890"),
                    kyc_status="pending",
                    status="active"
                )
                
                db.add(customer)
                db.flush()
                
                # Create account
                account_number = f"{settings.account_number_prefix}{random.randint(1000000000, 9999999999)}"
                
                account = Account(
                    account_number=account_number,
                    customer_id=customer.id,
                    account_type=context.get("account_type", "savings"),
                    currency="USD",
                    balance=0.00,
                    available_balance=0.00,
                    status="active"
                )
                
                db.add(account)
                db.flush()
                
                # Log audit event
                audit_logger.log_account_creation(
                    account_id=str(account.id),
                    customer_id=str(customer.id),
                    agent_name=self.name,
                    details={
                        "account_number": account_number,
                        "account_type": account.account_type,
                        "customer_id": customer_id
                    },
                    db=db
                )
                
                return {
                    "account_id": str(account.id),
                    "account_number": account_number,
                    "account_type": account.account_type,
                    "customer_id": customer_id,
                    "status": "active"
                }
                
        except Exception as e:
            self.logger.error(f"Failed to create account: {e}")
            return None


# Global account agent instance
account_agent = AccountAgent()
