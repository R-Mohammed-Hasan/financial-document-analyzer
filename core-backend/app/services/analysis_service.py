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
        self, file_name: str, query: str, user_id: int, file_path: str = None
    ) -> Dict[str, Any]:
        """
        Perform comprehensive AI analysis on a financial document using CrewAI agents.

        This method orchestrates the analysis workflow by:
        1. Validating the document is accessible and in a supported format
        2. Setting up the CrewAI agents with the document and query context
        3. Executing the analysis workflow
        4. Processing and storing the results
        5. Returning structured analysis results

        Args:
            file_name: Name of the file to analyze
            query: User's analysis query or objective
            user_id: ID of the user requesting analysis
            file_path: Optional direct path to the file (for testing or direct access)

        Returns:
            Dictionary containing:
            - success: Boolean indicating if analysis was successful
            - analysis_id: ID of the stored analysis (if successful)
            - results: Structured analysis results
            - error: Error message if analysis failed
        """
        from datetime import datetime
        from db.models.analysis import FinancialAnalysis, FinancialMetric
        from sqlalchemy.exc import SQLAlchemyError
        import json

        analysis_start_time = datetime.utcnow()
        analysis_id = None

        try:
            logger.info(
                f"Starting document analysis | file={file_name} user_id={user_id} query='{query}'"
            )

            # Get file information and content
            file = await self._get_file_by_name(file_name, user_id)
            if not file:
                error_msg = f"File not found or access denied | file={file_name} user_id={user_id}"
                logger.warning(error_msg)
                return {"success": False, "error": error_msg}

            # Get file content
            file_content = await self._get_file_content(file_name, user_id)
            if not file_content:
                error_msg = f"Could not read file content | file={file_name}"
                logger.error(error_msg)
                return {"success": False, "error": error_msg}

            # Create a temporary file for the analysis
            with tempfile.NamedTemporaryFile(delete=False, suffix='.txt') as temp_file:
                temp_file.write(file_content.encode('utf-8'))
                temp_file_path = temp_file.name

            try:
                # Create analysis crew with context
                analysis_crew = Crew(
                    agents=[verifier, financial_analyst, investment_advisor, risk_assessor],
                    tasks=[verify_document, analyze_financials, investment_analysis, assess_risks],
                    process=Process.sequential,
                    verbose=True,
                    full_output=True
                )

                # Set context for all agents
                context = {
                    "file_path": temp_file_path,
                    "file_name": file_name,
                    "query": query,
                    "user_id": user_id,
                    "analysis_time": analysis_start_time.isoformat()
                }

                # Execute analysis
                logger.info(f"Starting CrewAI analysis | context={context}")
                result = analysis_crew.kickoff(inputs=context)

                # Process results
                if not result or not hasattr(result, 'tasks_output'):
                    raise ValueError("Invalid analysis result format from CrewAI")

                # Extract task outputs
                task_outputs = result.tasks_output if hasattr(result, 'tasks_output') else []
                
                # Create analysis record
                analysis = FinancialAnalysis(
                    user_id=user_id,
                    file_id=file.id,
                    query=query,
                    status="completed",
                    analysis_type="full_analysis",
                    metadata={
                        "file_name": file_name,
                        "analysis_start": analysis_start_time.isoformat(),
                        "analysis_end": datetime.utcnow().isoformat(),
                        "query": query,
                        "agent_versions": {
                            "financial_analyst": "1.0",
                            "verifier": "1.0",
                            "investment_advisor": "1.0",
                            "risk_assessor": "1.0"
                        }
                    }
                )

                # Add metrics for each analysis section
                metrics = []
                
                # Verification metrics
                if len(task_outputs) > 0:
                    verification = task_outputs[0] or {}
                    metrics.append(FinancialMetric(
                        analysis=analysis,
                        metric_name="document_verification",
                        metric_value=1.0 if verification.get("is_valid", False) else 0.0,
                        metadata=verification
                    ))
                
                # Financial metrics
                if len(task_outputs) > 1:
                    financials = task_outputs[1] or {}
                    metrics.append(FinancialMetric(
                        analysis=analysis,
                        metric_name="financial_analysis",
                        metric_value=1.0,  # Placeholder for overall score
                        metadata=financials
                    ))
                
                # Investment analysis
                if len(task_outputs) > 2:
                    investment = task_outputs[2] or {}
                    metrics.append(FinancialMetric(
                        analysis=analysis,
                        metric_name="investment_analysis",
                        metric_value=1.0,  # Placeholder for overall score
                        metadata=investment
                    ))
                
                # Risk assessment
                if len(task_outputs) > 3:
                    risks = task_outputs[3] or {}
                    metrics.append(FinancialMetric(
                        analysis=analysis,
                        metric_name="risk_assessment",
                        metric_value=1.0,  # Placeholder for overall score
                        metadata=risks
                    ))

                # Save to database
                try:
                    self.db.add(analysis)
                    await self.db.flush()
                    analysis_id = analysis.id
                    
                    # Add metrics in batch
                    if metrics:
                        self.db.add_all(metrics)
                    
                    await self.db.commit()
                    logger.info(f"Analysis saved | analysis_id={analysis_id} metrics_count={len(metrics)}")
                    
                except SQLAlchemyError as db_error:
                    await self.db.rollback()
                    logger.error(f"Database error saving analysis | error={str(db_error)}", exc_info=True)
                    raise

                # Prepare response
                response = {
                    "success": True,
                    "analysis_id": analysis_id,
                    "file_name": file_name,
                    "query": query,
                    "results": {
                        "verification": task_outputs[0] if len(task_outputs) > 0 else {},
                        "financial_analysis": task_outputs[1] if len(task_outputs) > 1 else {},
                        "investment_analysis": task_outputs[2] if len(task_outputs) > 2 else {},
                        "risk_assessment": task_outputs[3] if len(task_outputs) > 3 else {}
                    },
                    "metadata": {
                        "analysis_id": analysis_id,
                        "start_time": analysis_start_time.isoformat(),
                        "end_time": datetime.utcnow().isoformat(),
                        "metrics_count": len(metrics)
                    }
                }

                logger.info(f"Analysis completed successfully | analysis_id={analysis_id}")
                return response

            except Exception as crew_error:
                error_msg = f"CrewAI analysis failed | error={str(crew_error)}"
                logger.error(error_msg, exc_info=True)
                return {"success": False, "error": error_msg, "analysis_id": analysis_id}

            finally:
                # Clean up temporary file
                try:
                    if os.path.exists(temp_file_path):
                        os.unlink(temp_file_path)
                        logger.debug(f"Cleaned up temporary file | path={temp_file_path}")
                except Exception as cleanup_error:
                    logger.warning(f"Failed to clean up temporary file | error={str(cleanup_error)}")

        except Exception as e:
            logger.error(
                f"Document analysis failed | file={file_name} user_id={user_id} error={str(e)}",
                exc_info=True
            )
            return {
                "success": False,
                "error": f"Analysis failed: {str(e)}",
                "analysis_id": analysis_id
            }

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
