"""
Pydantic schemas for AI analysis API.

This module defines request and response models for the AI analysis endpoints.
"""

from typing import Dict, Any, List, Optional, Union, Literal
from datetime import datetime, date
from enum import Enum
from pydantic import BaseModel, Field, validator


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


class TimePeriod(str, Enum):
    """Time period for financial data."""
    QUARTERLY = "quarterly"
    YEARLY = "yearly"


class FinancialMetricType(str, Enum):
    """Type of financial metric."""
    REVENUE = "revenue"
    EPS = "eps"
    GROSS_MARGIN = "gross_margin"
    OPERATING_MARGIN = "operating_margin"
    NET_INCOME = "net_income"
    EBITDA = "ebitda"


class FinancialMetricData(BaseModel):
    """Financial metric data point."""
    period: str = Field(..., description="Time period identifier, e.g., 'Q1 2023' or '2023'")
    value: float = Field(..., description="Metric value")
    previous_value: Optional[float] = Field(None, description="Previous period value for comparison")
    yoy_change: Optional[float] = Field(None, description="Year-over-year change percentage")
    qoq_change: Optional[float] = Field(None, description="Quarter-over-quarter change percentage")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")


class FinancialAnalysisCreate(BaseModel):
    """Request model for creating a financial analysis."""
    file_id: int = Field(..., description="ID of the analyzed file")
    analysis_type: str = Field(..., description="Type of analysis (e.g., 'revenue', 'eps', 'comparative')")
    title: str = Field(..., description="Title of the analysis")
    description: Optional[str] = Field(None, description="Description of the analysis")
    data: Dict[str, Any] = Field(..., description="Analysis data in a structured format")


class FinancialAnalysisResponse(FinancialAnalysisCreate):
    """Response model for financial analysis."""
    id: int = Field(..., description="Analysis ID")
    user_id: int = Field(..., description="ID of the user who created the analysis")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: Optional[datetime] = Field(None, description="Last update timestamp")

    class Config:
        orm_mode = True


class RevenueTrendsRequest(BaseModel):
    """Request model for revenue trends analysis."""
    file_id: int = Field(..., description="ID of the file to analyze")
    time_period: TimePeriod = Field(TimePeriod.QUARTERLY, description="Time period for the analysis")
    segments: Optional[List[str]] = Field(None, description="Segments to include (e.g., product lines, geographies)")
    start_date: Optional[date] = Field(None, description="Start date for the analysis")
    end_date: Optional[date] = Field(None, description="End date for the analysis")


class RevenueTrendsResponse(BaseModel):
    """Response model for revenue trends analysis."""
    analysis_id: int = Field(..., description="ID of the created analysis")
    time_period: TimePeriod = Field(..., description="Time period used for the analysis")
    metrics: List[FinancialMetricData] = Field(..., description="Revenue metrics over time")
    segments: Optional[Dict[str, List[FinancialMetricData]]] = Field(
        None, 
        description="Revenue by segment if segments were specified"
    )
    total_growth: Optional[float] = Field(None, description="Total growth percentage over the period")
    cagr: Optional[float] = Field(None, description="Compound Annual Growth Rate")


class EPSAnalysisRequest(BaseModel):
    """Request model for EPS analysis."""
    file_id: int = Field(..., description="ID of the file to analyze")
    time_period: TimePeriod = Field(TimePeriod.QUARTERLY, description="Time period for the analysis")
    include_guidance: bool = Field(True, description="Whether to include guidance data if available")
    compare_to_analyst_expectations: bool = Field(
        False, 
        description="Whether to compare with analyst expectations if available"
    )


class EPSAnalysisResponse(BaseModel):
    """Response model for EPS analysis."""
    analysis_id: int = Field(..., description="ID of the created analysis")
    time_period: TimePeriod = Field(..., description="Time period used for the analysis")
    eps_metrics: List[FinancialMetricData] = Field(..., description="EPS metrics over time")
    guidance: Optional[List[Dict[str, Any]]] = Field(
        None, 
        description="Guidance data if available and requested"
    )
    analyst_expectations: Optional[List[Dict[str, Any]]] = Field(
        None, 
        description="Analyst expectations if available and requested"
    )


class ComparativeAnalysisRequest(BaseModel):
    """Request model for comparative analysis."""
    file_id: int = Field(..., description="ID of the file to analyze")
    metrics: List[FinancialMetricType] = Field(
        default_factory=lambda: [
            FinancialMetricType.REVENUE, 
            FinancialMetricType.EPS, 
            FinancialMetricType.GROSS_MARGIN
        ],
        description="Metrics to include in the analysis"
    )
    time_period: TimePeriod = Field(TimePeriod.YEARLY, description="Time period for the analysis")
    include_percent_change: bool = Field(True, description="Whether to include percentage changes")


class ComparativeAnalysisResponse(BaseModel):
    """Response model for comparative analysis."""
    analysis_id: int = Field(..., description="ID of the created analysis")
    time_period: TimePeriod = Field(..., description="Time period used for the analysis")
    metrics: Dict[FinancialMetricType, List[FinancialMetricData]] = Field(
        ..., 
        description="Metrics data organized by metric type"
    )
    heatmap_data: Optional[Dict[str, Any]] = Field(
        None,
        description="Formatted data for heatmap visualization"
    )


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
