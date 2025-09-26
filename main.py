"""FastAPI app entrypoint and Crew orchestration for analysis workflows."""

from crewai import Crew, Process
from fastapi import FastAPI, File, UploadFile, Form, HTTPException, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
import os
import uuid
import time

from agents import financial_analyst
from task import analyze_financial_document
from logging_config import get_logger, set_request_id, log_function_call

# Import authentication and security modules
from config import settings
from models import get_db, init_db
from auth import router as auth_router
from dependencies import (
    get_current_active_user,
    require_viewer,
    require_analyst,
    rate_limit,
    upload_rate_limit,
    audit_log,
    get_request_context,
)
from security import security_utils
from schemas import AnalysisRequest, AnalysisResponse, DocumentResponse

# Initialize logging
logger = get_logger(__name__)

app = FastAPI(
    title="Financial Document Analyzer",
    description="AI-powered financial document analysis with comprehensive logging and enterprise authentication",
    version="1.0.0",
    docs_url=f"{settings.API_V1_PREFIX}/docs",
    redoc_url=f"{settings.API_V1_PREFIX}/redoc",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include authentication router
app.include_router(auth_router)


@app.middleware("http")
async def logging_middleware(request: Request, call_next):
    """Add request logging and timing."""
    start_time = time.time()

    # Set request ID for tracing
    request_id = set_request_id()

    # Log request start
    logger.info(
        f"Request started: {request.method} {request.url.path}",
        extra={
            "extra_fields": {
                "method": request.method,
                "url": str(request.url),
                "client_ip": request.client.host if request.client else "unknown",
                "user_agent": request.headers.get("user-agent", "unknown"),
                "request_id": request_id,
            }
        },
    )

    try:
        response = await call_next(request)

        # Log successful response
        process_time = time.time() - start_time
        logger.info(
            f"Request completed: {request.method} {request.url.path} - {response.status_code}",
            extra={
                "extra_fields": {
                    "status_code": response.status_code,
                    "process_time_seconds": round(process_time, 3),
                    "request_id": request_id,
                }
            },
        )

        # Add request ID to response headers
        response.headers["X-Request-ID"] = request_id
        return response

    except Exception as e:
        # Log error response
        process_time = time.time() - start_time
        logger.error(
            f"Request failed: {request.method} {request.url.path} - {str(e)}",
            extra={
                "extra_fields": {
                    "error_type": type(e).__name__,
                    "process_time_seconds": round(process_time, 3),
                    "request_id": request_id,
                }
            },
            exc_info=True,
        )
        raise


@log_function_call(logger)
def run_crew(query: str):
    """To run the whole crew"""
    logger.info(
        "Starting financial analysis crew",
        extra={"extra_fields": {"query_length": len(query)}},
    )

    try:
        financial_crew = Crew(
            agents=[financial_analyst],
            tasks=[analyze_financial_document],
            process=Process.sequential,
        )

        logger.debug("Crew initialized successfully")
        result = financial_crew.kickoff({"query": query})

        logger.info("Financial analysis completed successfully")
        return result

    except Exception as e:
        logger.error(f"Error in crew execution: {str(e)}", exc_info=True)
        raise


@app.get("/")
async def root():
    """Health check endpoint"""
    logger.info("Health check requested")
    return {
        "message": "Financial Document Analyzer API is running",
        "status": "healthy",
        "version": "1.0.0",
        "api_prefix": settings.API_V1_PREFIX,
    }


@app.get("/health")
async def health_check():
    """Detailed health check endpoint"""
    logger.debug("Detailed health check requested")

    # Check database health
    from database import check_database_health

    db_health = await check_database_health()

    health_status = {
        "status": "healthy" if db_health["status"] == "healthy" else "degraded",
        "timestamp": time.time(),
        "version": "1.0.0",
        "components": {
            "api": "healthy",
            "logging": "healthy",
            "crew_ai": "healthy",
            "database": db_health["status"],
            "authentication": "healthy",
        },
        "database_details": db_health if db_health["status"] != "healthy" else None,
    }

    return health_status


@app.post(f"{settings.API_V1_PREFIX}/analyze", response_model=AnalysisResponse)
async def analyse_financial_document(
    file: UploadFile = File(...),
    query: str = Form(
        default="Analyze this financial document for investment insights"
    ),
    current_user=Depends(require_analyst),
    db=Depends(get_db),
    request_context: dict = Depends(get_request_context),
    _: None = Depends(upload_rate_limit),
):
    """Analyze financial document and provide comprehensive investment recommendations"""

    from models import Document, Analysis
    from sqlalchemy import select

    file_id = str(uuid.uuid4())
    file_path = f"{settings.UPLOAD_DIR}/financial_document_{file_id}.pdf"

    logger.info(
        "Document analysis requested",
        extra={
            "extra_fields": {
                "filename": file.filename,
                "file_size": file.size if hasattr(file, "size") else "unknown",
                "content_type": file.content_type,
                "file_id": file_id,
                "query_length": len(query) if query else 0,
                "user_id": str(current_user.id),
            }
        },
    )

    try:
        # Validate file
        if not security_utils.validate_file_extension(file.filename):
            raise HTTPException(
                status_code=400,
                detail=f"File type not allowed. Allowed types: {', '.join(settings.ALLOWED_UPLOAD_EXTENSIONS)}",
            )

        # Read file content
        content = await file.read()

        if not security_utils.validate_file_size(len(content)):
            raise HTTPException(
                status_code=413,
                detail=f"File too large. Maximum size: {settings.MAX_UPLOAD_SIZE} bytes",
            )

        # Ensure upload directory exists
        os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
        logger.debug(f"Upload directory ensured, saving file to: {file_path}")

        # Save uploaded file
        with open(file_path, "wb") as f:
            f.write(content)

        logger.info(
            f"File saved successfully: {len(content)} bytes",
            extra={"extra_fields": {"file_size_bytes": len(content)}},
        )

        # Generate file hash
        file_hash = security_utils.generate_file_hash(content)

        # Check if file already exists (deduplication)
        existing_doc_query = select(Document).where(Document.sha256_hash == file_hash)
        existing_doc_result = await db.execute(existing_doc_query)
        existing_doc = existing_doc_result.scalar_one_or_none()

        if existing_doc:
            logger.info(
                f"File already exists, using existing document: {existing_doc.id}"
            )
            document = existing_doc
        else:
            # Create document record
            document = Document(
                user_id=current_user.id,
                filename=file.filename,
                original_filename=file.filename,
                content_type=file.content_type,
                file_size=len(content),
                file_path=file_path,
                sha256_hash=file_hash,
                is_processed=False,
                processing_status="pending",
            )
            db.add(document)
            await db.commit()
            await db.refresh(document)

        # Validate query
        if query == "" or query is None:
            query = "Analyze this financial document for investment insights"
            logger.debug("Using default query as none provided")

        # Process the financial document with all analysts
        logger.info("Starting document analysis with crew")
        start_time = time.time()

        response = run_crew(query=query.strip())

        processing_time = int(time.time() - start_time)

        logger.info(
            "Document analysis completed successfully",
            extra={
                "extra_fields": {
                    "response_length": len(str(response)),
                    "filename": file.filename,
                    "processing_time_seconds": processing_time,
                }
            },
        )

        # Create analysis record
        analysis = Analysis(
            user_id=current_user.id,
            document_id=document.id,
            query=query,
            analysis_result=str(response),
            confidence_score=85,  # Default confidence score
            analysis_type="financial",
            status="completed",
            processing_time_seconds=processing_time,
        )
        db.add(analysis)

        # Update document status
        document.is_processed = True
        document.processing_status = "completed"

        await db.commit()
        await db.refresh(analysis)

        # Audit log
        await audit_log(
            action="document_analyzed",
            resource_type="analysis",
            resource_id=str(analysis.id),
            details=f"Document analyzed: {file.filename}",
            current_user=current_user,
            request_context=request_context,
            db=db,
        )

        return AnalysisResponse(
            id=analysis.id,
            query=analysis.query,
            analysis_result=analysis.analysis_result,
            confidence_score=analysis.confidence_score,
            analysis_type=analysis.analysis_type,
            status=analysis.status,
            processing_time_seconds=analysis.processing_time_seconds,
            created_at=analysis.created_at,
            document_id=analysis.document_id,
            user_id=analysis.user_id,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Error processing financial document: {str(e)}",
            extra={
                "extra_fields": {
                    "filename": file.filename,
                    "file_id": file_id,
                    "error_type": type(e).__name__,
                    "user_id": str(current_user.id),
                }
            },
            exc_info=True,
        )

        # Audit log for error
        await audit_log(
            action="document_analysis_failed",
            resource_type="analysis",
            details=f"Document analysis failed: {file.filename} - {str(e)}",
            current_user=current_user,
            request_context=request_context,
            db=db,
        )

        raise HTTPException(
            status_code=500, detail=f"Error processing financial document: {str(e)}"
        ) from e

    finally:
        # Clean up uploaded file
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
                logger.debug(f"Cleaned up temporary file: {file_path}")
            except OSError as cleanup_error:
                logger.warning(
                    f"Failed to cleanup temporary file {file_path}: {cleanup_error}"
                )


@app.on_event("startup")
async def startup_event():
    """Initialize database and other startup tasks."""
    logger.info("Starting up Financial Document Analyzer API")

    try:
        # Initialize database
        await init_db()
        logger.info("Database initialized successfully")

        # Initialize Redis connection
        from dependencies import get_redis

        await get_redis()
        logger.info("Redis connection established")

        logger.info("Startup completed successfully")
    except Exception as e:
        logger.error(f"Startup failed: {str(e)}", exc_info=True)
        raise


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup tasks on shutdown."""
    logger.info("Shutting down Financial Document Analyzer API")

    try:
        # Close Redis connection
        from dependencies import redis_client

        if redis_client:
            await redis_client.close()
            logger.info("Redis connection closed")

        logger.info("Shutdown completed successfully")
    except Exception as e:
        logger.error(f"Shutdown error: {str(e)}", exc_info=True)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
