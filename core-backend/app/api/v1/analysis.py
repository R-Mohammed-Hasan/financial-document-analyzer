"""
AI Analysis API router.

This module defines AI analysis endpoints for financial document processing
using CrewAI agents and tasks.
"""

from typing import Dict, Any, List
from fastapi import APIRouter, Depends, HTTPException, status, Query, BackgroundTasks, Body
from sqlalchemy.ext.asyncio import AsyncSession
from core.dependencies import get_current_user
from db.session import get_async_db
from services.analysis_service import AnalysisService
from services.financial_analysis_service import FinancialAnalysisService
from schemas.analysis import (
    FinancialAnalysisCreate,
    FinancialAnalysisResponse,
    RevenueTrendsRequest,
    RevenueTrendsResponse,
    EPSAnalysisRequest,
    EPSAnalysisResponse,
    ComparativeAnalysisRequest,
    ComparativeAnalysisResponse,
    TimePeriod
)
from schemas.analysis import (
    AnalysisRequest,
    AnalysisResponse,
    AnalysisHistoryResponse,
    AnalysisStatusResponse,
    FileValidationResponse,
    AnalysisMetricsResponse,
)
from db.models.user import User

router = APIRouter()


@router.post("/analysis/analyze", response_model=AnalysisResponse)
async def analyze_document(
    request: AnalysisRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
) -> AnalysisResponse:
    """
    Perform AI analysis on a financial document in the background.

    Args:
        request: Analysis request with file_name and query
        background_tasks: Background tasks for async processing
        db: Database session

    Returns:
        AnalysisResponse indicating analysis has started
    """
    analysis_service = AnalysisService(db)

    # Check if file exists
    file = await analysis_service._get_file_by_name(request.file_name, current_user.id)
    if not file:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="File not found"
        )

    # Start background analysis
    background_tasks.add_task(
        analysis_service.analyze_document,
        request.file_name,
        request.query,
        current_user.id,
    )

    # Return immediate success
    return AnalysisResponse(
        success=True,
        file_name=request.file_name,
        query=request.query,
        results={},
        error=None,
    )


