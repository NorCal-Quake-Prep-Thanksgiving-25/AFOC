"""SQLAlchemy models and Pydantic schemas for AFOC."""

from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel
from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    Date,
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
    metadata_json = Column("metadata", JSON, nullable=True)

    utilization = relationship("Utilization", back_populates="event", uselist=False)


class ResourceInventory(Base):
    """Describe provisioned resources that incur cost."""

    __tablename__ = "resource_inventory"

    id = Column(Integer, primary_key=True)
    resource_id = Column(String(128), unique=True, nullable=False)
    provider = Column(String(32), nullable=False)
    resource_type = Column(String(64), nullable=False)
    region = Column(String(32), nullable=True)
    metadata_json = Column("metadata", JSON, nullable=True)

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


class TelemetryEventRecord(Base):
    """Unified telemetry event queue stored in the primary database."""

    __tablename__ = "telemetry_events"

    id = Column(Integer, primary_key=True)
    ts = Column(DateTime, nullable=False, default=datetime.utcnow)
    event_type = Column(String(32), nullable=False)
    scope = Column(String(256), nullable=False)
    severity = Column(String(16), nullable=False, default="info")
    payload = Column(JSON, nullable=False)
    dedupe_key = Column(String(256), nullable=True)
    processed = Column(Boolean, nullable=False, default=False)


class TelemetryDeadLetter(Base):
    """Capture telemetry events that failed downstream processing."""

    __tablename__ = "telemetry_dlq"

    id = Column(Integer, primary_key=True)
    ts = Column(DateTime, nullable=False, default=datetime.utcnow)
    event_id = Column(Integer, nullable=True)
    reason = Column(Text, nullable=True)
    payload = Column(JSON, nullable=False)


class ValueProof(Base):
    """Persist generated valuation proofs for audit trails."""

    __tablename__ = "value_proofs"

    id = Column(Integer, primary_key=True)
    generated_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    period_start = Column(Date, nullable=False)
    period_end = Column(Date, nullable=False)
    tier = Column(String(32), nullable=False)
    annual_spend = Column(Numeric(16, 2), nullable=False)
    anomaly_value = Column(Numeric(16, 2), nullable=False)
    rightsize_value = Column(Numeric(16, 2), nullable=False)
    forecast_value = Column(Numeric(16, 2), nullable=False)
    integrated_value = Column(Numeric(16, 2), nullable=False)
    assumptions = Column(JSON, nullable=False)
    signature = Column(String(512), nullable=True)


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


class TelemetryEventModel(BaseModel):
    """Schema representation of telemetry event records."""

    id: Optional[int]
    ts: datetime
    event_type: str
    scope: str
    severity: str
    payload: dict
    dedupe_key: Optional[str]
    processed: bool

    class Config:
        orm_mode = True


class TelemetryDeadLetterModel(BaseModel):
    """Schema for dead-letter queue entries."""

    id: Optional[int]
    ts: datetime
    event_id: Optional[int]
    reason: Optional[str]
    payload: dict

    class Config:
        orm_mode = True


class ValueProofModel(BaseModel):
    """Schema for persisted value proofs."""

    id: Optional[int]
    generated_at: datetime
    period_start: date
    period_end: date
    tier: str
    annual_spend: float
    anomaly_value: float
    rightsize_value: float
    forecast_value: float
    integrated_value: float
    assumptions: dict
    signature: Optional[str]

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
    "TelemetryEventRecord",
    "TelemetryDeadLetter",
    "ValueProof",
    "UsageEventModel",
    "ResourceInventoryModel",
    "UtilizationModel",
    "AnomalyModel",
    "RightsizingRecommendationModel",
    "ForecastModel",
    "ValueReportModel",
    "TelemetryEventModel",
    "TelemetryDeadLetterModel",
    "ValueProofModel",
]
