from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Dict
from pydantic import BaseModel

from models.models import User, CrawledContent, ContentPiece, ContentStatus, ToneType
from services.posting_service import PostingService
from api.deps import get_db, get_current_user

router = APIRouter(prefix="/content", tags=["content"])

class GenerateRequest(BaseModel):
    crawled_content_id: int
    tone: ToneType = ToneType.PROFESSIONAL

class ContentResponse(BaseModel):
    id: int
    content: str
    status: ContentStatus
    tone: ToneType
    platform: str
    url: str = None
    error: str = None

@router.get("/tones", response_model=List[Dict])
async def list_available_tones():
    """Get list of available content tones with descriptions"""
    return [
        {
            "type": ToneType.PROFESSIONAL,
            "name": "Professional",
            "description": "Formal, business-like tone suitable for corporate content"
        },
        {
            "type": ToneType.CASUAL,
            "name": "Casual",
            "description": "Friendly, conversational tone with emojis and relaxed language"
        },
        {
            "type": ToneType.HUMOROUS,
            "name": "Humorous",
            "description": "Fun, witty tone with wordplay and entertainment focus"
        },
        {
            "type": ToneType.INFORMATIVE,
            "name": "Informative",
            "description": "Educational, factual tone focused on clear explanations"
        }
    ]

@router.post("/generate", response_model=List[ContentResponse])
async def generate_content(
    request: GenerateRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Generate and post content from crawled content with specified tone"""
    # Get crawled content
    crawled_content = db.query(CrawledContent).filter_by(
        id=request.crawled_content_id
    ).first()
    
    if not crawled_content:
        raise HTTPException(status_code=404, detail="Content not found")
    
    # Verify ownership through website relationship
    if crawled_content.website.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    # Initialize posting service
    posting_service = PostingService(db)
    
    # Process content in background with specified tone
    results = await posting_service.process_crawled_content(
        crawled_content,
        current_user,
        tone=request.tone
    )
    
    # Format response
    responses = []
    for result in results:
        if result["success"]:
            content_piece = db.query(ContentPiece).get(result["content_id"])
            responses.append(
                ContentResponse(
                    id=result["content_id"],
                    content=content_piece.content,
                    status=ContentStatus.PUBLISHED,
                    tone=content_piece.tone,
                    platform=result["platform"].value,
                    url=result.get("url")
                )
            )
        else:
            responses.append(
                ContentResponse(
                    id=result.get("content_id", 0),
                    content="",
                    status=ContentStatus.FAILED,
                    tone=request.tone,
                    platform=result["platform"].value,
                    error=result.get("error")
                )
            )
    
    return responses

@router.get("/pieces", response_model=List[ContentResponse])
async def list_content_pieces(
    crawled_content_id: int = None,
    status: ContentStatus = None,
    tone: ToneType = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List content pieces with optional filters"""
    query = db.query(ContentPiece).join(
        ContentPiece.platform_account
    ).filter(
        ContentPiece.platform_account.has(user_id=current_user.id)
    )
    
    if crawled_content_id:
        query = query.filter(ContentPiece.crawled_content_id == crawled_content_id)
    
    if status:
        query = query.filter(ContentPiece.status == status)
        
    if tone:
        query = query.filter(ContentPiece.tone == tone)
    
    pieces = query.all()
    
    return [
        ContentResponse(
            id=piece.id,
            content=piece.content,
            status=piece.status,
            tone=piece.tone,
            platform=piece.platform_account.platform.value,
            url=piece.meta_data.get(f"{piece.platform_account.platform.value.lower()}_url")
        )
        for piece in pieces
    ]

@router.post("/pieces/{piece_id}/retry")
async def retry_failed_content(
    piece_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Retry posting a failed content piece"""
    # Get content piece
    piece = db.query(ContentPiece).filter_by(id=piece_id).first()
    if not piece:
        raise HTTPException(status_code=404, detail="Content piece not found")
    
    # Verify ownership
    if piece.platform_account.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    # Only retry failed content
    if piece.status != ContentStatus.FAILED:
        raise HTTPException(status_code=400, detail="Can only retry failed content")
    
    # Initialize posting service and retry
    posting_service = PostingService(db)
    result = await posting_service.post_content(piece)
    
    if result["success"]:
        return ContentResponse(
            id=piece.id,
            content=piece.content,
            status=ContentStatus.PUBLISHED,
            tone=piece.tone,
            platform=piece.platform_account.platform.value,
            url=result.get("url")
        )
    else:
        return ContentResponse(
            id=piece.id,
            content=piece.content,
            status=ContentStatus.FAILED,
            tone=piece.tone,
            platform=piece.platform_account.platform.value,
            error=result.get("error")
        )
