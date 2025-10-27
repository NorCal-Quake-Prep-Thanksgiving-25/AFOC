"""SQLAlchemy models and Pydantic schemas for AFOC."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel
from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    """Base class for declarative models."""

    pass


class UsageEvent(Base):
    """Track raw usage data for cost analysis."""

    __tablename__ = "usage_events"

    id = Column(Integer, primary_key=True)
    occurred_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    source = Column(String(64), nullable=False)
    service = Column(String(128), nullable=False)
    cost = Column(Numeric(14, 4), nullable=False)
    metadata = Column(JSON, nullable=True)

    utilization = relationship("Utilization", back_populates="event", uselist=False)


class ResourceInventory(Base):
    """Describe provisioned resources that incur cost."""

    __tablename__ = "resource_inventory"

    id = Column(Integer, primary_key=True)
    resource_id = Column(String(128), unique=True, nullable=False)
    provider = Column(String(32), nullable=False)
    resource_type = Column(String(64), nullable=False)
    region = Column(String(32), nullable=True)
    metadata = Column(JSON, nullable=True)

    utilizations = relationship("Utilization", back_populates="resource")


class Utilization(Base):
    """Capture performance utilization for resources."""

    __tablename__ = "utilization"

    id = Column(Integer, primary_key=True)
    resource_id = Column(Integer, ForeignKey("resource_inventory.id"), nullable=False)
    usage_event_id = Column(Integer, ForeignKey("usage_events.id"), nullable=True)
    observed_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    cpu_percent = Column(Float, nullable=True)
    memory_percent = Column(Float, nullable=True)
    notes = Column(Text, nullable=True)

    resource = relationship("ResourceInventory", back_populates="utilizations")
    event = relationship("UsageEvent", back_populates="utilization")


class Anomaly(Base):
    """Record anomalies detected in spend or utilization."""

    __tablename__ = "anomalies"

    id = Column(Integer, primary_key=True)
    detected_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    resource_id = Column(Integer, ForeignKey("resource_inventory.id"), nullable=True)
    severity = Column(String(16), nullable=False, default="medium")
    description = Column(Text, nullable=False)
    z_score = Column(Float, nullable=True)


class RightsizingRecommendation(Base):
    """Store automated right-sizing recommendations."""

    __tablename__ = "rightsizing_recs"

    id = Column(Integer, primary_key=True)
    resource_id = Column(Integer, ForeignKey("resource_inventory.id"), nullable=False)
    recommendation = Column(String(32), nullable=False)
    estimated_savings = Column(Float, nullable=False, default=0.0)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)


class Forecast(Base):
    """Persist forecast outputs for reporting."""

    __tablename__ = "forecasts"

    id = Column(Integer, primary_key=True)
    generated_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    metric = Column(String(64), nullable=False)
    horizon_days = Column(Integer, nullable=False, default=30)
    point_estimate = Column(Numeric(14, 4), nullable=False)
    lower_bound = Column(Numeric(14, 4), nullable=True)
    upper_bound = Column(Numeric(14, 4), nullable=True)


class ValueReport(Base):
    """High-level valuation reports for stakeholders."""

    __tablename__ = "value_reports"

    id = Column(Integer, primary_key=True)
    generated_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    owner = Column(String(128), nullable=False)
    value_score = Column(Float, nullable=False)
    notes = Column(Text, nullable=True)
    published = Column(Boolean, default=False, nullable=False)


class UsageEventModel(BaseModel):
    """Pydantic schema for usage events."""

    id: Optional[int]
    occurred_at: datetime
    source: str
    service: str
    cost: float
    metadata: Optional[dict]

    class Config:
        orm_mode = True


class ResourceInventoryModel(BaseModel):
    """Pydantic schema for resource inventory."""

    id: Optional[int]
    resource_id: str
    provider: str
    resource_type: str
    region: Optional[str]
    metadata: Optional[dict]

    class Config:
        orm_mode = True


class UtilizationModel(BaseModel):
    """Pydantic schema for utilization entries."""

    id: Optional[int]
    resource_id: int
    usage_event_id: Optional[int]
    observed_at: datetime
    cpu_percent: Optional[float]
    memory_percent: Optional[float]
    notes: Optional[str]

    class Config:
        orm_mode = True


class AnomalyModel(BaseModel):
    """Pydantic schema for anomalies."""

    id: Optional[int]
    detected_at: datetime
    resource_id: Optional[int]
    severity: str
    description: str
    z_score: Optional[float]

    class Config:
        orm_mode = True


class RightsizingRecommendationModel(BaseModel):
    """Pydantic schema for right-sizing recommendations."""

    id: Optional[int]
    resource_id: int
    recommendation: str
    estimated_savings: float
    created_at: datetime

    class Config:
        orm_mode = True


class ForecastModel(BaseModel):
    """Pydantic schema for forecasts."""

    id: Optional[int]
    generated_at: datetime
    metric: str
    horizon_days: int
    point_estimate: float
    lower_bound: Optional[float]
    upper_bound: Optional[float]

    class Config:
        orm_mode = True


class ValueReportModel(BaseModel):
    """Pydantic schema for valuation reports."""

    id: Optional[int]
    generated_at: datetime
    owner: str
    value_score: float
    notes: Optional[str]
    published: bool

    class Config:
        orm_mode = True


__all__ = [
    "Base",
    "UsageEvent",
    "ResourceInventory",
    "Utilization",
    "Anomaly",
    "RightsizingRecommendation",
    "Forecast",
    "ValueReport",
    "UsageEventModel",
    "ResourceInventoryModel",
    "UtilizationModel",
    "AnomalyModel",
    "RightsizingRecommendationModel",
    "ForecastModel",
    "ValueReportModel",
]
