from sqlalchemy import Column, Integer, String, Float, JSON, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from db.base import Base


class FinancialAnalysis(Base):
    """
    Model for storing financial analysis results.
    """
    __tablename__ = "financial_analyses"

    id = Column(Integer, primary_key=True, index=True)
    file_id = Column(Integer, ForeignKey("files.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    analysis_type = Column(String(50), nullable=False)  # 'revenue', 'eps', 'comparative', etc.
    
    # Common fields
    title = Column(String(200), nullable=False)
    description = Column(String(1000), nullable=True)
    
    # Analysis data (stored as JSON for flexibility)
    data = Column(JSON, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    file = relationship("File", back_populates="analyses")
    user = relationship("User", back_populates="financial_analyses")
    metrics = relationship("FinancialMetric", back_populates="analysis", cascade="all, delete-orphan")

    def to_dict(self):
        """Convert model to dictionary for API responses."""
        return {
            "id": self.id,
            "file_id": self.file_id,
            "analysis_type": self.analysis_type,
            "title": self.title,
            "description": self.description,
            "data": self.data,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }


class FinancialMetric(Base):
    """
    Model for storing time-series financial metrics.
    """
    __tablename__ = "financial_metrics"
    
    id = Column(Integer, primary_key=True, index=True)
    analysis_id = Column(Integer, ForeignKey("financial_analyses.id"), nullable=False)
    metric_name = Column(String(100), nullable=False)  # e.g., 'revenue', 'eps', 'gross_margin'
    period = Column(String(20), nullable=False)  # e.g., 'Q1 2023', '2023', 'FY2023'
    value = Column(Float, nullable=False)
    previous_value = Column(Float, nullable=True)
    yoy_change = Column(Float, nullable=True)
    qoq_change = Column(Float, nullable=True)
    
    # Additional metadata
    metadata_ = Column("metadata", JSON, nullable=True)
    
    # Timestamp
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    analysis = relationship("FinancialAnalysis", back_populates="metrics")

    def to_dict(self):
        """Convert model to dictionary for API responses."""
        return {
            "id": self.id,
            "analysis_id": self.analysis_id,
            "metric_name": self.metric_name,
            "period": self.period,
            "value": self.value,
            "previous_value": self.previous_value,
            "yoy_change": self.yoy_change,
            "qoq_change": self.qoq_change,
            "metadata": self.metadata_ or {},
            "created_at": self.created_at.isoformat() if self.created_at else None
        }
