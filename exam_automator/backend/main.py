"""
ProctorIQ - Automated Exam Evaluation System
FastAPI Backend with File Upload and Processing
"""

from fastapi import FastAPI, File, UploadFile, HTTPException, Depends, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from typing import List, Optional
import os
import shutil
import uuid
from pathlib import Path
import json
from datetime import datetime

from api.routes import router as api_router
from config.settings import get_settings
from services.vector_evaluator import VectorEnhancedEvaluator
from ocr.extractor import OCRExtractor

# Initialize FastAPI app
app = FastAPI(
    title="ProctorIQ API",
    description="Automated Exam Evaluation System with AI-powered grading",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],  # React dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(api_router, prefix="/api/v1")

# Create upload directory if it doesn't exist
UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

# Mount static files for serving uploaded files
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "ProctorIQ API is running",
        "version": "1.0.0",
        "docs": "/docs",
        "status": "healthy"
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "service": "ProctorIQ API"
    }

@app.post("/api/v1/upload/answer-sheet")
async def upload_answer_sheet(
    files: List[UploadFile] = File(...),
    student_name: str = Form(...),
    exam_id: str = Form(...),
    paper_number: Optional[str] = Form(None)
):
    """
    Upload student answer sheet files (images or PDFs)
    
    Args:
        files: List of uploaded files (images or PDFs)
        student_name: Name of the student
        exam_id: Exam identifier
        paper_number: Optional paper number for specific exam papers
    
    Returns:
        Upload confirmation with file details
    """
    try:
        # Generate unique upload session ID
        upload_id = str(uuid.uuid4())
        
        # Create directory for this upload session
        session_dir = UPLOAD_DIR / upload_id
        session_dir.mkdir(exist_ok=True)
        
        uploaded_files = []
        
        for file in files:
            # Validate file type - now supporting more formats
            if not file.content_type or not (
                file.content_type.startswith('image/') or 
                file.content_type == 'application/pdf' or
                file.content_type == 'text/plain' or
                file.content_type == 'application/msword' or
                file.content_type == 'application/vnd.openxmlformats-officedocument.wordprocessingml.document' or
                file.content_type == 'application/rtf' or
                file.content_type == 'text/markdown' or
                file.content_type == 'text/csv' or
                file.content_type.startswith('text/')
            ):
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid file type: {file.content_type}. Supported formats: PDF, Images (JPG/PNG/BMP/TIFF), Text files (TXT/MD), Word documents (DOC/DOCX), RTF, CSV"
                )
            
            # Generate unique filename
            file_extension = os.path.splitext(file.filename)[1]
            unique_filename = f"{uuid.uuid4()}{file_extension}"
            file_path = session_dir / unique_filename
            
            # Save file
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            
            uploaded_files.append({
                "original_name": file.filename,
                "saved_name": unique_filename,
                "file_path": str(file_path),
                "file_size": os.path.getsize(file_path),
                "content_type": file.content_type
            })
        
        # Create upload metadata
        upload_metadata = {
            "upload_id": upload_id,
            "student_name": student_name,
            "exam_id": exam_id,
            "paper_number": paper_number,
            "upload_timestamp": datetime.now().isoformat(),
            "files": uploaded_files,
            "status": "uploaded",
            "processed": False
        }
        
        # Save metadata
        metadata_path = session_dir / "metadata.json"
        with open(metadata_path, "w") as f:
            json.dump(upload_metadata, f, indent=2)
        
        return JSONResponse(
            status_code=200,
            content={
                "message": "Files uploaded successfully",
                "upload_id": upload_id,
                "files_count": len(uploaded_files),
                "metadata": upload_metadata
            }
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Upload failed: {str(e)}"
        )

