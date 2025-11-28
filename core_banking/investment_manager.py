"""
Investment Manager
Portfolio management, trade execution, and market data integration
"""
from typing import Dict, Any, Optional, List
from decimal import Decimal
from datetime import datetime, date
import logging
import uuid
from sqlalchemy.orm import Session

from database.models import Investment, Trade, Customer, Account

logger = logging.getLogger(__name__)


class InvestmentManager:
    """
    Investment account and portfolio management system
    Handles securities trading, portfolio tracking, and performance analytics
    """
    
    # Supported investment types
    INVESTMENT_TYPES = {
        "stock": "Individual Stocks",
        "etf": "Exchange-Traded Funds",
        "mutual_fund": "Mutual Funds",
        "bond": "Bonds",
        "crypto": "Cryptocurrency"
    }
    
    # Commission structure
    COMMISSION_RATES = {
        "stock": Decimal("0.00"),  # Commission-free
        "etf": Decimal("0.00"),
        "mutual_fund": Decimal("0.00"),
        "bond": Decimal("10.00"),  # Flat $10
        "crypto": Decimal("0.01")  # 1%
    }
    
    def __init__(self):
        self.logger = logging.getLogger("investment_manager")
    
    def open_investment_account(
        self,
        db: Session,
        customer_id: uuid.UUID,
        account_id: uuid.UUID,
        investment_type: str = "stock"
    ) -> Investment:
        """
        Open a new investment account/position
        """
        if investment_type not in self.INVESTMENT_TYPES:
            raise ValueError(f"Invalid investment type: {investment_type}")
        
        investment_id = f"INV{uuid.uuid4().hex[:10].upper()}"
        
        investment = Investment(
            investment_id=investment_id,
            customer_id=customer_id,
            account_id=account_id,
            investment_type=investment_type,
            quantity=Decimal("0.00"),
            status="active",
            opened_at=datetime.utcnow()
        )
        
        db.add(investment)
        db.commit()
        
        self.logger.info(
            f"Investment account opened: {investment_id}, Type: {investment_type}"
        )
        
        return investment
    
    def place_order(
        self,
        db: Session,
        customer_id: uuid.UUID,
        trade_type: str,  # buy or sell
        symbol: str,
        quantity: Decimal,
        price: Decimal,
        investment_type: str = "stock"
    ) -> Trade:
        """
        Place a securities trade order
        
        Args:
            db: Database session
            customer_id: Customer UUID
            trade_type: 'buy' or 'sell'
            symbol: Security symbol (e.g., 'AAPL', 'BTC')
            quantity: Number of shares/units
            price: Per-unit price
            investment_type: Type of investment
            
        Returns:
            Trade object
        """
        if trade_type not in ["buy", "sell"]:
            raise ValueError("Trade type must be 'buy' or 'sell'")
        
        # Find or create investment position
        investment = db.query(Investment).filter(
            Investment.customer_id == customer_id,
            Investment.symbol == symbol,
            Investment.status == "active"
        ).first()
        
        if not investment:
            # Create new investment position
            customer = db.query(Customer).filter(Customer.id == customer_id).first()
            if not customer:
                raise ValueError(f"Customer not found: {customer_id}")
            
            # Get first active account
            account = db.query(Account).filter(
                Account.customer_id == customer_id,
                Account.status == "active"
            ).first()
            
            if not account:
                raise ValueError("Customer has no active account")
            
            investment = self.open_investment_account(
                db, customer_id, account.id, investment_type
            )
            investment.symbol = symbol
            db.commit()
        
        # Calculate trade amount and fees
        total_amount = quantity * price
        commission = self._calculate_commission(investment_type, total_amount)
        fees = Decimal("0.00")  # Regulatory fees
        
        # Create trade order
        trade_id = f"TRD{uuid.uuid4().hex[:12].upper()}"
        trade = Trade(
            trade_id=trade_id,
            investment_id=investment.id,
            trade_type=trade_type,
            symbol=symbol,
            quantity=quantity,
            price=price,
            total_amount=total_amount,
            commission=commission,
            fees=fees,
            status="pending",
            order_date=datetime.utcnow()
        )
        
        db.add(trade)
        db.commit()
        
        self.logger.info(
            f"Trade order placed: {trade_id}, Type: {trade_type}, "
            f"Symbol: {symbol}, Quantity: {quantity}, Price: {price}"
        )
        
        # Execute trade immediately (in production, this would be queued)
        self.execute_trade(db, trade.id)
        
        return trade
    
    def execute_trade(
        self,
        db: Session,
        trade_id: uuid.UUID
    ) -> Trade:
        """
        Execute a pending trade
        Updates investment holdings and average cost
        """
        trade = db.query(Trade).filter(Trade.id == trade_id).first()
        
        if not trade:
            raise ValueError(f"Trade not found: {trade_id}")
        
        if trade.status != "pending":
            raise ValueError(f"Trade not in pending status: {trade.status}")
        
        investment = db.query(Investment).filter(
            Investment.id == trade.investment_id
        ).first()
        
        try:
            if trade.trade_type == "buy":
                # Update holdings for buy
                total_cost = (
                    investment.quantity * investment.average_cost
                    if investment.average_cost
                    else Decimal("0.00")
                )
                new_total_cost = total_cost + trade.total_amount
                new_quantity = investment.quantity + trade.quantity
                
                investment.quantity = new_quantity
                investment.average_cost = new_total_cost / new_quantity if new_quantity > 0 else Decimal("0.00")
                
            elif trade.trade_type == "sell":
                # Update holdings for sell
                if investment.quantity < trade.quantity:
                    raise ValueError(
                        f"Insufficient holdings. Available: {investment.quantity}, "
                        f"Requested: {trade.quantity}"
                    )
                
                investment.quantity -= trade.quantity
                
                # If all sold, close position
                if investment.quantity == 0:
                    investment.status = "closed"
                    investment.closed_at = datetime.utcnow()
            
            # Mark trade as executed
            trade.status = "executed"
            trade.execution_date = datetime.utcnow()
            trade.settlement_date = date.today()  # T+0 for simplicity
            
            # Update investment security name if not set
            if not investment.security_name:
                investment.security_name = trade.symbol  # In production, fetch from market data
            
            db.commit()
            
            self.logger.info(f"Trade executed: {trade.trade_id}")
            return trade
            
        except Exception as e:
            trade.status = "failed"
            db.commit()
            self.logger.error(f"Trade execution failed: {trade.trade_id}, Error: {e}")
            raise
    
    def update_market_prices(
        self,
        db: Session,
        symbol: str,
        current_price: Decimal
    ):
        """
        Update market prices for investments
        In production, this would integrate with market data providers
        """
        investments = db.query(Investment).filter(
            Investment.symbol == symbol,
            Investment.status == "active"
        ).all()
        
        for investment in investments:
            investment.current_price = current_price
            investment.market_value = investment.quantity * current_price
            
            if investment.average_cost:
                cost_basis = investment.quantity * investment.average_cost
                investment.unrealized_gain_loss = investment.market_value - cost_basis
        
        db.commit()
        
        self.logger.info(f"Market prices updated for {symbol}: {current_price}")
    
    def get_portfolio(
        self,
        db: Session,
        customer_id: uuid.UUID
    ) -> Dict[str, Any]:
        """
        Get complete portfolio for a customer
        """
        investments = db.query(Investment).filter(
            Investment.customer_id == customer_id,
            Investment.status == "active"
        ).all()
        
        total_market_value = Decimal("0.00")
        total_cost_basis = Decimal("0.00")
        total_gain_loss = Decimal("0.00")
        
        holdings = []
        for inv in investments:
            if inv.quantity > 0:
                cost_basis = (
                    inv.quantity * inv.average_cost
                    if inv.average_cost
                    else Decimal("0.00")
                )
                market_value = inv.market_value or Decimal("0.00")
                gain_loss = market_value - cost_basis
                
                total_market_value += market_value
                total_cost_basis += cost_basis
                total_gain_loss += gain_loss
                
                holdings.append({
                    "symbol": inv.symbol,
                    "security_name": inv.security_name,
                    "investment_type": inv.investment_type,
                    "quantity": float(inv.quantity),
                    "average_cost": float(inv.average_cost) if inv.average_cost else 0.0,
                    "current_price": float(inv.current_price) if inv.current_price else 0.0,
                    "market_value": float(market_value),
                    "cost_basis": float(cost_basis),
                    "gain_loss": float(gain_loss),
                    "gain_loss_pct": float(gain_loss / cost_basis * 100) if cost_basis > 0 else 0.0
                })
        
        return {
            "total_market_value": float(total_market_value),
            "total_cost_basis": float(total_cost_basis),
            "total_gain_loss": float(total_gain_loss),
            "total_return_pct": float(total_gain_loss / total_cost_basis * 100) if total_cost_basis > 0 else 0.0,
            "holdings": holdings
        }
    
    def get_trade_history(
        self,
        db: Session,
        customer_id: uuid.UUID,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Get trade history for a customer"""
        # Get all investments for customer
        investment_ids = [
            inv.id for inv in db.query(Investment).filter(
                Investment.customer_id == customer_id
            ).all()
        ]
        
        trades = db.query(Trade).filter(
            Trade.investment_id.in_(investment_ids)
        ).order_by(Trade.order_date.desc()).limit(limit).all()
        
        return [
            {
                "trade_id": t.trade_id,
                "trade_type": t.trade_type,
                "symbol": t.symbol,
                "quantity": float(t.quantity),
                "price": float(t.price),
                "total_amount": float(t.total_amount),
                "commission": float(t.commission),
                "status": t.status,
                "order_date": t.order_date.isoformat() if t.order_date else None,
                "execution_date": t.execution_date.isoformat() if t.execution_date else None
            }
            for t in trades
        ]
    
    def _calculate_commission(
        self,
        investment_type: str,
        trade_amount: Decimal
    ) -> Decimal:
        """Calculate commission based on investment type"""
        rate = self.COMMISSION_RATES.get(investment_type, Decimal("0.00"))
        
        # Percentage-based commission
        if investment_type == "crypto":
            return trade_amount * rate
        
        # Flat commission
        return rate


# Global instance
investment_manager = InvestmentManager()
