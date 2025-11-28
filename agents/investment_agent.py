"""
Investment Agent
Handles investment portfolio inquiries, trading, and market data
"""
from typing import Dict, Any, Optional
from decimal import Decimal
import logging
import uuid
from sqlalchemy.orm import Session

from agents.base_agent import BaseAgent
from core_banking.investment_manager import investment_manager
from database.models import Customer, Account
from database.connection import db_manager

logger = logging.getLogger(__name__)


class InvestmentAgent(BaseAgent):
    """
    AI agent specialized in investment management
    Handles portfolio inquiries, trading, and market analysis
    """
    
    def __init__(self):
        super().__init__(
            name="InvestmentAgent",
            description="Handles investment portfolio inquiries, trading, and market data"
        )
    
    def process(
        self,
        query: str,
        context: Dict[str, Any],
        session_id: str
    ) -> Dict[str, Any]:
        """Process investment-related queries"""
        
        # Extract intent if available, otherwise default to general
        intent = context.get("intent", "")
        
        try:
            if "portfolio" in query.lower() or "holdings" in query.lower():
                return self._handle_portfolio_inquiry(query, context, session_id)
            elif any(word in query.lower() for word in ["buy", "sell", "trade", "invest"]):
                return self._handle_trading(query, context, session_id)
            elif "market" in query.lower() or "price" in query.lower():
                return self._handle_market_data(query, context, session_id)
            else:
                return self._handle_general_investment_query(query, context, session_id)
                
        except Exception as e:
            return self.handle_error(e, query)
    
    def _handle_portfolio_inquiry(
        self,
        query: str,
        context: Dict[str, Any],
        session_id: str
    ) -> Dict[str, Any]:
        """Handle portfolio inquiry"""
        
        customer_info = context.get("customer_info")
        if not customer_info:
            return self.create_response(
                answer="I need your customer information to access your portfolio.",
                success=False,
                requires_action=True
            )
            
        try:
            with db_manager.get_session() as db:
                customer_id = uuid.UUID(customer_info.get("customer_id"))
                
                # Get portfolio
                portfolio = investment_manager.get_portfolio(db, customer_id)
                
                if not portfolio["holdings"]:
                    return self.create_response(
                        answer="You don't have any active investments yet. Would you like to start investing?",
                        success=True,
                        next_steps=["Start investing", "View investment options"]
                    )
                
                # Format response
                response = f"📊 **Your Investment Portfolio**\n\n"
                response += f"**Total Value:** ${portfolio['total_market_value']:,.2f}\n"
                response += f"**Total Return:** {portfolio['total_return_pct']:.2f}% (${portfolio['total_gain_loss']:,.2f})\n\n"
                
                response += "**Holdings:**\n"
                for holding in portfolio["holdings"]:
                    symbol = holding['symbol']
                    qty = holding['quantity']
                    price = holding['current_price']
                    value = holding['market_value']
                    gain_pct = holding['gain_loss_pct']
                    
                    emoji = "🟢" if gain_pct >= 0 else "🔴"
                    
                    response += f"{emoji} **{symbol}**: {qty} shares @ ${price:,.2f} = ${value:,.2f} ({gain_pct:+.2f}%)\n"
                
                return self.create_response(
                    answer=response,
                    success=True,
                    data=portfolio
                )
                
        except Exception as e:
            return self.handle_error(e, query)

    def _handle_trading(
        self,
        query: str,
        context: Dict[str, Any],
        session_id: str
    ) -> Dict[str, Any]:
        """Handle trading requests"""
        
        # Extract entities
        entities = context.get("entities", {})
        symbol = entities.get("symbol") or context.get("symbol")
        action = entities.get("action") or ("buy" if "buy" in query.lower() else "sell" if "sell" in query.lower() else None)
        quantity = entities.get("quantity") or context.get("quantity")
        
        # If missing info, ask for it
        if not all([symbol, action, quantity]):
            # Try to extract from query using simple rules if not in entities
            # (In a real system, the intent classifier would do this better)
            return self.create_response(
                answer="I can help you trade. Please specify what you want to buy or sell, the symbol, and the quantity. (e.g., 'Buy 10 shares of AAPL')",
                success=False,
                requires_action=True
            )
            
        try:
            with db_manager.get_session() as db:
                customer_info = context.get("customer_info")
                if not customer_info:
                    return self.create_response(
                        answer="Please log in to trade.",
                        success=False
                    )
                
                customer_id = uuid.UUID(customer_info.get("customer_id"))
                
                # Mock price fetch
                current_price = Decimal("150.00") # Placeholder
                
                # Execute trade
                trade = investment_manager.place_order(
                    db=db,
                    customer_id=customer_id,
                    trade_type=action,
                    symbol=symbol.upper(),
                    quantity=Decimal(str(quantity)),
                    price=current_price,
                    investment_type="stock" # Default
                )
                
                response = f"✅ **Order Placed Successfully**\n\n"
                response += f"**Order ID:** {trade.trade_id}\n"
                response += f"**Action:** {action.upper()} {symbol.upper()}\n"
                response += f"**Quantity:** {quantity}\n"
                response += f"**Price:** ${current_price:,.2f}\n"
                response += f"**Total:** ${trade.total_amount:,.2f}\n"
                
                return self.create_response(
                    answer=response,
                    success=True,
                    data={"trade_id": trade.trade_id}
                )
                
        except Exception as e:
            return self.handle_error(e, query)

    def _handle_market_data(
        self,
        query: str,
        context: Dict[str, Any],
        session_id: str
    ) -> Dict[str, Any]:
        """Handle market data inquiries"""
        # Placeholder for market data
        return self.create_response(
            answer="Market data is currently simulated. AAPL is trading at $150.00.",
            success=True
        )

    def _handle_general_investment_query(
        self,
        query: str,
        context: Dict[str, Any],
        session_id: str
    ) -> Dict[str, Any]:
        """Handle general investment queries"""
        
        context_str = self.format_context_for_llm(context)
        
        prompt = f"""{context_str}

Current Query: {query}

Provide a helpful response about investments, trading, or portfolio management."""
        
        response = self.generate_response(prompt, temperature=0.7)
        
        return self.create_response(answer=response, success=True)


# Global instance
investment_agent = InvestmentAgent()
