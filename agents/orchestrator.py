"""
Agentic AI Orchestrator
Main orchestrator that routes requests to specialized agents using LangGraph
"""
from typing import Dict, Any, Optional, List
from typing_extensions import TypedDict
import logging
from datetime import datetime
import uuid

from langgraph.graph import StateGraph, END
from langchain_core.messages import HumanMessage, AIMessage

from agents.intent_classifier import intent_classifier, Intent
from agents.account_agent import account_agent
from agents.transaction_agent import transaction_agent
from agents.card_agent import card_agent
from agents.card_agent import card_agent
from agents.loan_underwriting_agent import loan_underwriting_agent
from agents.investment_agent import investment_agent
from agents.memory import agent_memory
from utils.llm_client import llm_client

logger = logging.getLogger(__name__)


class ConversationState(TypedDict):
    """State for conversation flow"""
    session_id: str
    query: str
    intent: str
    confidence: float
    entities: Dict[str, Any]
    context: Dict[str, Any]
    response: Dict[str, Any]
    messages: List[Dict[str, str]]
    current_agent: Optional[str]


class BankingOrchestrator:
    """Main orchestrator for banking AI agents"""
    
    def __init__(self):
        """Initialize orchestrator"""
        self.name = "BankingOrchestrator"
        self.logger = logging.getLogger(self.name)
        
        # Agent registry
        self.agents = {
            "account": account_agent,
            "transaction": transaction_agent,
            "account": account_agent,
            "transaction": transaction_agent,
            "card": card_agent,
            "loan": loan_underwriting_agent,
            "investment": investment_agent
        }
        
        # Build workflow graph
        self.workflow = self._build_workflow()
    
    def _build_workflow(self) -> StateGraph:
        """Build LangGraph workflow"""
        
        # Define workflow
        workflow = StateGraph(ConversationState)
        
        # Add nodes
        workflow.add_node("classify_intent", self._classify_intent_node)
        workflow.add_node("route_to_agent", self._route_to_agent_node)
        workflow.add_node("generate_response", self._generate_response_node)
        workflow.add_node("save_to_memory", self._save_to_memory_node)
        
        # Define edges
        workflow.set_entry_point("classify_intent")
        workflow.add_edge("classify_intent", "route_to_agent")
        workflow.add_edge("route_to_agent", "generate_response")
        workflow.add_edge("generate_response", "save_to_memory")
        workflow.add_edge("save_to_memory", END)
        
        return workflow.compile()
    
    def _classify_intent_node(self, state: ConversationState) -> ConversationState:
        """Node: Classify user intent"""
        try:
            query = state["query"]
            
            # Classify intent
            classification = intent_classifier.classify(query, use_llm=True)
            
            state["intent"] = classification["intent"].value
            state["confidence"] = classification["confidence"]
            state["entities"] = classification.get("entities", {})
            
            self.logger.info(f"Intent classified: {state['intent']} (confidence: {state['confidence']})")
            
            return state
            
        except Exception as e:
            self.logger.error(f"Intent classification failed: {e}")
            state["intent"] = Intent.GENERAL_INQUIRY.value
            state["confidence"] = 0.5
            return state
    
    def _route_to_agent_node(self, state: ConversationState) -> ConversationState:
        """Node: Route to appropriate agent"""
        try:
            intent = state["intent"]
            
            # Map intent to agent
            agent_mapping = {
                Intent.ACCOUNT_CREATION.value: "account",
                Intent.ACCOUNT_INQUIRY.value: "account",
                Intent.KYC_VERIFICATION.value: "account",
                Intent.TRANSACTION_HISTORY.value: "transaction",
                Intent.TRANSACTION_DETAILS.value: "transaction",
                Intent.FUND_TRANSFER.value: "transaction",
                Intent.BALANCE_INQUIRY.value: "transaction",
                Intent.CARD_APPLICATION.value: "card",
                Intent.CARD_ACTIVATION.value: "card",
                Intent.CARD_BLOCK.value: "card",
                Intent.CARD_INQUIRY.value: "card",
                Intent.CARD_INQUIRY.value: "card",
                Intent.LOAN_INQUIRY.value: "loan",
                Intent.LOAN_APPLICATION.value: "loan",
                Intent.INVESTMENT_INQUIRY.value: "investment",
                Intent.INVESTMENT_TRADING.value: "investment",
                Intent.PORTFOLIO_INQUIRY.value: "investment",
                Intent.BILL_PAYMENT.value: "transaction",
                Intent.ADD_BENEFICIARY.value: "transaction",
                Intent.CHANGE_PIN.value: "card",
                Intent.SET_LIMIT.value: "card",
                Intent.STATEMENT_REQUEST.value: "account",
            }
            
            agent_name = agent_mapping.get(intent, "general")
            state["current_agent"] = agent_name
            
            self.logger.info(f"Routing to agent: {agent_name}")
            
            return state
            
        except Exception as e:
            self.logger.error(f"Routing failed: {e}")
            state["current_agent"] = "general"
            return state
    
    def _generate_response_node(self, state: ConversationState) -> ConversationState:
        """Node: Generate response using selected agent"""
        try:
            agent_name = state["current_agent"]
            query = state["query"]
            context = state["context"]
            session_id = state["session_id"]
            
            # Add entities to context
            context.update(state["entities"])
            
            # Get agent and process query
            if agent_name in self.agents:
                agent = self.agents[agent_name]
                response = agent.process(query, context, session_id)
            else:
                # Handle general queries
                response = self._handle_general_query(query, context, session_id)
            
            state["response"] = response
            
            return state
            
        except Exception as e:
            self.logger.error(f"Response generation failed: {e}")
            state["response"] = {
                "agent": "orchestrator",
                "answer": "I apologize, but I encountered an error. Please try again.",
                "success": False,
                "error": str(e)
            }
            return state
    
    def _save_to_memory_node(self, state: ConversationState) -> ConversationState:
        """Node: Save conversation to memory"""
        try:
            session_id = state["session_id"]
            query = state["query"]
            response = state["response"]
            
            # Save user message
            agent_memory.add_message(
                session_id=session_id,
                message=query,
                message_type="user",
                metadata={
                    "intent": state["intent"],
                    "confidence": state["confidence"]
                }
            )
            
            # Save agent response
            agent_memory.add_message(
                session_id=session_id,
                message=response["answer"],
                message_type="agent",
                agent_name=response.get("agent", "unknown"),
                metadata={
                    "success": response.get("success", False),
                    "intent": state["intent"]
                }
            )
            
            return state
            
        except Exception as e:
            self.logger.error(f"Failed to save to memory: {e}")
            return state
    
    def _handle_general_query(
        self,
        query: str,
        context: Dict[str, Any],
        session_id: str
    ) -> Dict[str, Any]:
        """Handle general queries not routed to specific agents"""
        
        system_prompt = """You are a helpful banking customer service AI assistant.
You can help with:
- Account opening and management
- Transaction history and details
- Fund transfers
- Card applications and management
- General banking inquiries

Provide helpful, professional, and accurate responses."""
        
        # Get conversation history
        history = agent_memory.get_conversation_history(session_id, limit=5)
        
        # Build context
        context_str = "Recent conversation:\n"
        for msg in history:
            msg_type = msg["metadata"].get("message_type", "unknown")
            context_str += f"{msg_type}: {msg['message']}\n"
        
        prompt = f"{context_str}\n\nUser: {query}\n\nAssistant:"
        
        try:
            response = llm_client.generate(prompt, system_prompt=system_prompt)
            
            return {
                "agent": "GeneralAssistant",
                "answer": response,
                "success": True,
                "timestamp": datetime.utcnow().isoformat()
            }
        except Exception as e:
            self.logger.error(f"General query failed: {e}")
            return {
                "agent": "GeneralAssistant",
                "answer": "I'm here to help! You can ask me about accounts, transactions, cards, and other banking services.",
                "success": True,
                "timestamp": datetime.utcnow().isoformat()
            }
    
    def process_query(
        self,
        query: str,
        session_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Process user query through the orchestrator
        
        Args:
            query: User query
            session_id: Optional session ID (generated if not provided)
            context: Optional context dictionary
            
        Returns:
            Response dictionary
        """
        try:
            # Generate session ID if not provided
            if not session_id:
                session_id = str(uuid.uuid4())
            
            # Get conversation context from memory
            memory_context = agent_memory.get_context(session_id, query)
            
            # Merge with provided context
            full_context = {**memory_context, **(context or {})}
            
            # Initialize state
            initial_state: ConversationState = {
                "session_id": session_id,
                "query": query,
                "intent": "",
                "confidence": 0.0,
                "entities": {},
                "context": full_context,
                "response": {},
                "messages": [],
                "current_agent": None
            }
            
            # Run workflow
            final_state = self.workflow.invoke(initial_state)
            
            # Return response with session ID
            response = final_state["response"]
            response["session_id"] = session_id
            response["intent"] = final_state["intent"]
            response["confidence"] = final_state["confidence"]
            
            return response
            
        except Exception as e:
            self.logger.error(f"Orchestrator error: {e}")
            return {
                "agent": "orchestrator",
                "answer": "I apologize, but I encountered an error processing your request. Please try again.",
                "success": False,
                "error": str(e),
                "session_id": session_id or str(uuid.uuid4())
            }
    
    def chat(
        self,
        message: str,
        session_id: Optional[str] = None,
        **context_kwargs
    ) -> str:
        """
        Simple chat interface
        
        Args:
            message: User message
            session_id: Optional session ID
            **context_kwargs: Additional context parameters
            
        Returns:
            Agent response text
        """
        response = self.process_query(message, session_id, context_kwargs)
        return response.get("answer", "I'm sorry, I couldn't process that request.")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get orchestrator statistics"""
        return {
            "name": self.name,
            "agents": list(self.agents.keys()),
            "memory_stats": agent_memory.get_stats()
        }


# Global orchestrator instance
orchestrator = BankingOrchestrator()


def process_query(query: str, session_id: Optional[str] = None, **context) -> Dict[str, Any]:
    """Convenience function to process query"""
    return orchestrator.process_query(query, session_id, context)


def chat(message: str, session_id: Optional[str] = None, **context) -> str:
    """Convenience function for chat"""
    return orchestrator.chat(message, session_id, **context)
