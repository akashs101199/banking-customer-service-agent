"""
Intent Classification for Banking Queries
Classifies user intents to route to appropriate specialized agents
"""
from typing import Dict, Any, Optional, List
from enum import Enum
import re
import logging

from utils.llm_client import llm_client

logger = logging.getLogger(__name__)


class Intent(str, Enum):
    """Banking intent types"""
    ACCOUNT_CREATION = "account_creation"
    ACCOUNT_INQUIRY = "account_inquiry"
    TRANSACTION_HISTORY = "transaction_history"
    TRANSACTION_DETAILS = "transaction_details"
    FUND_TRANSFER = "fund_transfer"
    BALANCE_INQUIRY = "balance_inquiry"
    CARD_APPLICATION = "card_application"
    CARD_ACTIVATION = "card_activation"
    CARD_BLOCK = "card_block"
    CARD_INQUIRY = "card_inquiry"
    LOAN_INQUIRY = "loan_inquiry"
    LOAN_APPLICATION = "loan_application"
    KYC_VERIFICATION = "kyc_verification"
    BILL_PAYMENT = "bill_payment"
    STATEMENT_REQUEST = "statement_request"
    GENERAL_INQUIRY = "general_inquiry"
    COMPLAINT = "complaint"
    INVESTMENT_INQUIRY = "investment_inquiry"
    INVESTMENT_TRADING = "investment_trading"
    PORTFOLIO_INQUIRY = "portfolio_inquiry"
    ADD_BENEFICIARY = "add_beneficiary"
    CHANGE_PIN = "change_pin"
    SET_LIMIT = "set_limit"
    UNKNOWN = "unknown"


