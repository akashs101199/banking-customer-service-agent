"""
FastAPI Main Application
REST API for Banking Customer Service AI
"""
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
import logging
from datetime import datetime

from config import settings
from agents.orchestrator import orchestrator
from database.connection import init_database
from utils.llm_client import llm_client

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Agentic AI for Banking Customer Service - Fully Autonomous Banking Operations",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=settings.cors_allow_credentials,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Pydantic models
class ChatRequest(BaseModel):
    """Chat request model"""
    message: str = Field(..., description="User message", min_length=1, max_length=5000)
    session_id: Optional[str] = Field(None, description="Session ID for conversation continuity")
    context: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional context")


class ChatResponse(BaseModel):
    """Chat response model"""
    answer: str = Field(..., description="AI agent response")
    agent: str = Field(..., description="Agent that handled the request")
    session_id: str = Field(..., description="Session ID")
    intent: str = Field(..., description="Classified intent")
    confidence: float = Field(..., description="Intent classification confidence")
    success: bool = Field(..., description="Whether operation was successful")
    data: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional data")
    next_steps: Optional[List[str]] = Field(default_factory=list, description="Suggested next steps")
    timestamp: str = Field(..., description="Response timestamp")


class HealthResponse(BaseModel):
    """Health check response"""
    status: str
    timestamp: str
    version: str
    services: Dict[str, bool]


# Startup and shutdown events
@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    logger.info(f"Starting {settings.app_name} v{settings.app_version}")
    
    try:
        # Initialize database
        init_database()
        logger.info("Database initialized")
        
        # Check Ollama connection
        if llm_client.is_available():
            logger.info("Ollama LLM service connected")
        else:
            logger.warning("Ollama LLM service not available - using fallback")
        
        logger.info("Application startup complete")
        
    except Exception as e:
        logger.error(f"Startup error: {e}")
        raise


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("Shutting down application")


# API Routes
@app.get("/", tags=["General"])
async def root():
    """Root endpoint"""
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "description": "Banking Customer Service Agentic AI",
        "docs": "/docs",
        "health": "/health"
    }


@app.get("/health", response_model=HealthResponse, tags=["General"])
async def health_check():
    """Health check endpoint"""
    
    # Check services
    services = {
        "database": True,  # Simplified - add actual DB check
        "llm": llm_client.is_available(),
        "memory": True,  # Simplified - add actual memory check
    }
    
    return HealthResponse(
        status="healthy" if all(services.values()) else "degraded",
        timestamp=datetime.utcnow().isoformat(),
        version=settings.app_version,
        services=services
    )


@app.post("/chat", response_model=ChatResponse, tags=["Chat"])
async def chat(request: ChatRequest):
    """
    Chat with the banking AI assistant
    
    This endpoint processes user queries and routes them to appropriate specialized agents.
    The AI can handle:
    - Account creation and management
    - Transaction history and details
    - Fund transfers
    - Card applications and management
    - KYC verification
    - General banking inquiries
    """
    try:
        logger.info(f"Chat request: {request.message[:100]}...")
        
        # Process query through orchestrator
        response = orchestrator.process_query(
            query=request.message,
            session_id=request.session_id,
            context=request.context
        )
        
        # Convert to response model
        return ChatResponse(
            answer=response.get("answer", "I apologize, but I couldn't process that request."),
            agent=response.get("agent", "unknown"),
            session_id=response.get("session_id", ""),
            intent=response.get("intent", "unknown"),
            confidence=response.get("confidence", 0.0),
            success=response.get("success", False),
            data=response.get("data", {}),
            next_steps=response.get("next_steps", []),
            timestamp=response.get("timestamp", datetime.utcnow().isoformat())
        )
        
    except Exception as e:
        logger.error(f"Chat error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/stats", tags=["General"])
async def get_stats():
    """Get system statistics"""
    try:
        stats = orchestrator.get_stats()
        return {
            "orchestrator": stats,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Stats error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/intents", tags=["General"])
async def list_intents():
    """List supported intents"""
    from agents.intent_classifier import Intent
    
    return {
        "intents": [intent.value for intent in Intent],
        "count": len(Intent)
    }


# Error handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """Handle HTTP exceptions"""
    return {
        "error": exc.detail,
        "status_code": exc.status_code,
        "timestamp": datetime.utcnow().isoformat()
    }


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """Handle general exceptions"""
    logger.error(f"Unhandled exception: {exc}")
    return {
        "error": "Internal server error",
        "detail": str(exc) if settings.debug else "An error occurred",
        "status_code": 500,
        "timestamp": datetime.utcnow().isoformat()
    }


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "api.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.api_reload,
        log_level=settings.log_level.lower()
    )
