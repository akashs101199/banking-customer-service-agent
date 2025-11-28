"""
Card Agent
Handles credit/debit card applications, activation, blocking, and inquiries
"""
from typing import Dict, Any, Optional
from datetime import datetime, timedelta, date
import random
from sqlalchemy.orm import Session

from agents.base_agent import BaseAgent
from database.models import Card, Account, Customer
from database.connection import db_manager
from security.audit_logger import audit_logger
from security.encryption import encryption_manager
from security.authentication import auth_manager
from config import settings
from agents.exceptions import ResourceNotFoundError, ValidationError


class CardAgent(BaseAgent):
    """Agent for card-related operations"""
    
    def __init__(self):
        super().__init__(
            name="CardAgent",
            description="Handles credit/debit card applications, activation, blocking, and card management"
        )
    
    def process(
        self,
        query: str,
        context: Dict[str, Any],
        session_id: str
    ) -> Dict[str, Any]:
        """Process card-related queries"""
        try:
            if not self.validate_input(query):
                return self.create_response(
                    answer="I didn't quite understand that. Could you please rephrase your request?",
                    success=False
                )
            
            query_lower = query.lower()
            
            if any(keyword in query_lower for keyword in ["apply", "new card", "get card"]):
                return self._handle_card_application(query, context, session_id)
            elif any(keyword in query_lower for keyword in ["activate", "activation"]):
                return self._handle_card_activation(query, context, session_id)
            elif any(keyword in query_lower for keyword in ["block", "freeze", "disable", "lost", "stolen"]):
                return self._handle_card_blocking(query, context, session_id)
            elif any(keyword in query_lower for keyword in ["card details", "card info", "my card"]):
                return self._handle_card_inquiry(query, context, session_id)
            elif any(keyword in query_lower for keyword in ["pin", "change pin", "set pin"]):
                return self._handle_pin_change(query, context, session_id)
            elif any(keyword in query_lower for keyword in ["limit", "spending limit"]):
                return self._handle_limit_change(query, context, session_id)
            else:
                return self._handle_general_card_query(query, context, session_id)
                
        except Exception as e:
            return self.handle_error(e, query)
    
    def _handle_card_application(
        self,
        query: str,
        context: Dict[str, Any],
        session_id: str
    ) -> Dict[str, Any]:
        """Handle card application"""
        
        # Determine card type
        query_lower = query.lower()
        if "credit" in query_lower:
            card_type = "credit"
        elif "debit" in query_lower:
            card_type = "debit"
        else:
            return self.create_response(
                answer="I'd be happy to help you apply for a card! Would you like a credit card or a debit card?",
                success=True,
                requires_action=True
            )
        
        # Check if customer info is available
        customer_id = context.get("customer_id")
        account_number = context.get("account_number")
        
        if not customer_id or not account_number:
            return self.create_response(
                answer=f"To apply for a {card_type} card, I'll need your customer ID and account number. Could you please provide them?",
                success=True,
                requires_action=True
            )
        
        # Process card application
        card_data = self._create_card(
            customer_id=customer_id,
            account_number=account_number,
            card_type=card_type
        )
        
        if card_data:
            response = f"✅ {card_type.title()} Card Application Approved!\n\n"
            response += f"Card Number: {card_data['masked_card_number']}\n"
            response += f"Card Type: {card_type.title()}\n"
            response += f"Status: Pending Activation\n"
            response += f"Expiry Date: {card_data['expiry_date']}\n\n"
            
            if card_type == "credit":
                response += f"Credit Limit: USD {card_data['credit_limit']:,.2f}\n\n"
            
            response += f"Your card will be delivered to your registered address within 5-7 business days.\n"
            response += f"Once you receive it, you can activate it by calling our helpline or through online banking."
            
            self.add_to_memory(
                session_id=session_id,
                message=f"Card application approved: {card_data['card_id']}",
                metadata={"action": "card_application", "card_type": card_type}
            )
            
            return self.create_response(
                answer=response,
                success=True,
                data=card_data,
                next_steps=[
                    "Wait for card delivery (5-7 days)",
                    "Activate card upon receipt",
                    "Set up card PIN"
                ]
            )
        else:
            return self.create_response(
                answer="I apologize, but we couldn't process your card application at this time. Please try again later or contact support.",
                success=False
            )
    
    def _handle_card_activation(
        self,
        query: str,
        context: Dict[str, Any],
        session_id: str
    ) -> Dict[str, Any]:
        """Handle card activation"""
        
        card_number = context.get("card_number")
        
        if not card_number:
            return self.create_response(
                answer="To activate your card, please provide the card number (last 4 digits are sufficient for security).",
                success=True,
                requires_action=True
            )
        
        with db_manager.get_session() as db:
            # Find card (in production, use secure lookup)
            card = db.query(Card).filter(
                Card.card_number.like(f"%{card_number[-4:]}")
            ).first()
            
            if not card:
                raise ResourceNotFoundError(
                    "Card not found. Please verify the card number.",
                    next_steps=["Check card number", "Apply for a new card"]
                )
            
            if card.status == "active":
                return self.create_response(
                    answer="This card is already activated and ready to use!",
                    success=True
                )
            
            # Activate card
            card.status = "active"
            card.activated_at = datetime.utcnow()
            db.flush()
            
            # Log audit event
            audit_logger.log_event(
                event_type="card_activation",
                action="activate_card",
                entity_type="card",
                entity_id=str(card.id),
                agent_name=self.name,
                details={"card_number": encryption_manager.mask_card_number(card.card_number)},
                db=db
            )
            
            response = f"✅ Card Activated Successfully!\n\n"
            response += f"Card Number: {encryption_manager.mask_card_number(card.card_number)}\n"
            response += f"Card Type: {card.card_type.title()}\n"
            response += f"Status: Active\n\n"
            response += f"Your card is now ready to use for transactions.\n"
            response += f"Please set up your PIN for ATM and POS transactions."
            
            return self.create_response(
                answer=response,
                success=True,
                next_steps=["Set up card PIN", "Start using your card"]
            )
    
    def _handle_card_blocking(
        self,
        query: str,
        context: Dict[str, Any],
        session_id: str
    ) -> Dict[str, Any]:
        """Handle card blocking/freezing"""
        
        card_number = context.get("card_number")
        reason = context.get("block_reason", "Customer requested")
        
        if not card_number:
            return self.create_response(
                answer="To block your card, please provide the card number or last 4 digits.",
                success=True,
                requires_action=True
            )
        
        with db_manager.get_session() as db:
            card = db.query(Card).filter(
                Card.card_number.like(f"%{card_number[-4:]}")
            ).first()
            
            if not card:
                raise ResourceNotFoundError("Card not found. Please verify the card number.")
            
            if card.status == "blocked":
                return self.create_response(
                    answer="This card is already blocked.",
                    success=True
                )
            
            # Block card
            card.status = "blocked"
            card.blocked_at = datetime.utcnow()
            card.block_reason = reason
            db.flush()
            
            # Log audit event
            audit_logger.log_event(
                event_type="card_blocking",
                action="block_card",
                entity_type="card",
                entity_id=str(card.id),
                agent_name=self.name,
                details={
                    "card_number": encryption_manager.mask_card_number(card.card_number),
                    "reason": reason
                },
                db=db
            )
            
            response = f"🔒 Card Blocked Successfully\n\n"
            response += f"Card Number: {encryption_manager.mask_card_number(card.card_number)}\n"
            response += f"Status: Blocked\n"
            response += f"Reason: {reason}\n\n"
            response += f"Your card has been blocked and cannot be used for transactions.\n"
            response += f"If you need a replacement card, please let me know."
            
            return self.create_response(
                answer=response,
                success=True,
                next_steps=["Request replacement card if needed"]
            )
    
    def _handle_card_inquiry(
        self,
        query: str,
        context: Dict[str, Any],
        session_id: str
    ) -> Dict[str, Any]:
        """Handle card inquiry"""
        
        customer_id = context.get("customer_id")
        
        if not customer_id:
            return self.create_response(
                answer="To view your card details, please provide your customer ID.",
                success=True,
                requires_action=True
            )
        
        with db_manager.get_session() as db:
            customer = db.query(Customer).filter(
                Customer.customer_id == customer_id
            ).first()
            
            if not customer:
                return self.create_response(
                    answer="Customer not found.",
                    success=False
                )
            
            cards = customer.cards
            
            if not cards:
                return self.create_response(
                    answer="You don't have any cards yet. Would you like to apply for a credit or debit card?",
                    success=True,
                    next_steps=["Apply for credit card", "Apply for debit card"]
                )
            
            response = f"💳 Your Cards\n\n"
            card_list = []
            
            for i, card in enumerate(cards, 1):
                card_info = {
                    "card_number": encryption_manager.mask_card_number(card.card_number),
                    "card_type": card.card_type,
                    "status": card.status,
                    "expiry_date": card.expiry_date.strftime("%m/%Y") if card.expiry_date else None
                }
                
                if card.card_type == "credit":
                    card_info["credit_limit"] = float(card.credit_limit) if card.credit_limit else 0
                    card_info["available_credit"] = float(card.available_credit) if card.available_credit else 0
                
                card_list.append(card_info)
                
                response += f"{i}. {card.card_type.title()} Card\n"
                response += f"   Number: {encryption_manager.mask_card_number(card.card_number)}\n"
                response += f"   Status: {card.status.title()}\n"
                response += f"   Expiry: {card.expiry_date.strftime('%m/%Y') if card.expiry_date else 'N/A'}\n"
                
                if card.card_type == "credit":
                    response += f"   Credit Limit: USD {card.credit_limit:,.2f}\n"
                    response += f"   Available: USD {card.available_credit:,.2f}\n"
                
                response += "\n"
            
            response += "How can I help you with your cards today?"
            
            return self.create_response(
                answer=response,
                success=True,
                data={"cards": card_list}
            )

    def _handle_pin_change(
        self,
        query: str,
        context: Dict[str, Any],
        session_id: str
    ) -> Dict[str, Any]:
        """Handle PIN change request"""
        card_number = context.get("card_number")
        new_pin = context.get("new_pin") or context.get("pin")
        
        if not card_number or not new_pin:
            return self.create_response(
                answer="To change your PIN, I need your card number and the new 4-digit PIN.",
                success=True,
                requires_action=True
            )
            
        with db_manager.get_session() as db:
            card = db.query(Card).filter(Card.card_number.like(f"%{card_number[-4:]}")).first()
            if not card:
                return self.create_response(answer="Card not found.", success=False)
                
            # In production, we would hash this
            card.pin_hash = new_pin
            db.commit()
            
            return self.create_response(
                answer="✅ Your PIN has been successfully updated.",
                success=True
            )

    def _handle_limit_change(
        self,
        query: str,
        context: Dict[str, Any],
        session_id: str
    ) -> Dict[str, Any]:
        """Handle spending limit change"""
        card_number = context.get("card_number")
        new_limit = context.get("limit") or context.get("amount")
        
        if not card_number or not new_limit:
            return self.create_response(
                answer="To set a spending limit, I need your card number and the new limit amount.",
                success=True,
                requires_action=True
            )
            
        with db_manager.get_session() as db:
            card = db.query(Card).filter(Card.card_number.like(f"%{card_number[-4:]}")).first()
            if not card:
                raise ResourceNotFoundError("Card not found.")
            
            if card.card_type != "credit":
                 raise ValidationError("Limit management is only available for credit cards.")

            card.credit_limit = float(new_limit)
            db.commit()
            
            return self.create_response(
                answer=f"✅ Credit limit updated to ${float(new_limit):,.2f}",
                success=True
            )
    
    def _handle_general_card_query(
        self,
        query: str,
        context: Dict[str, Any],
        session_id: str
    ) -> Dict[str, Any]:
        """Handle general card queries"""
        
        context_str = self.format_context_for_llm(context)
        
        prompt = f"""{context_str}

Current Query: {query}

Provide a helpful response about card-related matters."""
        
        response = self.generate_response(prompt, temperature=0.7)
        
        return self.create_response(answer=response, success=True)
    
    def _create_card(
        self,
        customer_id: str,
        account_number: str,
        card_type: str
    ) -> Optional[Dict[str, Any]]:
        """Create a new card"""
        try:
            with db_manager.get_session() as db:
                # Get customer and account
                customer = db.query(Customer).filter(
                    Customer.customer_id == customer_id
                ).first()
                
                account = db.query(Account).filter(
                    Account.account_number == account_number
                ).first()
                
                if not customer or not account:
                    return None
                
                # Generate card number
                card_number = f"{settings.card_number_prefix}{random.randint(100000000000, 999999999999)}"
                
                # Generate CVV and encrypt it
                cvv = f"{random.randint(100, 999)}"
                encrypted_cvv = encryption_manager.encrypt_cvv(cvv)
                
                # Set expiry date (3 years from now)
                expiry_date = date.today() + timedelta(days=3*365)
                
                # Create card
                card = Card(
                    card_number=card_number,
                    card_type=card_type,
                    account_id=account.id,
                    customer_id=customer.id,
                    card_holder_name=f"{customer.first_name} {customer.last_name}".upper(),
                    expiry_date=expiry_date,
                    cvv=encrypted_cvv,
                    status="pending"
                )
                
                # Set credit limit for credit cards
                if card_type == "credit":
                    card.credit_limit = 5000.00  # Default credit limit
                    card.available_credit = 5000.00
                
                db.add(card)
                db.flush()
                
                # Log audit event
                audit_logger.log_card_application(
                    card_id=str(card.id),
                    customer_id=str(customer.id),
                    agent_name=self.name,
                    card_type=card_type,
                    status="approved",
                    details={
                        "account_number": account_number,
                        "card_holder": card.card_holder_name
                    },
                    db=db
                )
                
                return {
                    "card_id": str(card.id),
                    "masked_card_number": encryption_manager.mask_card_number(card_number),
                    "card_type": card_type,
                    "expiry_date": expiry_date.strftime("%m/%Y"),
                    "credit_limit": float(card.credit_limit) if card.credit_limit else None,
                    "status": "pending"
                }
                
        except Exception as e:
            self.logger.error(f"Failed to create card: {e}")
            return None


# Global card agent instance
card_agent = CardAgent()
