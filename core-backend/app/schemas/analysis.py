"""
Pydantic schemas for AI analysis API.

This module defines request and response models for the AI analysis endpoints.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
from pydantic import BaseModel, Field


class AnalysisRequest(BaseModel):
    """Request model for document analysis."""
    file_name: str = Field(..., description="Name of the file to analyze")
    query: str = Field(..., description="User's analysis query")
    user_id: int = Field(..., description="ID of the user requesting analysis")
    options: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional analysis options")


class AnalysisResponse(BaseModel):
    """Response model for document analysis."""
    success: bool = Field(..., description="Whether analysis was successful")
    file_name: str = Field(..., description="Name of the analyzed file")
    query: str = Field(..., description="Original query")
    results: Dict[str, str] = Field(..., description="Analysis results by component")
    error: Optional[str] = Field(None, description="Error message if analysis failed")


class AnalysisHistoryRecord(BaseModel):
    """Model for analysis history record."""
    id: int = Field(..., description="Analysis ID")
    file_id: int = Field(..., description="Associated file ID")
    query: str = Field(..., description="Analysis query")
    created_at: str = Field(..., description="Analysis creation timestamp")
    status: str = Field(..., description="Analysis status")


class AnalysisHistoryResponse(BaseModel):
    """Response model for analysis history."""
    analyses: List[AnalysisHistoryRecord] = Field(..., description="List of analysis records")
    total: int = Field(..., description="Total number of records")
    page: int = Field(..., description="Current page number")
    page_size: int = Field(..., description="Number of records per page")


class AnalysisStatusResponse(BaseModel):
    """Response model for analysis status."""
    id: int = Field(..., description="Analysis ID")
    status: str = Field(..., description="Current status")
    progress: int = Field(..., description="Progress percentage (0-100)")
    estimated_time_remaining: int = Field(..., description="Estimated time remaining in seconds")


class FileValidationResponse(BaseModel):
    """Response model for file validation."""
    valid: bool = Field(..., description="Whether file is valid for analysis")
    reason: Optional[str] = Field(None, description="Reason for validation result")
    file_info: Optional[Dict[str, Any]] = Field(None, description="File information if valid")


class AnalysisMetricsResponse(BaseModel):
    """Response model for analysis metrics."""
    total_analyses: int = Field(..., description="Total number of analyses")
    successful_analyses: int = Field(..., description="Number of successful analyses")
    failed_analyses: int = Field(..., description="Number of failed analyses")
    average_processing_time: int = Field(..., description="Average processing time in seconds")
    most_analyzed_file_type: str = Field(..., description="Most common file type analyzed")
    analysis_trends: Dict[str, int] = Field(..., description="Analysis trends by time period")


class BatchAnalysisRequest(BaseModel):
    """Request model for batch analysis."""
    file_ids: List[int] = Field(..., description="List of file IDs to analyze")
    queries: List[str] = Field(..., description="List of queries for each file")
    user_id: int = Field(..., description="ID of the user requesting batch analysis")
    options: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional batch options")


class BatchAnalysisResponse(BaseModel):
    """Response model for batch analysis."""
    success: bool = Field(..., description="Whether batch analysis was initiated successfully")
    batch_id: str = Field(..., description="Unique batch ID")
    message: str = Field(..., description="Status message")
    estimated_completion_time: str = Field(..., description="Estimated completion timestamp")


class AnalysisCapabilitiesResponse(BaseModel):
    """Response model for analysis capabilities."""
    supported_file_types: List[str] = Field(..., description="Supported file extensions")
    analysis_types: List[str] = Field(..., description="Available analysis types")
    features: List[str] = Field(..., description="Available features")
    agents: List[Dict[str, str]] = Field(..., description="Available AI agents")


class AnalysisResultDetail(BaseModel):
    """Detailed analysis result model."""
    analysis_id: int = Field(..., description="Analysis ID")
    status: str = Field(..., description="Analysis status")
    results: Dict[str, str] = Field(..., description="Detailed results by component")
    metadata: Dict[str, Any] = Field(..., description="Analysis metadata")


class AnalysisErrorResponse(BaseModel):
    """Error response model for analysis failures."""
    success: bool = Field(False, description="Always false for errors")
    error: str = Field(..., description="Error message")
    error_code: Optional[str] = Field(None, description="Error code")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional error details")


class AnalysisProgressResponse(BaseModel):
    """Response model for analysis progress."""
    analysis_id: int = Field(..., description="Analysis ID")
    status: str = Field(..., description="Current status")
    progress: int = Field(..., description="Progress percentage")
    current_step: Optional[str] = Field(None, description="Current processing step")
    estimated_time_remaining: Optional[int] = Field(None, description="Estimated time remaining")


class AnalysisConfiguration(BaseModel):
    """Configuration model for analysis settings."""
    model: str = Field("gpt-3.5-turbo", description="AI model to use")
    temperature: float = Field(0.7, description="Model temperature")
    max_tokens: int = Field(2000, description="Maximum tokens per response")
    timeout: int = Field(300, description="Analysis timeout in seconds")
    enable_fallback: bool = Field(True, description="Enable fallback mechanisms")


class AnalysisWebhookRequest(BaseModel):
    """Request model for analysis webhook."""
    analysis_id: int = Field(..., description="Analysis ID")
    status: str = Field(..., description="Analysis status")
    results: Optional[Dict[str, Any]] = Field(None, description="Analysis results")
    error: Optional[str] = Field(None, description="Error message if failed")


class AnalysisExportRequest(BaseModel):
    """Request model for analysis export."""
    analysis_id: int = Field(..., description="Analysis ID to export")
    format: str = Field("json", description="Export format (json, pdf, csv)")
    include_metadata: bool = Field(True, description="Include metadata in export")
    user_id: int = Field(..., description="Requesting user ID")


class AnalysisExportResponse(BaseModel):
    """Response model for analysis export."""
    success: bool = Field(..., description="Whether export was successful")
    export_id: str = Field(..., description="Export ID")
    download_url: Optional[str] = Field(None, description="Download URL for export")
    expires_at: str = Field(..., description="Export expiration timestamp")


class AnalysisFeedbackRequest(BaseModel):
    """Request model for analysis feedback."""
    analysis_id: int = Field(..., description="Analysis ID")
    rating: int = Field(..., ge=1, le=5, description="Rating from 1-5")
    feedback: Optional[str] = Field(None, description="User feedback")
    user_id: int = Field(..., description="User providing feedback")


class AnalysisFeedbackResponse(BaseModel):
    """Response model for analysis feedback."""
    success: bool = Field(..., description="Whether feedback was recorded")
    message: str = Field(..., description="Feedback response message")


class AnalysisSearchRequest(BaseModel):
    """Request model for searching analyses."""
    query: str = Field(..., description="Search query")
    user_id: int = Field(..., description="User ID")
    filters: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Search filters")
    limit: int = Field(10, ge=1, le=100, description="Maximum results to return")


class AnalysisSearchResponse(BaseModel):
    """Response model for analysis search."""
    analyses: List[AnalysisHistoryRecord] = Field(..., description="Matching analyses")
    total: int = Field(..., description="Total matching records")
    query: str = Field(..., description="Original search query")