@app.post("/api/v1/upload/multiple-answer-sheets")
async def upload_multiple_answer_sheets(
    files: List[UploadFile] = File(...),
    exam_id: str = Form(...),
    paper_number: Optional[str] = Form(None)
):
    """
    Upload multiple student answer sheets for batch processing
    
    Args:
        files: List of answer sheet files (images, PDFs, text files)
        exam_id: Exam identifier
        paper_number: Question paper number (optional)
    
    Returns:
        Batch upload session with individual upload IDs for each student
    """
    try:
        # Create batch session ID
        batch_id = str(uuid.uuid4())
        batch_dir = UPLOAD_DIR / f"batch_{batch_id}"
        batch_dir.mkdir(exist_ok=True)
        
        uploaded_sessions = []
        
        # Process each file as a separate student submission
        for i, file in enumerate(files):
            if not file.filename:
                continue
                
            # Extract student name from filename (remove extension)
            student_name = os.path.splitext(file.filename)[0]
            
            # Create individual upload session for each student
            upload_id = str(uuid.uuid4())
            session_dir = UPLOAD_DIR / upload_id
            session_dir.mkdir(exist_ok=True)
            
            # Validate file type
            if not file.content_type or not (
                file.content_type.startswith('image/') or 
                file.content_type == 'application/pdf' or
                file.content_type == 'text/plain' or
                file.content_type == 'application/msword' or
                file.content_type == 'application/vnd.openxmlformats-officedocument.wordprocessingml.document' or
                file.content_type == 'application/rtf' or
                file.content_type == 'text/markdown' or
                file.content_type == 'text/csv' or
                file.content_type.startswith('text/')
            ):
                print(f"⚠️ Skipping invalid file type: {file.filename} ({file.content_type})")
                continue
            
            # Generate unique filename
            file_extension = os.path.splitext(file.filename)[1]
            unique_filename = f"{uuid.uuid4()}{file_extension}"
            file_path = session_dir / unique_filename
            
            # Save file
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            
            # Create upload metadata for individual student
            upload_metadata = {
                "upload_id": upload_id,
                "student_name": student_name,
                "exam_id": exam_id,
                "paper_number": paper_number,
                "upload_timestamp": datetime.now().isoformat(),
                "files": [{
                    "original_name": file.filename,
                    "saved_name": unique_filename,
                    "file_path": str(file_path),
                    "file_size": os.path.getsize(file_path),
                    "content_type": file.content_type
                }],
                "status": "uploaded",
                "processed": False,
                "batch_id": batch_id
            }
            
            # Save individual metadata
            metadata_path = session_dir / "metadata.json"
            with open(metadata_path, "w") as f:
                json.dump(upload_metadata, f, indent=2)
            
            uploaded_sessions.append({
                "upload_id": upload_id,
                "student_name": student_name,
                "filename": file.filename,
                "file_size": os.path.getsize(file_path)
            })
        
        # Create batch metadata
        batch_metadata = {
            "batch_id": batch_id,
            "exam_id": exam_id,
            "paper_number": paper_number,
            "upload_timestamp": datetime.now().isoformat(),
            "total_students": len(uploaded_sessions),
            "uploaded_sessions": uploaded_sessions,
            "status": "uploaded",
            "processed": False
        }
        
        # Save batch metadata
        batch_metadata_path = batch_dir / "batch_metadata.json"
        with open(batch_metadata_path, "w") as f:
            json.dump(batch_metadata, f, indent=2)
        
        return JSONResponse(
            status_code=200,
            content={
                "message": f"Batch upload successful: {len(uploaded_sessions)} students",
                "batch_id": batch_id,
                "total_students": len(uploaded_sessions),
                "uploaded_sessions": uploaded_sessions,
                "batch_metadata": batch_metadata
            }
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Batch upload failed: {str(e)}"
        )

