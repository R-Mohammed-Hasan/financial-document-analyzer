"""
Financial Analysis Service.

This module provides business logic for financial analysis operations.
"""

from typing import List, Dict, Any, Optional, Union
from datetime import datetime, date
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_
import json
import logging

from db.models.analysis import FinancialAnalysis, FinancialMetric
from db.models.file import File
from db.models.user import User
from schemas.analysis import (
    FinancialAnalysisCreate,
    RevenueTrendsRequest,
    RevenueTrendsResponse,
    EPSAnalysisRequest,
    EPSAnalysisResponse,
    ComparativeAnalysisRequest,
    ComparativeAnalysisResponse,
    FinancialMetricData,
    TimePeriod,
    FinancialMetricType
)
from core.logging_config import get_logger

logger = get_logger(__name__)

class FinancialAnalysisService:
    """Service class for financial analysis operations."""

    def __init__(self, db: AsyncSession):
        """Initialize the service with a database session."""
        self.db = db

    async def create_analysis(
        self, analysis_data: FinancialAnalysisCreate, user_id: int
    ) -> FinancialAnalysis:
        """
        Create a new financial analysis.

        Args:
            analysis_data: Analysis data
            user_id: ID of the user creating the analysis

        Returns:
            The created FinancialAnalysis instance
        """
        try:
            # Create the analysis record
            analysis = FinancialAnalysis(
                file_id=analysis_data.file_id,
                user_id=user_id,
                analysis_type=analysis_data.analysis_type,
                title=analysis_data.title,
                description=analysis_data.description,
                data=analysis_data.data
            )
            
            self.db.add(analysis)
            await self.db.commit()
            await self.db.refresh(analysis)
            
            logger.info(f"Created financial analysis with ID {analysis.id}")
            return analysis
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Failed to create financial analysis: {str(e)}", exc_info=True)
            raise

    async def get_analysis_by_id(
        self, analysis_id: int, user_id: int
    ) -> Optional[FinancialAnalysis]:
        """
        Get a financial analysis by ID.

        Args:
            analysis_id: ID of the analysis to retrieve
            user_id: ID of the user requesting the analysis

        Returns:
            The requested FinancialAnalysis or None if not found
        """
        result = await self.db.execute(
            select(FinancialAnalysis)
            .where(FinancialAnalysis.id == analysis_id)
            .where(FinancialAnalysis.user_id == user_id)
        )
        return result.scalars().first()

    async def get_analyses_by_file(
        self, file_id: int, user_id: int, limit: int = 100, offset: int = 0
    ) -> List[FinancialAnalysis]:
        """
        Get all analyses for a specific file.

        Args:
            file_id: ID of the file
            user_id: ID of the user
            limit: Maximum number of results to return
            offset: Number of results to skip

        Returns:
            List of FinancialAnalysis instances
        """
        result = await self.db.execute(
            select(FinancialAnalysis)
            .where(FinancialAnalysis.file_id == file_id)
            .where(FinancialAnalysis.user_id == user_id)
            .order_by(FinancialAnalysis.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        return result.scalars().all()

    async def analyze_revenue_trends(
        self, request: RevenueTrendsRequest, user_id: int
    ) -> RevenueTrendsResponse:
        """
        Analyze revenue trends from a financial document.
        
        This method extracts revenue data from the document, calculates trends,
        and returns a comprehensive analysis including YOY and QoQ changes.

        Args:
            request: Revenue trends analysis request
            user_id: ID of the user requesting the analysis

        Returns:
            RevenueTrendsResponse with analysis results
            
        Raises:
            HTTPException: If file is not found or not accessible
            ValueError: If the document format is not supported
        """
        try:
            # Get the file and verify access
            file = await self._get_file_for_analysis(request.file_id, user_id)
            
            # Extract financial data from the document
            financial_data = await self._extract_financial_data(file, 'revenue')
            
            # Process the data to calculate metrics
            metrics = self._calculate_revenue_metrics(
                financial_data, 
                request.time_period,
                request.start_date,
                request.end_date
            )
            
            # Calculate segment data if segments are requested
            segments_data = {}
            if request.segments:
                for segment in request.segments:
                    segment_data = await self._extract_segment_data(file, 'revenue', segment)
                    segments_data[segment] = self._calculate_segment_metrics(
                        segment_data,
                        request.time_period,
                        request.start_date,
                        request.end_date
                    )
            
            # Calculate overall growth metrics
            total_growth, cagr = self._calculate_growth_metrics(metrics)
            
            # Create the analysis record
            analysis = await self.create_analysis(
                FinancialAnalysisCreate(
                    file_id=request.file_id,
                    analysis_type="revenue_trends",
                    title=f"Revenue Trends Analysis - {file.original_filename}",
                    description=f"Revenue trends analysis for {file.original_filename}",
                    data={
                        "time_period": request.time_period,
                        "start_date": request.start_date.isoformat() if request.start_date else None,
                        "end_date": request.end_date.isoformat() if request.end_date else None,
                        "segments": request.segments,
                        "total_growth": total_growth,
                        "cagr": cagr
                    }
                ),
                user_id=user_id
            )
            
            # Store metrics in the database
            await self._store_metrics(analysis.id, metrics, segments_data)
            
            return RevenueTrendsResponse(
                analysis_id=analysis.id,
                time_period=request.time_period,
                metrics=metrics,
                segments=segments_data if segments_data else None,
                total_growth=total_growth,
                cagr=cagr
            )
            
        except Exception as e:
            logger.error(f"Error in analyze_revenue_trends: {str(e)}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to analyze revenue trends: {str(e)}"
            )

    async def analyze_eps(
        self, request: EPSAnalysisRequest, user_id: int
    ) -> EPSAnalysisResponse:
        """
        Analyze EPS (Earnings Per Share) data from financial documents.
        
        This method extracts EPS data, calculates growth rates, and compares against
        analyst estimates and company guidance.

        Args:
            request: EPS analysis request
            user_id: ID of the user requesting the analysis

        Returns:
            EPSAnalysisResponse with detailed EPS analysis
            
        Raises:
            HTTPException: If file is not found or analysis fails
        """
        try:
            # Get the file and verify access
            file = await self._get_file_for_analysis(request.file_id, user_id)
            
            # Extract EPS data from the document
            eps_data = await self._extract_financial_data(file, 'eps')
            
            # Process the data to calculate metrics
            metrics = self._calculate_eps_metrics(
                eps_data,
                request.time_period,
                include_estimates=request.include_estimates,
                include_guidance=request.include_guidance
            )
            
            # Calculate growth rates and other analytics
            growth_rates = self._calculate_growth_rates(metrics)
            
            # Create the analysis record
            analysis = await self.create_analysis(
                FinancialAnalysisCreate(
                    file_id=request.file_id,
                    analysis_type="eps_analysis",
                    title=f"EPS Analysis - {file.original_filename}",
                    description=f"Earnings Per Share analysis for {file.original_filename}",
                    data={
                        "time_period": request.time_period,
                        "include_estimates": request.include_estimates,
                        "include_guidance": request.include_guidance,
                        "growth_rates": growth_rates
                    }
                ),
                user_id=user_id
            )
            
            # Store metrics in the database
            await self._store_metrics(analysis.id, metrics, {})
            
            return EPSAnalysisResponse(
                analysis_id=analysis.id,
                metrics=metrics,
                growth_rates=growth_rates,
                beat_estimates=metrics[-1].get('beat_estimate', False) if metrics else False,
                met_guidance=metrics[-1].get('met_guidance', False) if metrics else False
            )
            
        except Exception as e:
            logger.error(f"Error in analyze_eps: {str(e)}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to analyze EPS data: {str(e)}"
            )
    
    async def analyze_comparative(
        self, request: ComparativeAnalysisRequest, user_id: int
    ) -> ComparativeAnalysisResponse:
        """
        Perform comparative analysis between financial documents.
        
        This method compares financial metrics across multiple documents or time periods
        to identify trends, anomalies, and relative performance.

        Args:
            request: Comparative analysis request
            user_id: ID of the user requesting the analysis

        Returns:
            ComparativeAnalysisResponse with comparison results
            
        Raises:
            HTTPException: If files are not found or analysis fails
        """
        try:
            # Verify all files exist and are accessible
            files = []
            for file_id in request.file_ids:
                file = await self._get_file_for_analysis(file_id, user_id)
                files.append(file)
            
            # Extract and compare financial data
            comparison_results = {}
            all_metrics = {}
            
            for file in files:
                file_metrics = {}
                for metric_type in request.metrics:
                    # Extract data for each requested metric
                    metric_data = await self._extract_financial_data(file, metric_type)
                    file_metrics[metric_type] = self._calculate_metrics(
                        metric_data,
                        request.time_period,
                        request.start_date,
                        request.end_date
                    )
                all_metrics[file.id] = file_metrics
            
            # Perform comparison
            comparison_results = self._compare_metrics(all_metrics, request.comparison_type)
            
            # Create the analysis record
            analysis = await self.create_analysis(
                FinancialAnalysisCreate(
                    file_id=request.file_ids[0],  # Primary file ID
                    analysis_type="comparative_analysis",
                    title=f"Comparative Analysis - {len(request.file_ids)} files",
                    description=f"Comparative analysis of {', '.join([f.original_filename for f in files])}",
                    data={
                        "time_period": request.time_period,
                        "metrics": request.metrics,
                        "comparison_type": request.comparison_type,
                        "file_ids": request.file_ids,
                        "start_date": request.start_date.isoformat() if request.start_date else None,
                        "end_date": request.end_date.isoformat() if request.end_date else None
                    }
                ),
                user_id=user_id
            )
            
            # Store metrics in the database
            await self._store_comparison_metrics(analysis.id, all_metrics, comparison_results)
            
            return ComparativeAnalysisResponse(
                analysis_id=analysis.id,
                metrics=comparison_results,
                time_period=request.time_period,
                comparison_type=request.comparison_type,
                file_ids=request.file_ids,
                file_names={file.id: file.original_filename for file in files}
            )
            
        except Exception as e:
            logger.error(f"Error in analyze_comparative: {str(e)}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to perform comparative analysis: {str(e)}"
            )
        
    async def _extract_financial_data(self, file: File, metric_type: str) -> Dict[str, Any]:
        """
        Extract financial data from a document for a specific metric type.
        
        Args:
            file: The file to extract data from
            metric_type: Type of metric to extract (e.g., 'revenue', 'eps')
            
        Returns:
            Dictionary containing the extracted financial data
            
        Raises:
            ValueError: If the file format is not supported
        """
        try:
            # In a real implementation, this would parse the document and extract the data
            # For now, we'll return a placeholder
            return {
                "metric_type": metric_type,
                "file_id": file.id,
                "extracted_data": []  # Placeholder for actual extracted data
            }
        except Exception as e:
            logger.error(f"Error extracting {metric_type} data: {str(e)}")
            raise ValueError(f"Failed to extract {metric_type} data: {str(e)}")
    
    def _calculate_revenue_metrics(
        self, 
        financial_data: Dict[str, Any],
        time_period: TimePeriod,
        start_date: date = None,
        end_date: date = None
    ) -> List[Dict[str, Any]]:
        """
        Calculate revenue metrics from extracted financial data.
        
        Args:
            financial_data: Raw financial data from document
            time_period: Time period for the analysis
            start_date: Optional start date filter
            end_date: Optional end date filter
            
        Returns:
            List of calculated revenue metrics
        """
        # In a real implementation, this would process the extracted data
        # and calculate the metrics based on the time period and date range
        return []
    
    def _calculate_eps_metrics(
        self,
        eps_data: Dict[str, Any],
        time_period: TimePeriod,
        include_estimates: bool = False,
        include_guidance: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Calculate EPS metrics from extracted EPS data.
        
        Args:
            eps_data: Raw EPS data from document
            time_period: Time period for the analysis
            include_estimates: Whether to include analyst estimates
            include_guidance: Whether to include company guidance
            
        Returns:
            List of calculated EPS metrics
        """
        # In a real implementation, this would process the extracted data
        # and calculate the metrics based on the time period and options
        return []
    
    def _calculate_growth_rates(self, metrics: List[Dict[str, Any]]) -> Dict[str, float]:
        """
        Calculate growth rates from a list of metrics.
        
        Args:
            metrics: List of metric data points
            
        Returns:
            Dictionary of growth rate calculations
        """
        if not metrics or len(metrics) < 2:
            return {}
            
        # Calculate various growth rates
        first = metrics[0]['value']
        last = metrics[-1]['value']
        num_periods = len(metrics)
        
        return {
            'absolute_growth': last - first,
            'percentage_growth': ((last - first) / abs(first)) * 100 if first != 0 else 0,
            'cagr': ((last / first) ** (1 / num_periods) - 1) * 100 if first != 0 else 0
        }
    
    def _compare_metrics(
        self, 
        all_metrics: Dict[int, Dict[str, List[Dict[str, Any]]]],
        comparison_type: str
    ) -> Dict[str, Any]:
        """
        Compare metrics across multiple files.
        
        Args:
            all_metrics: Dictionary mapping file IDs to their metrics
            comparison_type: Type of comparison to perform
            
        Returns:
            Dictionary with comparison results
        """
        comparison_results = {}
        
        # In a real implementation, this would perform the actual comparison
        # based on the comparison type (e.g., 'yoy', 'qoq', 'vs_peers')
        
        return comparison_results
    
    async def _store_metrics(
        self, 
        analysis_id: int, 
        metrics: List[Dict[str, Any]],
        segments_data: Dict[str, List[Dict[str, Any]]]
    ) -> None:
        """
        Store metrics in the database.
        
        Args:
            analysis_id: ID of the analysis
            metrics: List of metrics to store
            segments_data: Dictionary of segment data to store
        """
        try:
            # Store main metrics
            for metric in metrics:
                metric_record = FinancialMetric(
                    analysis_id=analysis_id,
                    metric_name=metric.get('metric_name', 'unknown'),
                    period=metric.get('period', ''),
                    value=metric.get('value', 0),
                    previous_value=metric.get('previous_value'),
                    yoy_change=metric.get('yoy_change'),
                    qoq_change=metric.get('qoq_change'),
                    metadata_=metric.get('metadata', {})
                )
                self.db.add(metric_record)
            
            # Store segment metrics
            for segment, segment_metrics in segments_data.items():
                for metric in segment_metrics:
                    metric_record = FinancialMetric(
                        analysis_id=analysis_id,
                        metric_name=f"{metric.get('metric_name', 'unknown')}_{segment}",
                        period=metric.get('period', ''),
                        value=metric.get('value', 0),
                        previous_value=metric.get('previous_value'),
                        yoy_change=metric.get('yoy_change'),
                        qoq_change=metric.get('qoq_change'),
                        metadata_={
                            **metric.get('metadata', {}),
                            'segment': segment,
                            'is_segment_metric': True
                        }
                    )
                    self.db.add(metric_record)
            
            await self.db.commit()
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Failed to store metrics: {str(e)}", exc_info=True)
            raise
    
    async def _store_comparison_metrics(
        self,
        analysis_id: int,
        all_metrics: Dict[int, Dict[str, List[Dict[str, Any]]]],
        comparison_results: Dict[str, Any]
    ) -> None:
        """
        Store comparison metrics in the database.
        
        Args:
            analysis_id: ID of the analysis
            all_metrics: Dictionary of metrics for each file
            comparison_results: Results of the comparison
        """
        try:
            # Store the comparison results as a single record
            comparison_metric = FinancialMetric(
                analysis_id=analysis_id,
                metric_name="comparison_summary",
                period="",
                value=0,  # No single value for comparison
                metadata_={
                    'comparison_results': comparison_results,
                    'compared_files': list(all_metrics.keys())
                }
            )
            self.db.add(comparison_metric)
            
            # Store individual metrics for each file
            for file_id, metrics in all_metrics.items():
                for metric_type, metric_list in metrics.items():
                    for metric in metric_list:
                        metric_record = FinancialMetric(
                            analysis_id=analysis_id,
                            metric_name=f"{metric_type}_file_{file_id}",
                            period=metric.get('period', ''),
                            value=metric.get('value', 0),
                            previous_value=metric.get('previous_value'),
                            yoy_change=metric.get('yoy_change'),
                            qoq_change=metric.get('qoq_change'),
                            metadata_={
                                **metric.get('metadata', {}),
                                'file_id': file_id,
                                'metric_type': metric_type,
                                'is_comparison_metric': True
                            }
                        )
                        self.db.add(metric_record)
            
            await self.db.commit()
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Failed to store comparison metrics: {str(e)}", exc_info=True)
            raise
    
    async def _get_file_for_analysis(self, file_id: int, user_id: int) -> File:
        """
        Get a file for analysis, verifying the user has access.
        
        Args:
            file_id: ID of the file to get
            user_id: ID of the user requesting access
            
        Returns:
            The requested File
            
        Raises:
            HTTPException: If the file is not found or access is denied
        """
        try:
            result = await self.db.execute(
                select(File).where(File.id == file_id, File.user_id == user_id)
            )
            file = result.scalars().first()
            
            if not file:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="File not found or access denied"
                )
                
            return file
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error getting file {file_id}: {str(e)}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to retrieve file"
            )
    # Add any additional helper methods or overrides as needed
    
    async def get_analysis_metrics(
        self,
        analysis_id: int,
        user_id: int,
        metric_type: str = None,
        period: str = None
    ) -> List[Dict[str, Any]]:
        """
        Get metrics for a specific analysis.
        
        Args:
            analysis_id: ID of the analysis
            user_id: ID of the user requesting the metrics
            metric_type: Optional filter by metric type
            period: Optional filter by period
            
        Returns:
            List of metric records
            
        Raises:
            HTTPException: If the analysis is not found or access is denied
        """
        try:
            # Verify the analysis exists and belongs to the user
            analysis = await self.get_analysis_by_id(analysis_id, user_id)
            if not analysis:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Analysis not found or access denied"
                )
            
            # Build the query
            query = select(FinancialMetric).where(
                FinancialMetric.analysis_id == analysis_id
            )
            
            if metric_type:
                query = query.where(FinancialMetric.metric_name.like(f"{metric_type}%"))
                
            if period:
                query = query.where(FinancialMetric.period == period)
            
            # Execute the query
            result = await self.db.execute(query)
            metrics = result.scalars().all()
            
            # Convert to list of dicts for response
            return [
                {
                    "id": m.id,
                    "metric_name": m.metric_name,
                    "period": m.period,
                    "value": m.value,
                    "previous_value": m.previous_value,
                    "yoy_change": m.yoy_change,
                    "qoq_change": m.qoq_change,
                    "metadata": m.metadata_ or {}
                }
                for m in metrics
            ]
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error getting metrics: {str(e)}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to retrieve analysis metrics"
            )
    
    async def delete_analysis(self, analysis_id: int, user_id: int) -> bool:
        """
        Delete a financial analysis and its associated metrics.
        
        Args:
            analysis_id: ID of the analysis to delete
            user_id: ID of the user requesting the deletion
            
        Returns:
            True if deletion was successful, False otherwise
            
        Raises:
            HTTPException: If the analysis is not found or access is denied
        """
        try:
            # Verify the analysis exists and belongs to the user
            analysis = await self.get_analysis_by_id(analysis_id, user_id)
            if not analysis:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Analysis not found or access denied"
                )
            
            # Delete the analysis (cascading will handle the metrics)
            await self.db.delete(analysis)
            await self.db.commit()
            
            return True
            
        except HTTPException:
            await self.db.rollback()
            raise
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error deleting analysis: {str(e)}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to delete analysis"
            )
    # Add any final class-level documentation or methods here
    # ...

# End of FinancialAnalysisService class
    async def get_analysis_metrics(
        self, analysis_id: int, user_id: int
    ) -> Dict[str, Any]:
        """
        Get metrics for a specific analysis.

        Args:
            analysis_id: ID of the analysis
            user_id: ID of the user requesting the metrics

        Returns:
            Dictionary containing analysis metrics
            
        Raises:
            HTTPException: If the analysis is not found or access is denied
        """
        try:
            # Verify the analysis exists and belongs to the user
            analysis = await self.get_analysis_by_id(analysis_id, user_id)
            if not analysis:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Analysis not found or access denied"
                )
                
            # Get all metrics for this analysis
            result = await self.db.execute(
                select(FinancialMetric)
                .where(FinancialMetric.analysis_id == analysis_id)
                .order_by(FinancialMetric.period)
            )
            metrics = result.scalars().all()
            
            # Group metrics by metric name
            metrics_by_name = {}
            for metric in metrics:
                if metric.metric_name not in metrics_by_name:
                    metrics_by_name[metric.metric_name] = []
                metrics_by_name[metric.metric_name].append(metric)
            
            # Calculate summary statistics
            periods = sorted({m.period for m in metrics} - {None, ''})
            metric_types = list(metrics_by_name.keys())
            
            return {
                "analysis_id": analysis.id,
                "file_id": analysis.file_id,
                "analysis_type": analysis.analysis_type,
                "created_at": analysis.created_at.isoformat(),
                "metrics": {
                    "count": len(metrics),
                    "unique_metrics": len(metric_types),
                    "time_periods": len(periods),
                    "periods": periods,
                    "metric_types": metric_types,
                    "last_updated": analysis.updated_at.isoformat() if analysis.updated_at else analysis.created_at.isoformat()
                }
            }
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error getting analysis metrics: {str(e)}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to retrieve analysis metrics"
            )
