"""
LLM Client for Ollama
Wrapper for interacting with local LLM via Ollama
"""
import httpx
from typing import Optional, Dict, Any, List
import logging
import json
from tenacity import retry, stop_after_attempt, wait_exponential

from config import settings

logger = logging.getLogger(__name__)


class OllamaClient:
    """Client for interacting with Ollama LLM"""
    
    def __init__(
        self,
        base_url: str = None,
        model: str = None,
        temperature: float = None,
        max_tokens: int = None
    ):
        """
        Initialize Ollama client
        
        Args:
            base_url: Ollama API base URL
            model: Model name to use
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
        """
        self.base_url = base_url or settings.ollama_base_url
        self.model = model or settings.ollama_model
        self.temperature = temperature or settings.ollama_temperature
        self.max_tokens = max_tokens or settings.ollama_max_tokens
        self.client = httpx.Client(timeout=60.0)
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        stream: bool = False
    ) -> str:
        """
        Generate text completion
        
        Args:
            prompt: User prompt
            system_prompt: Optional system prompt
            temperature: Override default temperature
            max_tokens: Override default max tokens
            stream: Whether to stream response
            
        Returns:
            Generated text
        """
        try:
            url = f"{self.base_url}/api/generate"
            
            payload = {
                "model": self.model,
                "prompt": prompt,
                "stream": stream,
                "options": {
                    "temperature": temperature or self.temperature,
                    "num_predict": max_tokens or self.max_tokens
                }
            }
            
            if system_prompt:
                payload["system"] = system_prompt
            
            response = self.client.post(url, json=payload)
            response.raise_for_status()
            
            if stream:
                # Handle streaming response
                full_response = ""
                for line in response.iter_lines():
                    if line:
                        data = json.loads(line)
                        if "response" in data:
                            full_response += data["response"]
                return full_response
            else:
                result = response.json()
                return result.get("response", "")
                
        except Exception as e:
            logger.error(f"Ollama generation error: {e}")
            raise
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None
    ) -> str:
        """
        Chat completion with message history
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            temperature: Override default temperature
            max_tokens: Override default max tokens
            
        Returns:
            Assistant's response
        """
        try:
            url = f"{self.base_url}/api/chat"
            
            payload = {
                "model": self.model,
                "messages": messages,
                "stream": False,
                "options": {
                    "temperature": temperature or self.temperature,
                    "num_predict": max_tokens or self.max_tokens
                }
            }
            
            response = self.client.post(url, json=payload)
            response.raise_for_status()
            
            result = response.json()
            return result.get("message", {}).get("content", "")
            
        except Exception as e:
            logger.error(f"Ollama chat error: {e}")
            raise
    
    def embed(self, text: str) -> List[float]:
        """
        Generate embeddings for text
        
        Args:
            text: Text to embed
            
        Returns:
            Embedding vector
        """
        try:
            url = f"{self.base_url}/api/embeddings"
            
            payload = {
                "model": self.model,
                "prompt": text
            }
            
            response = self.client.post(url, json=payload)
            response.raise_for_status()
            
            result = response.json()
            return result.get("embedding", [])
            
        except Exception as e:
            logger.error(f"Ollama embedding error: {e}")
            raise
    
    def is_available(self) -> bool:
        """
        Check if Ollama service is available
        
        Returns:
            True if available, False otherwise
        """
        try:
            response = self.client.get(f"{self.base_url}/api/tags")
            return response.status_code == 200
        except:
            return False
    
    def list_models(self) -> List[str]:
        """
        List available models
        
        Returns:
            List of model names
        """
        try:
            response = self.client.get(f"{self.base_url}/api/tags")
            response.raise_for_status()
            
            result = response.json()
            return [model["name"] for model in result.get("models", [])]
        except Exception as e:
            logger.error(f"Failed to list models: {e}")
            return []
    
    def __del__(self):
        """Cleanup client"""
        if hasattr(self, 'client'):
            self.client.close()


# Global Ollama client instance
llm_client = OllamaClient()


def generate_text(prompt: str, system_prompt: Optional[str] = None) -> str:
    """Convenience function to generate text"""
    return llm_client.generate(prompt, system_prompt=system_prompt)


def chat_completion(messages: List[Dict[str, str]]) -> str:
    """Convenience function for chat completion"""
    return llm_client.chat(messages)