@app.post("/api/v1/process/answer-sheet/{upload_id}")
async def process_answer_sheet(upload_id: str):
    """
    Process uploaded answer sheet using OCR and AI evaluation
    
    Args:
        upload_id: Upload session ID from file upload
    
    Returns:
        Processing results with extracted text and evaluation
    """
    try:
        # Load upload metadata
        session_dir = UPLOAD_DIR / upload_id
        metadata_path = session_dir / "metadata.json"
        
        if not metadata_path.exists():
            raise HTTPException(
                status_code=404,
                detail="Upload session not found"
            )
        
        with open(metadata_path, "r") as f:
            metadata = json.load(f)
        
        # Initialize OCR extractor
        ocr_extractor = OCRExtractor()
        
        # Process each uploaded file
        processed_files = []
        extracted_texts = []
        
        for file_info in metadata["files"]:
            file_path = file_info["file_path"]
            
            # Extract text using OCR
            extracted_text = ocr_extractor.extract_text(file_path)
            extracted_texts.append(extracted_text)
            
            processed_files.append({
                "file_name": file_info["original_name"],
                "extracted_text": extracted_text,
                "text_length": len(extracted_text)
            })
        
        # Combine all extracted texts
        combined_text = "\n\n".join(extracted_texts)
        
        # Initialize AI evaluator
        settings = get_settings()
        evaluator = VectorEnhancedEvaluator(
            openai_api_key=settings.openai_api_key,
            use_vector_db=True
        )
        
        # Load appropriate question paper
        paper_number = metadata.get("paper_number", "1")
        paper_path = f"docs/Paper{paper_number}_Structured.json"
        
        try:
            with open(paper_path, "r") as f:
                question_paper = json.load(f)
        except FileNotFoundError:
            # Use default paper if specific paper not found
            paper_path = "docs/Paper1_Structured.json"
            with open(paper_path, "r") as f:
                question_paper = json.load(f)
        
        # Evaluate the answer sheet
        evaluation_result = evaluator.evaluate_answer_sheet(
            question_paper, 
            combined_text
        )
        
        # Convert evaluation result to serializable format
        def convert_to_serializable(obj):
            """Convert dataclass objects to dictionaries for JSON serialization"""
            if hasattr(obj, '__dict__'):
                result = {}
                for key, value in obj.__dict__.items():
                    if isinstance(value, list):
                        result[key] = [convert_to_serializable(item) for item in value]
                    elif hasattr(value, '__dict__'):
                        result[key] = convert_to_serializable(value)
                    else:
                        result[key] = value
                return result
            return obj

        evaluation_dict = convert_to_serializable(evaluation_result)

        # Update metadata with processing results
        metadata.update({
            "processed": True,
            "processing_timestamp": datetime.now().isoformat(),
            "extracted_text": combined_text,
            "evaluation_result": evaluation_dict,
            "status": "completed"
        })

        # Save updated metadata
        with open(metadata_path, "w") as f:
            json.dump(metadata, f, indent=2)

        return JSONResponse(
            status_code=200,
            content={
                "message": "Answer sheet processed successfully",
                "upload_id": upload_id,
                "student_name": metadata["student_name"],
                "processed_files": processed_files,
                "evaluation": {
                    "total_marks": evaluation_result.total_marks_awarded,
                    "possible_marks": evaluation_result.total_possible_marks,
                    "percentage": evaluation_result.percentage,
                    "overall_feedback": evaluation_result.overall_feedback
                },
                "detailed_results": evaluation_dict
            }
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Processing failed: {str(e)}"
        )

