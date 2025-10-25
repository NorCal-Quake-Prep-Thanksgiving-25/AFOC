"""Cloud cost integrations (AWS, Azure, GCP)."""
from __future__ import annotations

import random
from typing import Dict, Iterable, List

from ..pydantic_compat import BaseModel


class CloudSpendSample(BaseModel):
    provider: str
    service: str
    amount: float


class CostCollector(BaseModel):
    provider: str
    credentials_ref: str

    def collect(self) -> List[CloudSpendSample]:  # pragma: no cover - simple wrapper
        # Placeholder for SDK integrations. Generates deterministic-ish samples.
        random.seed(self.provider)
        services = ["compute", "storage", "networking", "database"]
        return [
            CloudSpendSample(provider=self.provider, service=svc, amount=random.random() * 1000)
            for svc in services
        ]


class AWSCostCollector(CostCollector):
    provider: str = "aws"


class AzureCostCollector(CostCollector):
    provider: str = "azure"


class GCPCostCollector(CostCollector):
    provider: str = "gcp"


AVAILABLE_COLLECTORS = {
    "aws_cur": AWSCostCollector,
    "azure_cost": AzureCostCollector,
    "gcp_billing": GCPCostCollector,
}