class IntentClassifier:
    """Classifies user intents for routing to appropriate agents"""
    
    def __init__(self):
        """Initialize intent classifier"""
        self.intent_keywords = {
            Intent.ACCOUNT_CREATION: [
                "open account", "create account", "new account", "account opening",
                "start account", "register account", "sign up"
            ],
            Intent.ACCOUNT_INQUIRY: [
                "account details", "account information", "my account",
                "account status", "account type"
            ],
            Intent.TRANSACTION_HISTORY: [
                "transaction history", "past transactions", "transaction list",
                "recent transactions", "transaction record", "statement"
            ],
            Intent.TRANSACTION_DETAILS: [
                "transaction details", "transaction info", "about transaction",
                "transaction status", "specific transaction"
            ],
            Intent.FUND_TRANSFER: [
                "transfer money", "send money", "transfer funds", "make transfer",
                "pay someone", "wire transfer", "send payment"
            ],
            Intent.BALANCE_INQUIRY: [
                "check balance", "account balance", "how much", "balance inquiry",
                "current balance", "available balance"
            ],
            Intent.CARD_APPLICATION: [
                "apply card", "new card", "credit card", "debit card",
                "card application", "get card", "request card"
            ],
            Intent.CARD_ACTIVATION: [
                "activate card", "card activation", "enable card", "start card"
            ],
            Intent.CARD_BLOCK: [
                "block card", "freeze card", "disable card", "stop card",
                "card lost", "card stolen", "deactivate card"
            ],
            Intent.CARD_INQUIRY: [
                "card details", "card information", "card status", "my card",
                "card limit", "card balance"
            ],
            Intent.LOAN_INQUIRY: [
                "loan information", "loan details", "loan eligibility",
                "loan options", "loan types", "about loan"
            ],
            Intent.LOAN_APPLICATION: [
                "apply loan", "loan application", "get loan", "request loan",
                "need loan", "borrow money"
            ],
            Intent.KYC_VERIFICATION: [
                "kyc", "verify identity", "document verification", "upload documents",
                "identity verification", "verification status"
            ],
            Intent.BILL_PAYMENT: [
                "pay bill", "bill payment", "utility payment", "make payment"
            ],
            Intent.STATEMENT_REQUEST: [
                "bank statement", "account statement", "download statement",
                "statement request", "transaction statement"
            ],
            Intent.COMPLAINT: [
                "complaint", "issue", "problem", "error", "wrong transaction",
                "dispute", "report"
            ],
            Intent.INVESTMENT_INQUIRY: [
                "investment", "investing", "stock market", "market price", "share price",
                "ticker", "symbol", "quote"
            ],
            Intent.INVESTMENT_TRADING: [
                "buy stock", "sell stock", "trade", "purchase shares", "sell shares",
                "buy shares", "invest in"
            ],
            Intent.PORTFOLIO_INQUIRY: [
                "portfolio", "holdings", "my stocks", "my investments", "investment balance",
                "investment performance"
            ],
            Intent.ADD_BENEFICIARY: [
                "add beneficiary", "new payee", "save contact", "add payee",
                "save beneficiary"
            ],
            Intent.CHANGE_PIN: [
                "change pin", "new pin", "update pin", "reset pin", "set pin"
            ],
            Intent.SET_LIMIT: [
                "set limit", "spending limit", "change limit", "increase limit",
                "decrease limit", "card limit"
            ]
        }
    
    def classify_rule_based(self, query: str) -> Intent:
        """
        Rule-based intent classification using keywords
        
        Args:
            query: User query
            
        Returns:
            Classified intent
        """
        query_lower = query.lower()
        
        # Check each intent's keywords
        for intent, keywords in self.intent_keywords.items():
            for keyword in keywords:
                if keyword in query_lower:
                    return intent
        
        return Intent.GENERAL_INQUIRY
    
    def classify_llm_based(self, query: str) -> Dict[str, Any]:
        """
        LLM-based intent classification with confidence scores
        
        Args:
            query: User query
            
        Returns:
            Dictionary with intent, confidence, and entities
        """
        try:
            system_prompt = """You are an intent classifier for a banking AI system.
Classify the user's query into one of these intents:
- account_creation: Opening new accounts
- account_inquiry: Questions about existing accounts
- transaction_history: Viewing past transactions
- transaction_details: Details about specific transactions
- fund_transfer: Transferring money
- balance_inquiry: Checking account balance
- card_application: Applying for credit/debit cards
- card_activation: Activating a card
- card_block: Blocking/freezing a card
- card_inquiry: Questions about cards
- loan_inquiry: Questions about loans
- loan_application: Applying for a loan
- kyc_verification: KYC/document verification
- bill_payment: Paying bills
- statement_request: Requesting statements
- statement_request: Requesting statements
- complaint: Complaints or issues
- investment_inquiry: General investment/market questions
- investment_trading: Buying/selling stocks or assets
- portfolio_inquiry: Checking investment holdings
- add_beneficiary: Adding a new payee/beneficiary
- change_pin: Changing card PIN
- set_limit: Setting card spending limits
- general_inquiry: General questions

Respond in JSON format with:
{
  "intent": "<intent_name>",
  "confidence": <0.0-1.0>,
  "entities": {
    "amount": <if mentioned>,
    "account_number": <if mentioned>,
    "card_type": <if mentioned>,
    "account_number": <if mentioned>,
    "card_type": <if mentioned>,
    "transaction_id": <if mentioned>,
    "symbol": <if mentioned>,
    "quantity": <if mentioned>,
    "action": <buy/sell if mentioned>
  },
  "reasoning": "<brief explanation>"
}"""
            
            user_prompt = f"User query: {query}\n\nClassify this query:"
            
            response = llm_client.generate(
                prompt=user_prompt,
                system_prompt=system_prompt,
                temperature=0.3
            )
            
            # Parse JSON response
            import json
            # Extract JSON from response
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group())
                return {
                    "intent": Intent(result.get("intent", "general_inquiry")),
                    "confidence": result.get("confidence", 0.5),
                    "entities": result.get("entities", {}),
                    "reasoning": result.get("reasoning", "")
                }
            else:
                # Fallback to rule-based
                return {
                    "intent": self.classify_rule_based(query),
                    "confidence": 0.6,
                    "entities": {},
                    "reasoning": "Rule-based classification"
                }
                
        except Exception as e:
            logger.error(f"LLM classification failed: {e}")
            # Fallback to rule-based
            return {
                "intent": self.classify_rule_based(query),
                "confidence": 0.6,
                "entities": {},
                "reasoning": "Fallback to rule-based"
            }
    
    def classify(self, query: str, use_llm: bool = True) -> Dict[str, Any]:
        """
        Classify user intent
        
        Args:
            query: User query
            use_llm: Whether to use LLM-based classification
            
        Returns:
            Classification result with intent, confidence, and entities
        """
        if use_llm:
            return self.classify_llm_based(query)
        else:
            return {
                "intent": self.classify_rule_based(query),
                "confidence": 0.7,
                "entities": {},
                "reasoning": "Rule-based classification"
            }
    
    def extract_entities(self, query: str) -> Dict[str, Any]:
        """
        Extract entities from query
        
        Args:
            query: User query
            
        Returns:
            Dictionary of extracted entities
        """
        entities = {}
        
        # Extract amount
        amount_pattern = r'\$?(\d+(?:,\d{3})*(?:\.\d{2})?)'
        amount_match = re.search(amount_pattern, query)
        if amount_match:
            entities["amount"] = amount_match.group(1).replace(',', '')
        
        # Extract account number (assuming format: ACC followed by digits)
        account_pattern = r'ACC\d+'
        account_match = re.search(account_pattern, query, re.IGNORECASE)
        if account_match:
            entities["account_number"] = account_match.group()
        
        # Extract card type
        if "credit card" in query.lower():
            entities["card_type"] = "credit"
        elif "debit card" in query.lower():
            entities["card_type"] = "debit"
        
        return entities


# Global intent classifier instance
intent_classifier = IntentClassifier()


def classify_intent(query: str, use_llm: bool = True) -> Dict[str, Any]:
    """Convenience function to classify intent"""
    return intent_classifier.classify(query, use_llm=use_llm)
