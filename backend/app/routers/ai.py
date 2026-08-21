import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.agent.orchestrator import AIAgentOrchestrator
from app.database import get_db
from app.routers.auth import get_current_user_dependency
from app.schemas.ai import ChatRequest, ChatResponse, ConversationResponse, MessageResponse
from app.models.ai_conversation import AIConversation
from app.models.ai_message import AIMessage
from app.config import get_settings

router = APIRouter(prefix="/api/ai", tags=["AI Agent"])


@router.get("/info")
async def get_ai_info():
    """Return live runtime AI configuration and active tool counts."""
    settings = get_settings()
    orchestrator = AIAgentOrchestrator(
        llm_api_key=settings.effective_llm_api_key,
        llm_model=settings.effective_llm_model,
        llm_provider=settings.LLM_PROVIDER
    )
    return {
        "provider": settings.LLM_PROVIDER.upper(),
        "model": settings.effective_llm_model,
        "tools_count": len(orchestrator.tools),
        "tool_names": list(orchestrator.tools.keys()),
        "is_configured": bool(settings.effective_llm_api_key),
        "simulation_mode": settings.SIMULATION_MODE,
        "autonomous_mode": True,
        "monitoring_enabled": True,
    }


@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user_dependency),
):
    settings = get_settings()
    orchestrator = AIAgentOrchestrator(
        llm_api_key=settings.effective_llm_api_key,
        llm_model=settings.effective_llm_model,
        llm_provider=settings.LLM_PROVIDER
    )
    
    result = await orchestrator.process_message(
        db=db,
        merchant_id=current_user.merchant_id,
        user_id=current_user.id,
        conversation_id=request.conversation_id,
        message=request.message,
    )
    
    # process_message saves the messages to the DB, so we can just return the response
    return ChatResponse(
        conversation_id=request.conversation_id,
        message=MessageResponse(
            id=uuid.uuid4(),
            role="assistant",
            content=result.get("content", ""),
            tools_called=result.get("tool_calls", []),
            token_count=0,
        ),
        tools_called=result.get("tool_calls", []),
        suggestions=[],
    )


@router.get("/conversations", response_model=list[ConversationResponse])
async def list_conversations(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user_dependency),
):
    result = await db.execute(
        select(AIConversation)
        .where(AIConversation.merchant_id == current_user.merchant_id)
        .order_by(AIConversation.created_at.desc())
    )
    conversations = result.scalars().all()
    
    return [
        ConversationResponse(
            id=c.id,
            merchant_id=c.merchant_id,
            user_id=c.user_id,
            title=c.title,
            messages=[],
            created_at=c.created_at,
            updated_at=c.updated_at,
        )
        for c in conversations
    ]


@router.get("/conversations/{conversation_id}", response_model=ConversationResponse)
async def get_conversation(
    conversation_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user_dependency),
):
    result = await db.execute(
        select(AIConversation)
        .options(selectinload(AIConversation.messages))
        .where(
            AIConversation.id == conversation_id,
            AIConversation.merchant_id == current_user.merchant_id
        )
    )
    conv = result.scalar_one_or_none()
    
    if not conv:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found",
        )
        
    messages = [
        MessageResponse(
            id=m.id,
            role=m.role,
            content=m.content,
            tools_called=m.tools_called,
            token_count=m.token_count,
            created_at=m.created_at,
        )
        for m in conv.messages
    ]
    
    return ConversationResponse(
        id=conv.id,
        merchant_id=conv.merchant_id,
        user_id=conv.user_id,
        title=conv.title,
        messages=messages,
        created_at=conv.created_at,
        updated_at=conv.updated_at,
    )


@router.post("/conversations", response_model=ConversationResponse, status_code=status.HTTP_201_CREATED)
async def create_conversation(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user_dependency),
):
    conv = AIConversation(
        merchant_id=current_user.merchant_id,
        user_id=current_user.id,
        title="New conversation"
    )
    db.add(conv)
    await db.commit()
    await db.refresh(conv)
    
    return ConversationResponse(
        id=conv.id,
        merchant_id=conv.merchant_id,
        user_id=conv.user_id,
        title=conv.title,
        messages=[],
        created_at=conv.created_at,
        updated_at=conv.updated_at,
    )
