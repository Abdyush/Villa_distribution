from __future__ import annotations

from src.domain.ports import DistributionLogRepository
from src.domain.types import DistributionMessage


class NoopDistributionLogRepository(DistributionLogRepository):
    def save(self, distribution: DistributionMessage) -> None:
        return None
