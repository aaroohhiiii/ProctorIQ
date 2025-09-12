"""
API Routes for ProctorIQ Backend
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import List, Dict, Any
import json
from pathlib import Path

from config.settings import get_settings, Settings

router = APIRouter()

@router.get("/")
async def api_root():
    """API root endpoint"""
    return {
        "message": "ProctorIQ API v1",
        "endpoints": {
            "upload": "/upload/answer-sheet",
            "process": "/process/answer-sheet/{upload_id}",
            "results": "/results/{upload_id}",
            "uploads": "/uploads"
        }
    }

@router.get("/papers")
async def list_question_papers():
    """
    List available question papers
    
    Returns:
        List of available question papers with metadata
    """
    try:
        docs_dir = Path("docs")
        papers = []
        
        for paper_file in docs_dir.glob("Paper*_Structured.json"):
            try:
                with open(paper_file, "r") as f:
                    paper_data = json.load(f)
                
                papers.append({
                    "file_name": paper_file.name,
                    "paper_number": paper_file.stem.split("_")[0].replace("Paper", ""),
                    "title": paper_data.get("title", "Unknown Paper"),
                    "total_marks": paper_data.get("total_marks", 0),
                    "sections": len(paper_data.get("sections", [])),
                    "questions_count": sum(
                        len(section.get("questions", [])) 
                        for section in paper_data.get("sections", [])
                    )
                })
            except (json.JSONDecodeError, KeyError) as e:
                continue
        
        return {
            "papers": papers,
            "total_count": len(papers)
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list question papers: {str(e)}"
        )

@router.get("/papers/{paper_number}")
async def get_question_paper(paper_number: str):
    """
    Get specific question paper details
    
    Args:
        paper_number: Paper number (e.g., "1", "2", "3")
    
    Returns:
        Question paper structure and content
    """
    try:
        paper_path = Path(f"docs/Paper{paper_number}_Structured.json")
        
        if not paper_path.exists():
            raise HTTPException(
                status_code=404,
                detail=f"Question paper {paper_number} not found"
            )
        
        with open(paper_path, "r") as f:
            paper_data = json.load(f)
        
        return {
            "paper_number": paper_number,
            "data": paper_data
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to load question paper: {str(e)}"
        )

@router.get("/config")
async def get_api_config(settings: Settings = Depends(get_settings)):
    """
    Get API configuration (non-sensitive data only)
    
    Returns:
        Public configuration settings
    """
    return {
        "app_name": settings.app_name,
        "app_version": settings.app_version,
        "debug": settings.debug,
        "max_file_size": settings.max_file_size,
        "allowed_file_types": settings.allowed_file_types,
        "openai_model": settings.openai_model,
        "vector_db_enabled": bool(settings.pinecone_api_key)
    }

@router.get("/status")
async def get_system_status():
    """
    Get system status and health information
    
    Returns:
        System status information
    """
    try:
        # Check if required directories exist
        docs_dir = Path("docs")
        uploads_dir = Path("uploads")
        
        # Count available papers
        papers_count = len(list(docs_dir.glob("Paper*_Structured.json")))
        
        # Count upload sessions
        upload_sessions = len([d for d in uploads_dir.iterdir() if d.is_dir()]) if uploads_dir.exists() else 0
        
        return {
            "status": "healthy",
            "directories": {
                "docs_exists": docs_dir.exists(),
                "uploads_exists": uploads_dir.exists()
            },
            "resources": {
                "question_papers": papers_count,
                "upload_sessions": upload_sessions
            },
            "services": {
                "api": "running",
                "file_upload": "available",
                "ocr_processing": "available",
                "ai_evaluation": "available"
            }
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"System status check failed: {str(e)}"
        )
