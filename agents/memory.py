"""
Agent Memory Management using ChromaDB
Maintains conversation context and customer history for agents
"""
import chromadb
from chromadb.config import Settings
from typing import List, Dict, Any, Optional
import logging
from datetime import datetime
import json

from config import settings as app_settings

logger = logging.getLogger(__name__)


class AgentMemory:
    """Memory management for AI agents using ChromaDB"""
    
    def __init__(
        self,
        collection_name: str = None,
        persist_directory: str = None
    ):
        """
        Initialize agent memory
        
        Args:
            collection_name: Name of the ChromaDB collection
            persist_directory: Directory to persist vector database
        """
        self.collection_name = collection_name or app_settings.chroma_collection_name
        self.persist_directory = persist_directory or app_settings.chroma_persist_directory
        
        # Initialize ChromaDB client
        self.client = chromadb.Client(Settings(
            persist_directory=self.persist_directory,
            anonymized_telemetry=False
        ))
        
        # Get or create collection
        self.collection = self.client.get_or_create_collection(
            name=self.collection_name,
            metadata={"description": "Banking AI conversation memory"}
        )
        
        logger.info(f"Agent memory initialized with collection: {self.collection_name}")
    
    def add_message(
        self,
        session_id: str,
        message: str,
        message_type: str,
        agent_name: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Add a message to memory
        
        Args:
            session_id: Conversation session ID
            message: Message content
            message_type: Type of message (user, agent, system)
            agent_name: Name of the agent (if applicable)
            metadata: Additional metadata
            
        Returns:
            Message ID
        """
        try:
            message_id = f"{session_id}_{datetime.utcnow().timestamp()}"
            
            meta = {
                "session_id": session_id,
                "message_type": message_type,
                "timestamp": datetime.utcnow().isoformat(),
                **(metadata or {})
            }
            
            if agent_name:
                meta["agent_name"] = agent_name
            
            self.collection.add(
                documents=[message],
                metadatas=[meta],
                ids=[message_id]
            )
            
            return message_id
            
        except Exception as e:
            logger.error(f"Failed to add message to memory: {e}")
            raise
    
    def get_conversation_history(
        self,
        session_id: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Get conversation history for a session
        
        Args:
            session_id: Conversation session ID
            limit: Maximum number of messages to retrieve
            
        Returns:
            List of messages with metadata
        """
        try:
            results = self.collection.get(
                where={"session_id": session_id},
                limit=limit
            )
            
            if not results or not results.get("documents"):
                return []
            
            messages = []
            for i, doc in enumerate(results["documents"]):
                messages.append({
                    "id": results["ids"][i],
                    "message": doc,
                    "metadata": results["metadatas"][i]
                })
            
            # Sort by timestamp
            messages.sort(key=lambda x: x["metadata"].get("timestamp", ""))
            
            return messages
            
        except Exception as e:
            logger.error(f"Failed to get conversation history: {e}")
            return []
    
    def search_similar(
        self,
        query: str,
        session_id: Optional[str] = None,
        n_results: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Search for similar messages using semantic search
        
        Args:
            query: Search query
            session_id: Optional session ID to filter by
            n_results: Number of results to return
            
        Returns:
            List of similar messages with metadata and distances
        """
        try:
            where_filter = {"session_id": session_id} if session_id else None
            
            results = self.collection.query(
                query_texts=[query],
                n_results=n_results,
                where=where_filter
            )
            
            if not results or not results.get("documents"):
                return []
            
            similar_messages = []
            for i, docs in enumerate(results["documents"][0]):
                similar_messages.append({
                    "id": results["ids"][0][i],
                    "message": docs,
                    "metadata": results["metadatas"][0][i],
                    "distance": results["distances"][0][i] if "distances" in results else None
                })
            
            return similar_messages
            
        except Exception as e:
            logger.error(f"Failed to search similar messages: {e}")
            return []
    
    def get_context(
        self,
        session_id: str,
        current_query: str,
        history_limit: int = 5,
        similar_limit: int = 3
    ) -> Dict[str, Any]:
        """
        Get comprehensive context for agent decision making
        
        Args:
            session_id: Conversation session ID
            current_query: Current user query
            history_limit: Number of recent messages to include
            similar_limit: Number of similar past conversations to include
            
        Returns:
            Context dictionary with history and similar conversations
        """
        try:
            # Get recent conversation history
            history = self.get_conversation_history(session_id, limit=history_limit)
            
            # Search for similar past conversations
            similar = self.search_similar(current_query, n_results=similar_limit)
            
            return {
                "session_id": session_id,
                "recent_history": history,
                "similar_conversations": similar,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to get context: {e}")
            return {
                "session_id": session_id,
                "recent_history": [],
                "similar_conversations": [],
                "timestamp": datetime.utcnow().isoformat()
            }
    
    def clear_session(self, session_id: str):
        """
        Clear all messages for a session
        
        Args:
            session_id: Session ID to clear
        """
        try:
            results = self.collection.get(where={"session_id": session_id})
            if results and results.get("ids"):
                self.collection.delete(ids=results["ids"])
                logger.info(f"Cleared session: {session_id}")
        except Exception as e:
            logger.error(f"Failed to clear session: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get memory statistics
        
        Returns:
            Statistics dictionary
        """
        try:
            count = self.collection.count()
            return {
                "collection_name": self.collection_name,
                "total_messages": count,
                "persist_directory": self.persist_directory
            }
        except Exception as e:
            logger.error(f"Failed to get stats: {e}")
            return {}


# Global agent memory instance
agent_memory = AgentMemory()


def add_to_memory(session_id: str, message: str, message_type: str, **kwargs):
    """Convenience function to add message to memory"""
    return agent_memory.add_message(session_id, message, message_type, **kwargs)


def get_context(session_id: str, query: str) -> Dict[str, Any]:
    """Convenience function to get context"""
    return agent_memory.get_context(session_id, query)
