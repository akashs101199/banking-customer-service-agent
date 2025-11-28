"""
Transaction Agent
Handles transaction history, details, fund transfers, and balance inquiries
"""
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from decimal import Decimal
import random
from sqlalchemy.orm import Session
from sqlalchemy import desc

from agents.base_agent import BaseAgent
from database.models import Transaction, Account, Customer
from database.models import Transaction, Account, Customer
from database.connection import db_manager
from security.audit_logger import audit_logger
from core_banking.payment_processor import payment_processor
from agents.exceptions import InsufficientFundsError, ResourceNotFoundError, ValidationError


class TransactionAgent(BaseAgent):
    """Agent for transaction-related operations"""
    
    def __init__(self):
        super().__init__(
            name="TransactionAgent",
            description="Handles transaction history, details, fund transfers, and balance inquiries"
        )
    
    def process(
        self,
        query: str,
        context: Dict[str, Any],
        session_id: str
    ) -> Dict[str, Any]:
        """Process transaction-related queries"""
        try:
            if not self.validate_input(query):
                return self.create_response(
                    answer="I didn't quite understand that. Could you please rephrase your request?",
                    success=False
                )
            
            query_lower = query.lower()
            
            if any(keyword in query_lower for keyword in ["balance", "how much"]):
                return self._handle_balance_inquiry(query, context, session_id)
            elif any(keyword in query_lower for keyword in ["history", "transactions", "statement"]):
                return self._handle_transaction_history(query, context, session_id)
            elif any(keyword in query_lower for keyword in ["transfer", "send money", "pay"]):
                if "bill" in query_lower:
                    return self._handle_bill_payment(query, context, session_id)
                elif "beneficiary" in query_lower or "payee" in query_lower:
                    return self._handle_beneficiary_management(query, context, session_id)
                else:
                    return self._handle_fund_transfer(query, context, session_id)
            elif "transaction" in query_lower and any(word in query_lower for word in ["details", "info", "about"]):
                return self._handle_transaction_details(query, context, session_id)
            else:
                return self._handle_general_transaction_query(query, context, session_id)
                
        except Exception as e:
            return self.handle_error(e, query)
    
    def _handle_balance_inquiry(
        self,
        query: str,
        context: Dict[str, Any],
        session_id: str
    ) -> Dict[str, Any]:
        """Handle balance inquiry"""
        
        account_number = context.get("account_number")
        
        if not account_number:
            return self.create_response(
                answer="I'd be happy to check your balance. Could you please provide your account number?",
                success=True,
                requires_action=True
            )
        
        with db_manager.get_session() as db:
            account = db.query(Account).filter(
                Account.account_number == account_number
            ).first()
            
            if not account:
                return self.create_response(
                    answer="I couldn't find an account with that number. Please verify and try again.",
                    success=False
                )
            
            balance_info = {
                "account_number": account.account_number,
                "account_type": account.account_type,
                "balance": float(account.balance),
                "available_balance": float(account.available_balance),
                "currency": account.currency
            }
            
            response = f"💰 Account Balance Information\n\n"
            response += f"Account: {account.account_number} ({account.account_type.title()})\n"
            response += f"Current Balance: {account.currency} {account.balance:,.2f}\n"
            response += f"Available Balance: {account.currency} {account.available_balance:,.2f}\n\n"
            response += f"Is there anything else you'd like to know about your account?"
            
            return self.create_response(
                answer=response,
                success=True,
                data=balance_info
            )
    
    def _handle_transaction_history(
        self,
        query: str,
        context: Dict[str, Any],
        session_id: str
    ) -> Dict[str, Any]:
        """Handle transaction history request"""
        
        account_number = context.get("account_number")
        
        if not account_number:
            return self.create_response(
                answer="To view your transaction history, please provide your account number.",
                success=True,
                requires_action=True
            )
        
        with db_manager.get_session() as db:
            account = db.query(Account).filter(
                Account.account_number == account_number
            ).first()
            
            if not account:
                return self.create_response(
                    answer="Account not found. Please verify your account number.",
                    success=False
                )
            
            # Get recent transactions (last 30 days)
            thirty_days_ago = datetime.utcnow() - timedelta(days=30)
            transactions = db.query(Transaction).filter(
                Transaction.account_id == account.id,
                Transaction.transaction_date >= thirty_days_ago
            ).order_by(desc(Transaction.transaction_date)).limit(20).all()
            
            if not transactions:
                return self.create_response(
                    answer=f"No transactions found for account {account.account_number} in the last 30 days.",
                    success=True,
                    data={"transactions": []}
                )
            
            # Format transaction history
            transaction_list = []
            response = f"📊 Transaction History - Last 30 Days\n"
            response += f"Account: {account.account_number}\n\n"
            
            for txn in transactions:
                transaction_list.append({
                    "transaction_id": txn.transaction_id,
                    "date": txn.transaction_date.isoformat(),
                    "type": txn.transaction_type,
                    "amount": float(txn.amount),
                    "description": txn.description,
                    "balance_after": float(txn.balance_after) if txn.balance_after else None
                })
                
                # Format for display
                date_str = txn.transaction_date.strftime("%Y-%m-%d %H:%M")
                amount_str = f"{txn.currency} {txn.amount:,.2f}"
                symbol = "+" if txn.transaction_type == "credit" else "-"
                
                response += f"{date_str} | {symbol}{amount_str} | {txn.description or 'N/A'}\n"
            
            response += f"\nTotal transactions: {len(transactions)}\n"
            response += f"Would you like details about any specific transaction?"
            
            return self.create_response(
                answer=response,
                success=True,
                data={"transactions": transaction_list}
            )
    
    def _handle_fund_transfer(
        self,
        query: str,
        context: Dict[str, Any],
        session_id: str
    ) -> Dict[str, Any]:
        """Handle fund transfer request"""
        
        # Extract transfer details from context
        from_account = context.get("from_account")
        to_account = context.get("to_account")
        amount = context.get("amount")
        
        # Check if we have all required information
        missing_info = []
        if not from_account:
            missing_info.append("source account number")
        if not to_account:
            missing_info.append("destination account number")
        if not amount:
            missing_info.append("transfer amount")
        
        if missing_info:
            return self.create_response(
                answer=f"To process the transfer, I need the following information:\n" +
                       "\n".join(f"- {info}" for info in missing_info) +
                       "\n\nPlease provide these details.",
                success=True,
                requires_action=True
            )
        
        # Process transfer
        transfer_result = self._process_transfer(
            from_account=from_account,
            to_account=to_account,
            amount=float(amount),
            description=context.get("description", "Fund transfer")
        )
        
        if transfer_result["success"]:
            response = f"✅ Transfer Successful!\n\n"
            response += f"From: {from_account}\n"
            response += f"To: {to_account}\n"
            response += f"Amount: USD {float(amount):,.2f}\n"
            response += f"Transaction ID: {transfer_result['transaction_id']}\n"
            response += f"New Balance: USD {transfer_result['new_balance']:,.2f}\n\n"
            response += f"The funds have been transferred successfully."
            
            return self.create_response(
                answer=response,
                success=True,
                data=transfer_result
            )
        else:
            return self.create_response(
                answer=f"❌ Transfer Failed: {transfer_result.get('error', 'Unknown error')}",
                success=False,
                data=transfer_result
            )
    
    def _handle_transaction_details(
        self,
        query: str,
        context: Dict[str, Any],
        session_id: str
    ) -> Dict[str, Any]:
        """Handle transaction details inquiry"""
        
        transaction_id = context.get("transaction_id")
        
        if not transaction_id:
            return self.create_response(
                answer="Please provide the transaction ID to view details.",
                success=True,
                requires_action=True
            )
        
        with db_manager.get_session() as db:
            transaction = db.query(Transaction).filter(
                Transaction.transaction_id == transaction_id
            ).first()
            
            if not transaction:
                return self.create_response(
                    answer=f"Transaction {transaction_id} not found.",
                    success=False
                )
            
            response = f"📝 Transaction Details\n\n"
            response += f"Transaction ID: {transaction.transaction_id}\n"
            response += f"Date: {transaction.transaction_date.strftime('%Y-%m-%d %H:%M:%S')}\n"
            response += f"Type: {transaction.transaction_type.title()}\n"
            response += f"Amount: {transaction.currency} {transaction.amount:,.2f}\n"
            response += f"Description: {transaction.description or 'N/A'}\n"
            response += f"Status: {transaction.status.title()}\n"
            
            if transaction.counterparty_name:
                response += f"Counterparty: {transaction.counterparty_name}\n"
            
            if transaction.reference_number:
                response += f"Reference: {transaction.reference_number}\n"
            
            return self.create_response(
                answer=response,
                success=True,
                data={
                    "transaction_id": transaction.transaction_id,
                    "date": transaction.transaction_date.isoformat(),
                    "type": transaction.transaction_type,
                    "amount": float(transaction.amount),
                    "status": transaction.status
                }
            )

    def _handle_bill_payment(
        self,
        query: str,
        context: Dict[str, Any],
        session_id: str
    ) -> Dict[str, Any]:
        """Handle bill payment"""
        biller = context.get("biller") or context.get("entities", {}).get("biller")
        amount = context.get("amount") or context.get("entities", {}).get("amount")
        account_number = context.get("account_number")
        
        if not all([biller, amount, account_number]):
            return self.create_response(
                answer="To pay a bill, I need the biller name, amount, and your account number.",
                success=True,
                requires_action=True
            )
            
        with db_manager.get_session() as db:
            account = db.query(Account).filter(Account.account_number == account_number).first()
            if not account:
                raise ResourceNotFoundError("Account not found.")
            
            if account.available_balance < Decimal(str(amount)):
                 raise InsufficientFundsError(
                    f"Insufficient funds for bill payment. Available: {account.currency} {account.available_balance:,.2f}",
                    next_steps=["Check balance", "Deposit funds"]
                )

            result = payment_processor.pay_bill(
                db=db,
                account_id=account.id,
                biller_name=biller,
                amount=Decimal(str(amount))
            )
            
            return self.create_response(
                answer=f"✅ Paid {result['currency'] if 'currency' in result else '$'}{result['amount']} to {result['biller']}.",
                success=True,
                data=result
            )

    def _handle_beneficiary_management(
        self,
        query: str,
        context: Dict[str, Any],
        session_id: str
    ) -> Dict[str, Any]:
        """Handle beneficiary management"""
        customer_info = context.get("customer_info")
        if not customer_info:
            return self.create_response(answer="Please log in to manage beneficiaries.", success=False)
            
        customer_id = uuid.UUID(customer_info.get("customer_id"))
        
        with db_manager.get_session() as db:
            if "add" in query.lower():
                # Simplified add flow - in real app would ask for details step-by-step
                name = context.get("name")
                acc_num = context.get("account_number")
                if not (name and acc_num):
                    return self.create_response(
                        answer="To add a beneficiary, I need their name and account number.",
                        success=False
                    )
                
                result = payment_processor.add_beneficiary(
                    db=db,
                    customer_id=customer_id,
                    name=name,
                    account_number=acc_num,
                    bank_name="External Bank"
                )
                return self.create_response(
                    answer=f"✅ Added beneficiary: {result['name']}",
                    success=True
                )
            else:
                # List beneficiaries
                beneficiaries = payment_processor.get_beneficiaries(db, customer_id)
                if not beneficiaries:
                    return self.create_response(answer="You have no saved beneficiaries.", success=True)
                
                response = "👥 **Your Beneficiaries**\n\n"
                for b in beneficiaries:
                    response += f"• {b['name']} ({b['account_number']})\n"
                
                return self.create_response(answer=response, success=True)
    
    def _handle_general_transaction_query(
        self,
        query: str,
        context: Dict[str, Any],
        session_id: str
    ) -> Dict[str, Any]:
        """Handle general transaction queries"""
        
        context_str = self.format_context_for_llm(context)
        
        prompt = f"""{context_str}

Current Query: {query}

Provide a helpful response about transaction-related matters."""
        
        response = self.generate_response(prompt, temperature=0.7)
        
        return self.create_response(answer=response, success=True)
    
    def _process_transfer(
        self,
        from_account: str,
        to_account: str,
        amount: float,
        description: str
    ) -> Dict[str, Any]:
        """Process fund transfer between accounts"""
        try:
            with db_manager.get_session() as db:
                # Get source account
                source = db.query(Account).filter(
                    Account.account_number == from_account
                ).first()
                
                if not source:
                    return {"success": False, "error": "Source account not found"}
                
                # Check balance
                if source.available_balance < Decimal(str(amount)):
                    return {"success": False, "error": "Insufficient funds"}
                
                # Get destination account
                dest = db.query(Account).filter(
                    Account.account_number == to_account
                ).first()
                
                if not dest:
                    return {"success": False, "error": "Destination account not found"}
                
                # Create debit transaction
                debit_txn_id = f"TXN{random.randint(1000000000, 9999999999)}"
                source.balance -= Decimal(str(amount))
                source.available_balance -= Decimal(str(amount))
                
                debit_txn = Transaction(
                    transaction_id=debit_txn_id,
                    account_id=source.id,
                    transaction_type="debit",
                    amount=Decimal(str(amount)),
                    currency="USD",
                    balance_after=source.balance,
                    description=description,
                    counterparty_account=to_account,
                    status="completed"
                )
                
                # Create credit transaction
                credit_txn_id = f"TXN{random.randint(1000000000, 9999999999)}"
                dest.balance += Decimal(str(amount))
                dest.available_balance += Decimal(str(amount))
                
                credit_txn = Transaction(
                    transaction_id=credit_txn_id,
                    account_id=dest.id,
                    transaction_type="credit",
                    amount=Decimal(str(amount)),
                    currency="USD",
                    balance_after=dest.balance,
                    description=description,
                    counterparty_account=from_account,
                    status="completed"
                )
                
                db.add(debit_txn)
                db.add(credit_txn)
                db.flush()
                
                # Log audit event
                audit_logger.log_transaction(
                    transaction_id=debit_txn_id,
                    account_id=str(source.id),
                    agent_name=self.name,
                    transaction_type="transfer",
                    amount=amount,
                    details={
                        "from_account": from_account,
                        "to_account": to_account,
                        "description": description
                    },
                    db=db
                )
                
                return {
                    "success": True,
                    "transaction_id": debit_txn_id,
                    "new_balance": float(source.balance),
                    "amount": amount
                }
                
        except Exception as e:
            self.logger.error(f"Transfer failed: {e}")
            return {"success": False, "error": str(e)}


# Global transaction agent instance
transaction_agent = TransactionAgent()
