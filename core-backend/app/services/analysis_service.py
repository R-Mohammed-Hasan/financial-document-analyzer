"""
AI Analysis Service for financial document processing.

This module provides business logic for orchestrating AI analysis workflows
using CrewAI agents and tasks.
"""

import os
import tempfile
from typing import Dict, Any, Optional, List
from crewai import Crew, Process
from sqlalchemy.ext.asyncio import AsyncSession

from ai.agents import financial_analyst, verifier, investment_advisor, risk_assessor
from ai.tasks import (
    verify_document,
    analyze_financials,
    investment_analysis,
    assess_risks,
)
from db.session import get_async_db
from services.file_service import FileService


class AnalysisService:
    """
    Service class for AI-powered financial document analysis.
    """

    def __init__(self, db: AsyncSession):
        """Initialize analysis service with database session."""
        self.db = db
        self.file_service = FileService(db)

    async def analyze_document(
        self, file_id: int, query: str, user_id: int
    ) -> Dict[str, Any]:
        """
        Perform comprehensive AI analysis on a financial document.

        Args:
            file_id: ID of the file to analyze
            query: User's analysis query
            user_id: ID of the user requesting analysis

        Returns:
            Dictionary with analysis results
        """
        try:
            # Get file information
            file_info = await self._get_file_content(file_id, user_id)
            if not file_info:
                return {"success": False, "error": "File not found or access denied"}

            # Create analysis crew
            analysis_crew = Crew(
                agents=[verifier, financial_analyst, investment_advisor, risk_assessor],
                tasks=[
                    verify_document,
                    analyze_financials,
                    investment_analysis,
                    assess_risks,
                ],
                process=Process.sequential,
                verbose=True,
            )

            # Set query context for all agents
            for agent in analysis_crew.agents:
                agent.goal = agent.goal.replace("{query}", query)

            # Execute analysis
            result = analysis_crew.kickoff()

            return {
                "success": True,
                "file_id": file_id,
                "query": query,
                "results": {
                    "verification": (
                        result.tasks_output[0] if result.tasks_output else ""
                    ),
                    "financial_analysis": (
                        result.tasks_output[1] if len(result.tasks_output) > 1 else ""
                    ),
                    "investment_analysis": (
                        result.tasks_output[2] if len(result.tasks_output) > 2 else ""
                    ),
                    "risk_assessment": (
                        result.tasks_output[3] if len(result.tasks_output) > 3 else ""
                    ),
                },
            }

        except Exception as e:
            return {"success": False, "error": f"Analysis failed: {str(e)}"}

    async def _get_file_content(self, file_id: int, user_id: int) -> Optional[str]:
        """
        Get file content for analysis.

        Args:
            file_id: File ID
            user_id: User ID

        Returns:
            File content as string or None if not accessible
        """
        try:
            # Get file from database
            file = await self.file_service.get_file_by_id(file_id)
            if not file or file.user_id != user_id:
                return None

            # Check if file exists on disk
            if not os.path.exists(file.file_path):
                return None

            # Read file content based on type
            if file.content_type == "application/pdf":
                from ai.tools import read_financial_pdf

                return read_financial_pdf(file.file_path)
            else:
                # For other file types, read as text
                with open(file.file_path, "r", encoding="utf-8") as f:
                    return f.read()

        except Exception:
            return None

    async def get_analysis_history(
        self, user_id: int, limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Get user's analysis history.

        Args:
            user_id: User ID
            limit: Maximum number of records to return

        Returns:
            List of analysis history records
        """
        # Mock implementation - replace with actual database queries
        return [
            {
                "id": 1,
                "file_id": 1,
                "query": "Analyze Q4 earnings impact on stock price",
                "created_at": "2023-12-01T10:00:00",
                "status": "completed",
            },
            {
                "id": 2,
                "file_id": 2,
                "query": "Risk assessment for market volatility",
                "created_at": "2023-12-01T11:00:00",
                "status": "completed",
            },
        ][:limit]

    async def get_supported_file_types(self) -> List[str]:
        """
        Get list of supported file types for analysis.

        Returns:
            List of supported file extensions
        """
        return [".pdf", ".docx", ".xlsx", ".csv", ".txt"]

    async def validate_file_for_analysis(
        self, file_id: int, user_id: int
    ) -> Dict[str, Any]:
        """
        Validate if a file can be analyzed.

        Args:
            file_id: File ID
            user_id: User ID

        Returns:
            Validation result
        """
        try:
            file = await self.file_service.get_file_by_id(file_id)
            if not file:
                return {"valid": False, "reason": "File not found"}

            if file.user_id != user_id:
                return {"valid": False, "reason": "Access denied"}

            if file.status != "processed":
                return {"valid": False, "reason": "File not yet processed"}

            supported_types = await self.get_supported_file_types()
            file_ext = os.path.splitext(file.filename)[1].lower()

            if file_ext not in supported_types:
                return {"valid": False, "reason": f"Unsupported file type: {file_ext}"}

            return {
                "valid": True,
                "file_info": {
                    "id": file.id,
                    "name": file.original_filename,
                    "type": file.file_type,
                    "size": file.file_size,
                },
            }

        except Exception as e:
            return {"valid": False, "reason": f"Validation error: {str(e)}"}

    async def get_analysis_status(self, analysis_id: int) -> Dict[str, Any]:
        """
        Get the status of a specific analysis.

        Args:
            analysis_id: Analysis ID

        Returns:
            Analysis status information
        """
        # Mock implementation - replace with actual database queries
        return {
            "id": analysis_id,
            "status": "completed",
            "progress": 100,
            "estimated_time_remaining": 0,
        }

    async def cancel_analysis(self, analysis_id: int, user_id: int) -> Dict[str, Any]:
        """
        Cancel a running analysis.

        Args:
            analysis_id: Analysis ID
            user_id: User ID

        Returns:
            Cancellation result
        """
        # Mock implementation - replace with actual cancellation logic
        return {"success": True, "message": "Analysis cancelled successfully"}

    async def get_analysis_metrics(self, user_id: int) -> Dict[str, Any]:
        """
        Get analysis metrics for a user.

        Args:
            user_id: User ID

        Returns:
            Analysis metrics
        """
        # Mock implementation - replace with actual metrics calculation
        return {
            "total_analyses": 25,
            "successful_analyses": 23,
            "failed_analyses": 2,
            "average_processing_time": 45,  # seconds
            "most_analyzed_file_type": "pdf",
            "analysis_trends": {"this_week": 5, "this_month": 18, "this_year": 25},
        }