@app.post("/api/v1/process/batch/{batch_id}")
async def process_batch_answer_sheets(batch_id: str):
    """
    Process multiple answer sheets in parallel
    
    Args:
        batch_id: Batch session ID from multiple file upload
    
    Returns:
        Batch processing results with individual evaluation results
    """
    try:
        import asyncio
        import concurrent.futures
        from functools import partial
        
        # Load batch metadata
        batch_dir = UPLOAD_DIR / f"batch_{batch_id}"
        batch_metadata_path = batch_dir / "batch_metadata.json"
        
        if not batch_metadata_path.exists():
            raise HTTPException(
                status_code=404,
                detail="Batch session not found"
            )
        
        with open(batch_metadata_path, "r") as f:
            batch_metadata = json.load(f)
        
        print(f"🚀 Starting batch processing for {batch_metadata['total_students']} students")
        
        # Function to process a single student's answer sheet
        def process_single_student(upload_info):
            try:
                upload_id = upload_info["upload_id"]
                student_name = upload_info["student_name"]
                
                print(f"📝 Processing {student_name} ({upload_id})")
                
                # Load individual metadata
                session_dir = UPLOAD_DIR / upload_id
                metadata_path = session_dir / "metadata.json"
                
                with open(metadata_path, "r") as f:
                    metadata = json.load(f)
                
                # Initialize OCR extractor
                ocr_extractor = OCRExtractor()
                
                # Process files
                processed_files = []
                extracted_texts = []
                
                for file_info in metadata["files"]:
                    file_path = file_info["file_path"]
                    
                    try:
                        extracted_text = ocr_extractor.extract_text(file_path)
                        extracted_texts.append(extracted_text)
                        processed_files.append({
                            "filename": file_info["original_name"],
                            "extracted_length": len(extracted_text),
                            "status": "success"
                        })
                    except Exception as e:
                        processed_files.append({
                            "filename": file_info["original_name"],
                            "status": "error",
                            "error": str(e)
                        })
                
                # Combine all extracted texts
                combined_text = "\\n\\n".join(extracted_texts)
                
                # Initialize AI evaluator
                settings = get_settings()
                evaluator = VectorEnhancedEvaluator(
                    openai_api_key=settings.openai_api_key or "",
                    use_vector_db=True
                )
                
                # Determine paper number
                paper_number = metadata.get("paper_number", "1")
                paper_path = f"docs/Paper{paper_number}_Structured.json"
                
                if not os.path.exists(paper_path):
                    paper_path = "docs/Paper1_Structured.json"
                    paper_number = "1"
                
                # Load question paper
                question_paper = evaluator.load_structured_question_paper(paper_path)
                
                # Evaluate
                evaluation_result = evaluator.evaluate_answer_sheet(question_paper, combined_text)
                
                # Convert to serializable format
                def convert_to_serializable(obj):
                    """Convert complex objects to JSON-serializable format"""
                    if hasattr(obj, '__dict__'):
                        result = {}
                        for key, value in obj.__dict__.items():
                            if hasattr(value, '__dict__'):
                                result[key] = convert_to_serializable(value)
                            elif isinstance(value, list):
                                result[key] = [convert_to_serializable(item) for item in value]
                            else:
                                result[key] = value
                        return result
                    elif isinstance(obj, list):
                        return [convert_to_serializable(item) for item in obj]
                    else:
                        return obj
                
                evaluation_dict = convert_to_serializable(evaluation_result)
                
                # Update metadata
                metadata.update({
                    "extracted_text": combined_text,
                    "processed_files": processed_files,
                    "evaluation_result": evaluation_dict,
                    "status": "completed",
                    "processed": True,
                    "processing_timestamp": datetime.now().isoformat()
                })
                
                # Save updated metadata
                with open(metadata_path, "w") as f:
                    json.dump(metadata, f, indent=2)
                
                return {
                    "upload_id": upload_id,
                    "student_name": student_name,
                    "status": "success",
                    "evaluation": {
                        "total_marks": evaluation_result.total_marks_awarded,
                        "possible_marks": evaluation_result.total_possible_marks,
                        "percentage": evaluation_result.percentage,
                        "overall_feedback": evaluation_result.overall_feedback
                    }
                }
                
            except Exception as e:
                print(f"❌ Error processing {upload_info['student_name']}: {e}")
                return {
                    "upload_id": upload_info["upload_id"],
                    "student_name": upload_info["student_name"],
                    "status": "error",
                    "error": str(e)
                }
        
        # Process all students in parallel
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            # Submit all processing tasks
            future_to_student = {
                executor.submit(process_single_student, upload_info): upload_info
                for upload_info in batch_metadata["uploaded_sessions"]
            }
            
            # Collect results as they complete
            batch_results = []
            completed = 0
            total = len(batch_metadata["uploaded_sessions"])
            
            for future in concurrent.futures.as_completed(future_to_student):
                result = future.result()
                batch_results.append(result)
                completed += 1
                print(f"✅ Progress: {completed}/{total} students completed")
        
        # Calculate batch statistics
        successful_evaluations = [r for r in batch_results if r["status"] == "success"]
        failed_evaluations = [r for r in batch_results if r["status"] == "error"]
        
        if successful_evaluations:
            avg_percentage = sum(r["evaluation"]["percentage"] for r in successful_evaluations) / len(successful_evaluations)
            total_marks_awarded = sum(r["evaluation"]["total_marks"] for r in successful_evaluations)
            total_possible_marks = sum(r["evaluation"]["possible_marks"] for r in successful_evaluations)
        else:
            avg_percentage = 0
            total_marks_awarded = 0
            total_possible_marks = 0
        
        # Update batch metadata
        batch_metadata.update({
            "status": "completed",
            "processed": True,
            "processing_timestamp": datetime.now().isoformat(),
            "batch_results": batch_results,
            "statistics": {
                "total_students": total,
                "successful": len(successful_evaluations),
                "failed": len(failed_evaluations),
                "average_percentage": avg_percentage,
                "total_marks_awarded": total_marks_awarded,
                "total_possible_marks": total_possible_marks
            }
        })
        
        # Save updated batch metadata
        with open(batch_metadata_path, "w") as f:
            json.dump(batch_metadata, f, indent=2)
        
        print(f"🎉 Batch processing complete: {len(successful_evaluations)}/{total} successful")
        
        return JSONResponse(
            status_code=200,
            content={
                "message": f"Batch processing completed: {len(successful_evaluations)}/{total} successful",
                "batch_id": batch_id,
                "statistics": batch_metadata["statistics"],
                "results": batch_results
            }
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Batch processing failed: {str(e)}"
        )