@router.get("/analysis/history", response_model=AnalysisHistoryResponse)
async def get_analysis_history(
    user_id: int = Query(..., description="User ID"),
    limit: int = Query(10, ge=1, le=100, description="Number of records to return"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    db: AsyncSession = Depends(get_async_db),
) -> AnalysisHistoryResponse:
    """
    Get user's analysis history.

    Args:
        user_id: User ID
        limit: Maximum number of records to return
        skip: Number of records to skip
        db: Database session

    Returns:
        AnalysisHistoryResponse with analysis history
    """
    analysis_service = AnalysisService(db)
    history = await analysis_service.get_analysis_history(user_id, limit + skip)

    return AnalysisHistoryResponse(
        analyses=history[skip : skip + limit],
        total=len(history),
        page=skip // limit + 1,
        page_size=limit,
    )


@router.get("/analysis/{analysis_id}/status", response_model=AnalysisStatusResponse)
async def get_analysis_status(
    analysis_id: int, db: AsyncSession = Depends(get_async_db)
) -> AnalysisStatusResponse:
    """
    Get the status of a specific analysis.

    Args:
        analysis_id: Analysis ID
        db: Database session

    Returns:
        AnalysisStatusResponse with analysis status
    """
    analysis_service = AnalysisService(db)
    status_info = await analysis_service.get_analysis_status(analysis_id)

    return AnalysisStatusResponse(**status_info)


@router.post("/analysis/{analysis_id}/cancel")
async def cancel_analysis(
    analysis_id: int,
    user_id: int = Query(..., description="User ID"),
    db: AsyncSession = Depends(get_async_db),
) -> Dict[str, Any]:
    """
    Cancel a running analysis.

    Args:
        analysis_id: Analysis ID
        user_id: User ID
        db: Database session

    Returns:
        Dict with cancellation result
    """
    analysis_service = AnalysisService(db)
    result = await analysis_service.cancel_analysis(analysis_id, user_id)

    if not result["success"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=result["message"]
        )

    return result


@router.get("/analysis/supported-types", response_model=List[str])
async def get_supported_file_types(
    db: AsyncSession = Depends(get_async_db),
) -> List[str]:
    """
    Get list of supported file types for analysis.

    Args:
        db: Database session

    Returns:
        List of supported file extensions
    """
    analysis_service = AnalysisService(db)
    return await analysis_service.get_supported_file_types()


@router.post("/analysis/validate-file", response_model=FileValidationResponse)
async def validate_file_for_analysis(
    file_name: str = Query(..., description="File name"),
    user_id: int = Query(..., description="User ID"),
    db: AsyncSession = Depends(get_async_db),
) -> FileValidationResponse:
    """
    Validate if a file can be analyzed.

    Args:
        file_name: File name
        user_id: User ID
        db: Database session

    Returns:
        FileValidationResponse with validation result
    """
    analysis_service = AnalysisService(db)
    validation = await analysis_service.validate_file_for_analysis(file_name, user_id)

    return FileValidationResponse(**validation)


@router.get("/analysis/metrics", response_model=AnalysisMetricsResponse)
async def get_analysis_metrics(
    user_id: int = Query(..., description="User ID"),
    db: AsyncSession = Depends(get_async_db),
) -> AnalysisMetricsResponse:
    """
    Get analysis metrics for a user.

    Args:
        user_id: User ID
        db: Database session

    Returns:
        AnalysisMetricsResponse with analysis metrics
    """
    analysis_service = AnalysisService(db)
    metrics = await analysis_service.get_analysis_metrics(user_id)

    return AnalysisMetricsResponse(**metrics)


@router.get("/analysis/capabilities", response_model=Dict[str, Any])
async def get_analysis_capabilities() -> Dict[str, Any]:
    """
    Get AI analysis capabilities information.

    Returns:
        Dict with analysis capabilities
    """
    return {
        "supported_file_types": [".pdf", ".docx", ".xlsx", ".csv", ".txt"],
        "analysis_types": [
            "financial_analysis",
            "investment_analysis",
            "risk_assessment",
            "document_verification",
        ],
        "features": [
            "Multi-agent analysis",
            "Sequential processing",
            "Error handling and fallbacks",
            "Progress tracking",
            "Analysis history",
        ],
        "agents": [
            {
                "name": "Financial Analyst",
                "description": "Performs comprehensive financial analysis and extracts key metrics",
            },
            {
                "name": "Document Verifier",
                "description": "Validates document type and summarizes key sections",
            },
            {
                "name": "Investment Advisor",
                "description": "Provides investment implications and recommendations",
            },
            {
                "name": "Risk Assessor",
                "description": "Identifies and assesses material risks",
            },
        ],
    }


@router.post("/analysis/batch", response_model=Dict[str, Any])
async def batch_analysis(
    request: Dict[str, Any],  # BatchAnalysisRequest schema
    db: AsyncSession = Depends(get_async_db),
) -> Dict[str, Any]:
    """
    Perform batch analysis on multiple files.

    Args:
        request: Batch analysis request
        db: Database session

    Returns:
        Dict with batch analysis results
    """
    # Mock implementation - replace with actual batch processing
    return {
        "success": True,
        "message": "Batch analysis initiated",
        "batch_id": "batch_123",
        "estimated_completion_time": "2023-12-01T12:00:00",
    }


@router.get("/analysis/{analysis_id}/results", response_model=Dict[str, Any])
async def get_analysis_results(
    analysis_id: int,
    user_id: int = Query(..., description="User ID"),
    db: AsyncSession = Depends(get_async_db),
) -> Dict[str, Any]:
    """
    Get detailed results of a specific analysis.

    Args:
        analysis_id: Analysis ID
        user_id: User ID
        db: Database session

    Returns:
        Dict with detailed analysis results
    """
    # Mock implementation - replace with actual results retrieval
    return {
        "analysis_id": analysis_id,
        "status": "completed",
        "results": {
            "verification": "Document verified as financial report",
            "financial_analysis": "Revenue growth of 15% with improved margins",
            "investment_analysis": "Positive outlook with strong fundamentals",
            "risk_assessment": "Moderate risk with good mitigation strategies",
        },
        "metadata": {
            "processing_time": 45,
            "tokens_used": 1200,
            "model_used": "gpt-3.5-turbo",
        },
    }
