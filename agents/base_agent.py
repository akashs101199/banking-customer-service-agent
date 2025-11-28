"""
Base Agent Class
Foundation for all specialized banking agents
"""
from typing import Dict, Any, Optional, List
from abc import ABC, abstractmethod
import logging
from datetime import datetime
import uuid

from utils.llm_client import llm_client
from agents.memory import agent_memory
from security.audit_logger import audit_logger
from agents.exceptions import BankingException

logger = logging.getLogger(__name__)


class BaseAgent(ABC):
    """Base class for all banking AI agents"""
    
    def __init__(self, name: str, description: str):
        """
        Initialize base agent
        
        Args:
            name: Agent name
            description: Agent description
        """
        self.name = name
        self.description = description
        self.logger = logging.getLogger(f"agent.{name}")
    
    @abstractmethod
    def process(
        self,
        query: str,
        context: Dict[str, Any],
        session_id: str
    ) -> Dict[str, Any]:
        """
        Process user query
        
        Args:
            query: User query
            context: Conversation context
            session_id: Session ID
            
        Returns:
            Response dictionary with answer and metadata
        """
        pass
    
    def generate_response(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7
    ) -> str:
        """
        Generate response using LLM
        
        Args:
            prompt: User prompt
            system_prompt: System prompt
            temperature: Sampling temperature
            
        Returns:
            Generated response
        """
        try:
            response = llm_client.generate(
                prompt=prompt,
                system_prompt=system_prompt or self._get_system_prompt(),
                temperature=temperature
            )
            return response
        except Exception as e:
            self.logger.error(f"Failed to generate response: {e}")
            return "I apologize, but I'm having trouble processing your request. Please try again."
    
    def _get_system_prompt(self) -> str:
        """
        Get default system prompt for this agent
        
        Returns:
            System prompt string
        """
        return f"""You are {self.name}, a specialized banking AI agent.
Your role: {self.description}

Guidelines:
- Be professional, helpful, and accurate
- Provide clear and concise responses
- Always prioritize security and compliance
- If you're unsure, ask for clarification
- Never make up information
- Follow banking regulations and best practices
"""
    
    def log_decision(
        self,
        decision: str,
        entity_type: str,
        entity_id: str,
        reasoning: str,
        confidence: float,
        details: Optional[Dict[str, Any]] = None,
        db = None
    ):
        """
        Log agent decision for audit trail
        
        Args:
            decision: Decision made
            entity_type: Type of entity
            entity_id: Entity ID
            reasoning: Reasoning for decision
            confidence: Confidence score
            details: Additional details
            db: Database session
        """
        audit_logger.log_agent_decision(
            agent_name=self.name,
            decision=decision,
            entity_type=entity_type,
            entity_id=entity_id,
            reasoning=reasoning,
            confidence=confidence,
            details=details,
            db=db
        )
    
    def add_to_memory(
        self,
        session_id: str,
        message: str,
        message_type: str = "agent",
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Add message to conversation memory
        
        Args:
            session_id: Session ID
            message: Message content
            message_type: Type of message
            metadata: Additional metadata
        """
        agent_memory.add_message(
            session_id=session_id,
            message=message,
            message_type=message_type,
            agent_name=self.name,
            metadata=metadata
        )
    
    def get_conversation_context(
        self,
        session_id: str,
        query: str
    ) -> Dict[str, Any]:
        """
        Get conversation context from memory
        
        Args:
            session_id: Session ID
            query: Current query
            
        Returns:
            Context dictionary
        """
        return agent_memory.get_context(session_id, query)
    
    def format_context_for_llm(self, context: Dict[str, Any]) -> str:
        """
        Format context for LLM prompt
        
        Args:
            context: Context dictionary
            
        Returns:
            Formatted context string
        """
        formatted = "Conversation Context:\n"
        
        # Add recent history
        if context.get("recent_history"):
            formatted += "\nRecent Conversation:\n"
            for msg in context["recent_history"][-5:]:  # Last 5 messages
                msg_type = msg["metadata"].get("message_type", "unknown")
                content = msg["message"]
                formatted += f"- [{msg_type}]: {content}\n"
        
        # Add customer info if available
        if context.get("customer_info"):
            formatted += "\nCustomer Information:\n"
            customer = context["customer_info"]
            formatted += f"- Name: {customer.get('name', 'N/A')}\n"
            formatted += f"- Customer ID: {customer.get('customer_id', 'N/A')}\n"
            formatted += f"- KYC Status: {customer.get('kyc_status', 'N/A')}\n"
        
        return formatted
    
    def validate_input(self, query: str) -> bool:
        """
        Validate user input
        
        Args:
            query: User query
            
        Returns:
            True if valid, False otherwise
        """
        if not query or not query.strip():
            return False
        
        if len(query) > 5000:  # Max length check
            return False
        
        return True
    
    def create_response(
        self,
        answer: str,
        success: bool = True,
        data: Optional[Dict[str, Any]] = None,
        next_steps: Optional[List[str]] = None,
        requires_action: bool = False
    ) -> Dict[str, Any]:
        """
        Create standardized response
        
        Args:
            answer: Response text
            success: Whether operation was successful
            data: Additional data
            next_steps: Suggested next steps
            requires_action: Whether user action is required
            
        Returns:
            Response dictionary
        """
        return {
            "agent": self.name,
            "answer": answer,
            "success": success,
            "data": data or {},
            "next_steps": next_steps or [],
            "requires_action": requires_action,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    def handle_error(self, error: Exception, query: str) -> Dict[str, Any]:
        """
        Handle errors gracefully
        
        Args:
            error: Exception that occurred
            query: User query
            
        Returns:
            Error response
        """
        self.logger.error(f"Error processing query '{query}': {error}")
        
        if isinstance(error, BankingException):
            return self.create_response(
                answer=f"❌ {error.user_message}",
                success=False,
                next_steps=error.next_steps,
                data={"error_type": error.__class__.__name__}
            )
            
        return self.create_response(
            answer="I apologize, but I encountered an unexpected error. Please try again later.",
            success=False,
            data={"error": str(error)}
        )
    
    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}(name='{self.name}')>"
