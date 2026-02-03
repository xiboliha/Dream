"""FastAPI application for AI Girlfriend Agent web interface."""

import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException, Depends, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from loguru import logger

from config.settings import settings


class ChatRequest(BaseModel):
    """Chat request model."""
    user_id: int
    message: str
    message_type: str = "text"


class MessageItem(BaseModel):
    """Single message item in multi-message response."""
    content: str
    typing_delay: float = 1.0


class ChatResponse(BaseModel):
    """Chat response model."""
    response: str
    messages: List[MessageItem] = []  # New: multiple messages support
    conversation_id: int
    session_id: str
    emotion_detected: Optional[str] = None
    typing_delay: float = 1.0


class UserStatusResponse(BaseModel):
    """User status response model."""
    user_id: int
    intimacy: float
    trust: float
    relationship_stage: str
    total_interactions: int
    consecutive_days: int


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    version: str
    environment: str
    rag_enabled: bool = False
    rag_index_size: int = 0


# Global instances
_conversation_engine = None
_coordinator = None
_dialogue_rag = None
_proactive_service = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    global _conversation_engine, _coordinator, _dialogue_rag, _proactive_service

    logger.info("Starting AI Girlfriend Agent API...")

    # Initialize services
    from src.utils.logger import setup_logger
    from src.services.storage import init_database, init_cache, close_database, close_cache
    from src.services.ai import create_ai_service
    from src.services.ai.embedding_service import EmbeddingService
    from src.services.memory import MemoryManager
    from src.core.conversation import ConversationEngine
    from src.core.personality import init_personality_system
    from src.core.coordinator import init_coordinator
    from src.services.knowledge import VectorStore, DialogueRAG
    from src.services.proactive import init_proactive_service

    setup_logger(log_level=settings.log_level)

    # Initialize database
    init_database(settings.database_url, echo=settings.database_echo)

    # Initialize cache
    await init_cache(settings.redis_url, settings.redis_password)

    # Initialize AI service
    ai_service = create_ai_service(
        provider=settings.ai_provider.value,
        api_key=settings.get_ai_api_key(),
        model=settings.get_ai_model(),
    )

    # Initialize RAG service
    try:
        embedding_service = EmbeddingService(
            api_key=settings.get_ai_api_key(),
            model="text-embedding-v3",
            dimension=1024,
        )

        use_qdrant = settings.rag_backend == "qdrant"

        if use_qdrant:
            from src.services.knowledge import QdrantStore
            vector_store = QdrantStore(
                collection_name=settings.qdrant_collection,
                dimension=1024,
                host=settings.qdrant_host,
                port=settings.qdrant_port,
                url=settings.qdrant_url,
                api_key=settings.qdrant_api_key,
            )
            logger.info("Using Qdrant backend for RAG")
        else:
            vector_store_path = os.path.join(
                settings.data_dir, "vector_store", "dialogue_index"
            )
            os.makedirs(os.path.dirname(vector_store_path), exist_ok=True)
            vector_store = VectorStore(
                dimension=1024,
                storage_path=vector_store_path,
            )
            logger.info("Using FAISS backend for RAG")

        _dialogue_rag = DialogueRAG(
            embedding_service=embedding_service,
            vector_store=vector_store,
            use_qdrant=use_qdrant,
        )

        # Initialize RAG index
        await _dialogue_rag.initialize()
        logger.info(f"RAG service initialized with {_dialogue_rag.index_size} dialogues")
    except Exception as e:
        logger.warning(f"RAG service initialization failed: {e}, continuing without RAG")
        _dialogue_rag = None

    # Initialize personality system
    personality_system = init_personality_system()
    if personality_system.list_personalities():
        personality_system.set_current_personality(
            personality_system.list_personalities()[0]
        )

    # Initialize memory manager
    from src.services.storage import get_cache_service
    memory_manager = MemoryManager(
        ai_service=ai_service,
        cache_service=get_cache_service(),
        short_term_limit=settings.short_term_memory_limit,
        consolidation_threshold=settings.long_term_memory_threshold,
    )

    # Initialize conversation engine
    _conversation_engine = ConversationEngine(
        ai_service=ai_service,
        memory_manager=memory_manager,
        max_context_messages=settings.max_context_messages,
        response_timeout=settings.response_timeout,
        dialogue_rag=_dialogue_rag,
    )

    # Initialize coordinator
    _coordinator = init_coordinator(_conversation_engine)

    # Initialize proactive message service
    _proactive_service = init_proactive_service()
    # 配置AI和DB服务，用于智能话题生成
    from src.services.storage import get_database_service
    _proactive_service.set_services(ai_service, get_database_service())
    _proactive_service.start()

    logger.info("API initialization complete")

    yield

    # Cleanup
    logger.info("Shutting down API...")
    if _proactive_service:
        await _proactive_service.stop()
    await ai_service.close()
    await close_cache()
    await close_database()
    logger.info("API shutdown complete")


