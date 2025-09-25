"""FastAPI app entrypoint and Crew orchestration for analysis workflows."""

from crewai import Crew, Process
from fastapi import FastAPI, File, UploadFile, Form, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
import os
import uuid
import time

from agents import financial_analyst
from task import analyze_financial_document
from logging_config import get_logger, set_request_id, log_function_call

# Initialize logging
logger = get_logger(__name__)

app = FastAPI(
    title="Financial Document Analyzer",
    description="AI-powered financial document analysis with comprehensive logging",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


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
            'extra_fields': {
                'method': request.method,
                'url': str(request.url),
                'client_ip': request.client.host if request.client else 'unknown',
                'user_agent': request.headers.get('user-agent', 'unknown'),
                'request_id': request_id
            }
        }
    )
    
    try:
        response = await call_next(request)
        
        # Log successful response
        process_time = time.time() - start_time
        logger.info(
            f"Request completed: {request.method} {request.url.path} - {response.status_code}",
            extra={
                'extra_fields': {
                    'status_code': response.status_code,
                    'process_time_seconds': round(process_time, 3),
                    'request_id': request_id
                }
            }
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
                'extra_fields': {
                    'error_type': type(e).__name__,
                    'process_time_seconds': round(process_time, 3),
                    'request_id': request_id
                }
            },
            exc_info=True
        )
        raise


@log_function_call(logger)
def run_crew(query: str):
    """To run the whole crew"""
    logger.info("Starting financial analysis crew", extra={'extra_fields': {'query_length': len(query)}})
    
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
        "version": "1.0.0"
    }


@app.get("/health")
async def health_check():
    """Detailed health check endpoint"""
    logger.debug("Detailed health check requested")
    
    health_status = {
        "status": "healthy",
        "timestamp": time.time(),
        "version": "1.0.0",
        "components": {
            "api": "healthy",
            "logging": "healthy",
            "crew_ai": "healthy"
        }
    }
    
    return health_status


@app.post("/analyze")
async def analyse_financial_document(
    file: UploadFile = File(...),
    query: str = Form(
        default="Analyze this financial document for investment insights"
    ),
):
    """Analyze financial document and provide comprehensive investment recommendations"""

    file_id = str(uuid.uuid4())
    file_path = f"data/financial_document_{file_id}.pdf"
    
    logger.info(
        "Document analysis requested",
        extra={
            'extra_fields': {
                'filename': file.filename,
                'file_size': file.size if hasattr(file, 'size') else 'unknown',
                'content_type': file.content_type,
                'file_id': file_id,
                'query_length': len(query) if query else 0
            }
        }
    )

    try:
        # Ensure data directory exists
        os.makedirs("data", exist_ok=True)
        logger.debug(f"Data directory ensured, saving file to: {file_path}")

        # Save uploaded file
        with open(file_path, "wb") as f:
            content = await file.read()
            f.write(content)
            
        logger.info(
            f"File saved successfully: {len(content)} bytes",
            extra={'extra_fields': {'file_size_bytes': len(content)}}
        )

        # Validate query
        if query == "" or query is None:
            query = "Analyze this financial document for investment insights"
            logger.debug("Using default query as none provided")

        # Process the financial document with all analysts
        logger.info("Starting document analysis with crew")
        response = run_crew(query=query.strip())

        logger.info(
            "Document analysis completed successfully",
            extra={
                'extra_fields': {
                    'response_length': len(str(response)),
                    'filename': file.filename
                }
            }
        )

        return {
            "status": "success",
            "query": query,
            "analysis": str(response),
            "file_processed": file.filename,
            "file_id": file_id
        }

    except Exception as e:
        logger.error(
            f"Error processing financial document: {str(e)}",
            extra={
                'extra_fields': {
                    'filename': file.filename,
                    'file_id': file_id,
                    'error_type': type(e).__name__
                }
            },
            exc_info=True
        )
        raise HTTPException(
            status_code=500, 
            detail=f"Error processing financial document: {str(e)}"
        ) from e

    finally:
        # Clean up uploaded file
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
                logger.debug(f"Cleaned up temporary file: {file_path}")
            except OSError as cleanup_error:
                logger.warning(f"Failed to cleanup temporary file {file_path}: {cleanup_error}")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