@app.get("/api/v1/results/{upload_id}")
async def get_evaluation_results(upload_id: str):
    """
    Get evaluation results for a processed answer sheet
    
    Args:
        upload_id: Upload session ID
    
    Returns:
        Detailed evaluation results
    """
    try:
        session_dir = UPLOAD_DIR / upload_id
        metadata_path = session_dir / "metadata.json"
        
        if not metadata_path.exists():
            raise HTTPException(
                status_code=404,
                detail="Upload session not found"
            )
        
        with open(metadata_path, "r") as f:
            metadata = json.load(f)
        
        if not metadata.get("processed", False):
            raise HTTPException(
                status_code=400,
                detail="Answer sheet not yet processed"
            )
        
        return JSONResponse(
            status_code=200,
            content={
                "upload_id": upload_id,
                "student_info": {
                    "name": metadata["student_name"],
                    "exam_id": metadata["exam_id"],
                    "paper_number": metadata.get("paper_number")
                },
                "processing_info": {
                    "upload_timestamp": metadata["upload_timestamp"],
                    "processing_timestamp": metadata["processing_timestamp"],
                    "files_count": len(metadata["files"])
                },
                "evaluation_results": metadata["evaluation_result"]
            }
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve results: {str(e)}"
        )

@app.get("/api/v1/batch/results/{batch_id}")
async def get_batch_evaluation_results(batch_id: str):
    """
    Get batch evaluation results for multiple processed answer sheets
    
    Args:
        batch_id: Batch session ID
    
    Returns:
        Detailed batch evaluation results with statistics
    """
    try:
        batch_dir = UPLOAD_DIR / f"batch_{batch_id}"
        batch_metadata_path = batch_dir / "batch_metadata.json"
        
        if not batch_metadata_path.exists():
            raise HTTPException(
                status_code=404,
                detail="Batch session not found"
            )
        
        with open(batch_metadata_path, "r") as f:
            batch_metadata = json.load(f)
        
        if not batch_metadata.get("processed", False):
            raise HTTPException(
                status_code=400,
                detail="Batch not yet processed"
            )
        
        return JSONResponse(
            status_code=200,
            content={
                "batch_id": batch_id,
                "batch_info": {
                    "exam_id": batch_metadata["exam_id"],
                    "paper_number": batch_metadata.get("paper_number"),
                    "total_students": batch_metadata["total_students"]
                },
                "processing_info": {
                    "upload_timestamp": batch_metadata["upload_timestamp"],
                    "processing_timestamp": batch_metadata["processing_timestamp"]
                },
                "statistics": batch_metadata["statistics"],
                "results": batch_metadata["batch_results"]
            }
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve batch results: {str(e)}"
        )

@app.get("/api/v1/uploads")
async def list_uploads():
    """
    List all upload sessions
    
    Returns:
        List of all upload sessions with basic info
    """
    try:
        uploads = []
        corrupted_files = []
        
        for upload_dir in UPLOAD_DIR.iterdir():
            if upload_dir.is_dir():
                metadata_path = upload_dir / "metadata.json"
                if metadata_path.exists():
                    try:
                        with open(metadata_path, "r") as f:
                            content = f.read().strip()
                            # Remove any trailing % or other non-JSON characters
                            if content.endswith('%'):
                                content = content[:-1]
                            metadata = json.loads(content)
                        
                        uploads.append({
                            "upload_id": metadata["upload_id"],
                            "student_name": metadata.get("student_name", "Unknown"),
                            "exam_id": metadata.get("exam_id", "Unknown"),
                            "upload_timestamp": metadata.get("upload_timestamp", "Unknown"),
                            "status": metadata.get("status", "unknown"),
                            "processed": metadata.get("processed", False),
                            "files_count": len(metadata.get("files", []))
                        })
                    except (json.JSONDecodeError, KeyError) as e:
                        # Skip corrupted metadata files but log them
                        corrupted_files.append(upload_dir.name)
                        print(f"⚠️ Skipping corrupted metadata file: {metadata_path} - {e}")
                        continue
        
        # Sort by upload timestamp (newest first)
        uploads.sort(key=lambda x: x.get("upload_timestamp", ""), reverse=True)
        
        response_content = {
            "uploads": uploads,
            "total_count": len(uploads)
        }
        
        if corrupted_files:
            response_content["warning"] = f"Skipped {len(corrupted_files)} corrupted files"
            response_content["corrupted_files"] = corrupted_files
        
        return JSONResponse(
            status_code=200,
            content=response_content
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list uploads: {str(e)}"
        )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
