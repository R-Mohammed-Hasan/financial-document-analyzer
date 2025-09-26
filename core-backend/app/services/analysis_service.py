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
from sqlalchemy import select

from ai.agents import financial_analyst, verifier, investment_advisor, risk_assessor
from ai.tasks import (
    verify_document,
    analyze_financials,
    investment_analysis,
    assess_risks,
)
from db.session import get_async_db
from db.models.file import File
from services.file_service import FileService
from core.logging_config import get_logger

# Module-level logger for the service layer
logger = get_logger(__name__)


class AnalysisService:
    """
    Service class for AI-powered financial document analysis.
    """

    def __init__(self, db: AsyncSession):
        """
        Initialize the analysis service with an async database session.

        Returns:
            None
        """
        self.db = db
        self.file_service = FileService(db)

    async def analyze_document(
        self, file_name: str, query: str, user_id: int
    ) -> Dict[str, Any]:
        """
        Perform comprehensive AI analysis on a financial document.

        Args:
            file_name: Name of the file to analyze
            query: User's analysis query
            user_id: ID of the user requesting analysis

        Returns:
            Dictionary with analysis results (success flag, details, or error).
        """
        try:
            logger.info(
                f"Analysis requested | file_name={file_name} user_id={user_id} query_len={len(query) if query else 0}"
            )
            # Get file information
            file_info = await self._get_file_content(file_name, user_id)
            if not file_info:
                logger.warning(
                    f"Analysis aborted: file not accessible | file_name={file_name} user_id={user_id}"
                )
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

            output = {
                "success": True,
                "file_name": file_name,
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
            logger.info(f"Analysis completed | file_name={file_name} user_id={user_id}")
            return output

        except Exception as e:
            logger.error(
                f"Analysis failed | file_name={file_name} user_id={user_id} error={e}",
                exc_info=True,
            )
            return {"success": False, "error": f"Analysis failed: {str(e)}"}

    async def _get_file_content(self, file_name: str, user_id: int) -> Optional[str]:
        """
        Get file content for analysis.

        Args:
            file_name: File name
            user_id: User ID

        Returns:
            File content as string or None if not accessible.
        """
        try:
            # Get file from database by original filename
            file = await self._get_file_by_name(file_name, user_id)
            if not file:
                logger.debug(
                    f"File not accessible | file_name={file_name} user_id={user_id}"
                )
                return None

            # Check if file exists on disk
            if not os.path.exists(file.file_path):
                logger.debug(f"File missing on disk | path={file.file_path}")
                return None

            # Read file content based on type
            if file.content_type == "application/pdf":
                from ai.tools import read_financial_pdf

                content = read_financial_pdf(file.file_path)
                logger.debug(
                    f"PDF content loaded | file_name={file_name} length={len(content) if content else 0}"
                )
                return content
            else:
                # For other file types, read as text
                with open(file.file_path, "r", encoding="utf-8") as f:
                    content = f.read()
                    logger.debug(
                        f"Text content loaded | file_name={file_name} length={len(content) if content else 0}"
                    )
                    return content

        except Exception as e:
            logger.error(
                f"Failed to load file content | file_name={file_name} user_id={user_id} error={e}",
                exc_info=True,
            )
            return None

    async def _get_file_by_name(self, file_name: str, user_id: int):
        """
        Get file by original filename and user ID.

        Args:
            file_name: Original filename
            user_id: User ID

        Returns:
            File object or None if not found.
        """
        try:
            # Try async first
            result = await self.db.execute(
                select(File).where(File.filename == file_name, File.user_id == user_id)
            )
            file = result.scalars().first()
            return file
        except TypeError:
            # Fallback to sync if session is not async
            file = (
                self.db.query(File)
                .filter(File.original_filename == file_name, File.user_id == user_id)
                .first()
            )
            return file

    async def get_analysis_history(
        self, user_id: int, limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Get user's analysis history (mock implementation).

        Args:
            user_id: User ID
            limit: Maximum number of records to return

        Returns:
            List of analysis history records.
        """
        # Mock implementation - replace with actual database queries
        history = [
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
        logger.debug(f"Analysis history | user_id={user_id} count={len(history)}")
        return history

    async def get_supported_file_types(self) -> List[str]:
        """
        Get list of supported file types for analysis.

        Returns:
            List of supported file extensions.
        """
        return [".pdf", ".docx", ".xlsx", ".csv", ".txt"]

    async def validate_file_for_analysis(
        self, file_name: str, user_id: int
    ) -> Dict[str, Any]:
        """
        Validate if a file can be analyzed.

        Args:
            file_name: File name
            user_id: User ID

        Returns:
            Validation result as a dictionary with validity and details.
        """
        try:
            file = await self._get_file_by_name(file_name, user_id)
            if not file:
                logger.debug(f"Validation: file not found | file_name={file_name}")
                return {"valid": False, "reason": "File not found"}

            supported_types = await self.get_supported_file_types()
            file_ext = os.path.splitext(file.filename)[1].lower()

            if file_ext not in supported_types:
                logger.debug(
                    f"Validation: unsupported type | file_name={file_name} ext={file_ext}"
                )
                return {"valid": False, "reason": f"Unsupported file type: {file_ext}"}

            result = {
                "valid": True,
                "file_info": {
                    "id": file.id,
                    "name": file.original_filename,
                    "type": file.file_type,
                    "size": file.file_size,
                },
            }
            logger.debug(f"Validation: success | file_name={file_name}")
            return result

        except Exception as e:
            logger.error(
                f"Validation error | file_name={file_name} user_id={user_id} error={e}",
                exc_info=True,
            )
            return {"valid": False, "reason": f"Validation error: {str(e)}"}

    async def get_analysis_status(self, analysis_id: int) -> Dict[str, Any]:
        """
        Get the status of a specific analysis (mock implementation).

        Args:
            analysis_id: Analysis ID

        Returns:
            Analysis status information.
        """
        # Mock implementation - replace with actual database queries
        return {
            "id": analysis_id,
            "status": "completed",
            "estimated_time_remaining": 0,
        }

    async def cancel_analysis(self, analysis_id: int, user_id: int) -> Dict[str, Any]:
        """
        Cancel a running analysis (mock implementation).

        Args:
            analysis_id: Analysis ID
            user_id: User ID

        Returns:
            Cancellation result as a success dictionary.
        """
        # Mock implementation - replace with actual cancellation logic
        logger.info(
            f"Analysis cancel requested | analysis_id={analysis_id} user_id={user_id}"
        )
        return {"success": True, "message": "Analysis cancelled successfully"}

    async def get_analysis_metrics(self, user_id: int) -> Dict[str, Any]:
        """
        Get analysis metrics for a user (mock implementation).

        Args:
            user_id: User ID

        Returns:
            Analysis metrics as a dictionary.
        """
        # Mock implementation - replace with actual metrics calculation
        metrics = {
            "total_analyses": 25,
            "successful_analyses": 23,
            "failed_analyses": 2,
            "average_processing_time": 45,  # seconds
            "most_analyzed_file_type": "pdf",
            "analysis_trends": {"this_week": 5, "this_month": 18, "this_year": 25},
        }
        logger.debug(
            f"Analysis metrics | user_id={user_id} totals={metrics['total_analyses']}"
        )
        return metrics