# Create FastAPI app
app = FastAPI(
    title="AI Girlfriend Agent API",
    description="API for AI Girlfriend chatbot with memory and personality",
    version="0.1.0",
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Mount static assets directory
assets_path = Path(__file__).parent / "interfaces" / "web" / "assets"
if assets_path.exists():
    app.mount("/assets", StaticFiles(directory=str(assets_path)), name="assets")


# Serve static chat interface
@app.get("/")
async def serve_chat_interface():
    """Serve the chat interface HTML."""
    html_path = Path(__file__).parent / "interfaces" / "web" / "chat.html"
    if html_path.exists():
        return FileResponse(html_path)
    return {"message": "Welcome to AI Girlfriend Agent API. Visit /docs for API documentation."}


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    global _dialogue_rag
    return HealthResponse(
        status="healthy",
        version="0.1.0",
        environment=settings.environment.value,
        rag_enabled=_dialogue_rag is not None and _dialogue_rag.is_initialized,
        rag_index_size=_dialogue_rag.index_size if _dialogue_rag else 0,
    )


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Send a chat message and get response."""
    global _conversation_engine, _proactive_service

    if not _conversation_engine:
        raise HTTPException(status_code=503, detail="Service not initialized")

    try:
        from src.services.storage import get_database_service
        from src.core.personality import get_personality_system
        from src.services.emotion import get_emotion_analyzer

        db = get_database_service()
        personality_system = get_personality_system()
        emotion_analyzer = get_emotion_analyzer()

        # Update user activity for proactive messaging
        if _proactive_service:
            _proactive_service.update_user_activity(request.user_id)

        async with db.get_async_session() as session:
            # Analyze emotion
            emotion_result = emotion_analyzer.analyze(request.message)

            # Get personality config
            personality_config = personality_system.get_personality_for_user(
                request.user_id
            )

            # Process message
            result = await _conversation_engine.process_message(
                session=session,
                user_id=request.user_id,
                message_content=request.message,
                message_type=request.message_type,
                personality_config=personality_config,
            )

        return ChatResponse(
            response=result["response"],
            messages=[MessageItem(**m) for m in result.get("messages", [])],
            conversation_id=result["conversation_id"],
            session_id=result["session_id"],
            emotion_detected=emotion_result.primary_emotion.value,
            typing_delay=result.get("typing_delay", 1.0),
        )

    except Exception as e:
        logger.error(f"Chat error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/users/{user_id}/status", response_model=UserStatusResponse)
async def get_user_status(user_id: int):
    """Get user relationship status."""
    try:
        from src.services.storage import get_database_service
        from src.core.relationship import get_relationship_builder

        db = get_database_service()
        relationship_builder = get_relationship_builder()

        async with db.get_async_session() as session:
            metrics = await relationship_builder.get_metrics(session, user_id)

        return UserStatusResponse(
            user_id=user_id,
            intimacy=metrics.intimacy,
            trust=metrics.trust,
            relationship_stage=metrics.get_stage().value,
            total_interactions=metrics.total_interactions,
            consecutive_days=metrics.consecutive_days,
        )

    except Exception as e:
        logger.error(f"Get user status error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/users/{user_id}/memories")
async def get_user_memories(user_id: int, limit: int = 20):
    """Get user's long-term memories."""
    try:
        from src.services.storage import get_database_service
        from src.services.memory import MemoryManager
        from src.services.ai import create_ai_service

        db = get_database_service()

        # Create a temporary memory manager for query
        ai_service = create_ai_service(
            provider=settings.ai_provider.value,
            api_key=settings.get_ai_api_key(),
            model=settings.get_ai_model(),
        )
        memory_manager = MemoryManager(ai_service=ai_service)

        async with db.get_async_session() as session:
            memories = await memory_manager.get_user_memories(
                session, user_id, limit=limit
            )

        await ai_service.close()

        return {
            "user_id": user_id,
            "memories": [
                {
                    "id": m.id,
                    "type": m.memory_type,
                    "key": m.key,
                    "value": m.value,
                    "importance": m.importance,
                    "created_at": m.created_at.isoformat() if m.created_at else None,
                }
                for m in memories
            ],
        }

    except Exception as e:
        logger.error(f"Get memories error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/personalities")
async def list_personalities():
    """List available personalities."""
    from src.core.personality import get_personality_system

    system = get_personality_system()
    personalities = []

    for name in system.list_personalities():
        config = system.get_personality(name)
        if config:
            personalities.append({
                "name": config.name,
                "display_name": config.display_name,
                "description": config.description,
            })

    return {"personalities": personalities}


@app.post("/users/{user_id}/greeting")
async def get_greeting(user_id: int):
    """Get a greeting message for user."""
    global _conversation_engine

    if not _conversation_engine:
        raise HTTPException(status_code=503, detail="Service not initialized")

    try:
        from src.services.storage import get_database_service
        from src.core.personality import get_personality_system

        db = get_database_service()
        personality_system = get_personality_system()

        async with db.get_async_session() as session:
            personality_config = personality_system.get_personality_for_user(user_id)
            greeting = await _conversation_engine.get_greeting(
                session=session,
                user_id=user_id,
                personality_config=personality_config,
            )

        return {"greeting": greeting}

    except Exception as e:
        logger.error(f"Get greeting error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# WebSocket endpoint for real-time messaging
@app.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: int):
    """WebSocket endpoint for real-time proactive messages."""
    global _proactive_service

    await websocket.accept()
    logger.info(f"WebSocket connected for user {user_id}")

    if _proactive_service:
        _proactive_service.register_websocket(user_id, websocket)
        _proactive_service.update_user_activity(user_id)

    try:
        while True:
            # 接收客户端消息（心跳或活动更新）
            data = await websocket.receive_text()
            import json
            try:
                msg = json.loads(data)
                if msg.get("type") == "ping":
                    await websocket.send_text(json.dumps({"type": "pong"}))
                elif msg.get("type") == "activity":
                    if _proactive_service:
                        _proactive_service.update_user_activity(user_id)
            except json.JSONDecodeError:
                pass

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for user {user_id}")
    except Exception as e:
        logger.debug(f"WebSocket error for user {user_id}: {e}")
    finally:
        if _proactive_service:
            _proactive_service.unregister_websocket(user_id, websocket)


# RAG API endpoints
class DialogueAddRequest(BaseModel):
    """Request to add dialogue."""
    user: str
    response: str
    category: str = ""
    mood: str = "neutral"
    id: Optional[str] = None


class DialogueBatchAddRequest(BaseModel):
    """Request to add multiple dialogues."""
    dialogues: List[DialogueAddRequest]


@app.post("/rag/dialogues")
async def add_dialogue(request: DialogueAddRequest):
    """Add a single dialogue to RAG index."""
    global _dialogue_rag

    if not _dialogue_rag:
        raise HTTPException(status_code=503, detail="RAG service not available")

    try:
        success = await _dialogue_rag.add_dialogue(
            user=request.user,
            response=request.response,
            category=request.category,
            mood=request.mood,
            dialogue_id=request.id,
        )

        if success:
            return {"status": "success", "index_size": _dialogue_rag.index_size}
        else:
            raise HTTPException(status_code=500, detail="Failed to add dialogue")

    except Exception as e:
        logger.error(f"Add dialogue error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/rag/dialogues/batch")
async def add_dialogues_batch(request: DialogueBatchAddRequest):
    """Add multiple dialogues to RAG index."""
    global _dialogue_rag

    if not _dialogue_rag:
        raise HTTPException(status_code=503, detail="RAG service not available")

    try:
        dialogues = [d.model_dump() for d in request.dialogues]
        count = await _dialogue_rag.add_dialogues_batch(dialogues)

        return {
            "status": "success",
            "added": count,
            "index_size": _dialogue_rag.index_size,
        }

    except Exception as e:
        logger.error(f"Batch add dialogues error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/rag/stats")
async def get_rag_stats():
    """Get RAG service statistics."""
    global _dialogue_rag

    if not _dialogue_rag:
        return {"status": "disabled", "reason": "RAG service not available"}

    return _dialogue_rag.get_stats()


@app.get("/rag/search")
async def search_dialogues(query: str, top_k: int = 5, threshold: float = 0.5):
    """Search for similar dialogues."""
    global _dialogue_rag

    if not _dialogue_rag:
        raise HTTPException(status_code=503, detail="RAG service not available")

    try:
        results = await _dialogue_rag.search(query, top_k, threshold)
        return {"query": query, "results": results}

    except Exception as e:
        logger.error(f"Search error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============ 日志监控 API ============

@app.get("/logs")
async def get_logs(limit: int = 100, level: Optional[str] = None):
    """获取最近的日志记录。"""
    from src.utils.logger import get_log_store

    log_store = get_log_store()
    logs = log_store.get_logs(limit=limit, level=level)

    return {
        "count": len(logs),
        "logs": logs,
    }


@app.get("/logs/chats")
async def get_chat_logs(limit: int = 50):
    """获取最近的对话日志。"""
    from src.utils.logger import get_log_store

    log_store = get_log_store()
    chat_logs = log_store.get_chat_logs(limit=limit)

    return {
        "count": len(chat_logs),
        "chats": chat_logs,
    }


@app.get("/logs/errors")
async def get_error_logs(limit: int = 50):
    """获取最近的错误日志。"""
    from src.utils.logger import get_log_store

    log_store = get_log_store()
    error_logs = log_store.get_error_logs(limit=limit)

    return {
        "count": len(error_logs),
        "errors": error_logs,
    }


@app.get("/logs/stats")
async def get_log_stats():
    """获取日志统计信息。"""
    from src.utils.logger import get_log_store

    log_store = get_log_store()
    stats = log_store.get_stats()

    return stats


@app.get("/monitor")
async def serve_monitor_page():
    """Serve the monitor page."""
    html_path = Path(__file__).parent / "interfaces" / "web" / "monitor.html"
    if html_path.exists():
        return FileResponse(html_path)
    raise HTTPException(status_code=404, detail="Monitor page not found")


# ============ 主动消息 API ============

@app.get("/users/{user_id}/proactive")
async def get_proactive_messages(user_id: int):
    """获取用户的主动消息（定时问候、空闲提醒等）。

    前端应定期轮询此接口获取主动消息。
    """
    global _proactive_service

    if not _proactive_service:
        return {"messages": []}

    messages = _proactive_service.get_pending_messages(user_id)
    return {"messages": messages}


@app.post("/users/{user_id}/activity")
async def update_user_activity(user_id: int):
    """更新用户活动时间（用于空闲检测）。

    前端可在用户有任何交互时调用此接口。
    """
    global _proactive_service

    if _proactive_service:
        _proactive_service.update_user_activity(user_id)

    return {"status": "ok"}


@app.get("/proactive/settings")
async def get_proactive_settings():
    """获取主动消息设置。"""
    return {
        "morning_greeting_hour": settings.morning_greeting_hour,
        "noon_greeting_hour": settings.noon_greeting_hour,
        "afternoon_nap_hour": settings.afternoon_nap_hour,
        "dinner_greeting_hour": settings.dinner_greeting_hour,
        "night_greeting_hour": settings.night_greeting_hour,
        "idle_threshold_minutes": 30,
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "src.app:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
    )
