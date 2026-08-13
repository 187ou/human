"""偏好漂移持续检测引擎（KS检验）"""
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.mining import DriftDetectionRecord
from app.models.behavior import BehaviorLog


class KSDriftDetector:
    """KS检验漂移检测器"""

    DRIFT_THRESHOLD = 0.05
    MIN_SAMPLES = 7

    def __init__(self, session: AsyncSession, user_id: int):
        self.session = session
        self.user_id = user_id

    async def detect_all(self) -> list[dict[str, Any]]:
        """检测所有维度"""
        drifts = []
        for dim in ["sleep", "consume", "study", "schedule"]:
            drift = await self._detect(dim)
            if drift and drift["is_drifted"]:
                drifts.append(drift)

        await self.session.commit()
        return drifts

    async def _detect(self, dimension: str) -> dict | None:
        now = datetime.utcnow()
        mid = now - timedelta(days=15)
        early_start = now - timedelta(days=30)

        early = await self._get_values(dimension, early_start, mid)
        recent = await self._get_values(dimension, mid, now)

        if len(early) < self.MIN_SAMPLES or len(recent) < self.MIN_SAMPLES:
            return None

        ks_stat, p_value = self._ks_test(early, recent)
        is_drifted = p_value < self.DRIFT_THRESHOLD

        record = DriftDetectionRecord(
            user_id=self.user_id,
            dimension=dimension,
            ks_statistic=round(ks_stat, 4),
            p_value=round(p_value, 4),
            is_drifted=is_drifted,
            drift_description=f"{dimension}维度{'偏移' if is_drifted else '稳定'}(p={p_value:.4f})",
            action_taken="freeze_rules" if is_drifted else "none",
        )
        self.session.add(record)

        return {"dimension": dimension, "is_drifted": is_drifted, "p_value": round(p_value, 4)}

    async def _get_values(self, dimension: str, start: datetime, end: datetime) -> list[float]:
        result = await self.session.execute(
            select(BehaviorLog).where(and_(
                BehaviorLog.user_id == self.user_id,
                func.strftime('%Y-%m-%d', BehaviorLog.created_at) >= start.strftime('%Y-%m-%d'),
                func.strftime('%Y-%m-%d', BehaviorLog.created_at) < end.strftime('%Y-%m-%d'),
            ))
        )
        logs = result.scalars().all()
        return [float(log.value or 0) for log in logs if log.value is not None]

    def _ks_test(self, s1: list[float], s2: list[float]) -> tuple[float, float]:
        """KS检验"""
        all_vals = sorted(set(s1 + s2))
        max_diff = 0.0
        for v in all_vals:
            f1 = sum(1 for x in s1 if x <= v) / len(s1)
            f2 = sum(1 for x in s2 if x <= v) / len(s2)
            max_diff = max(max_diff, abs(f1 - f2))

        n1, n2 = len(s1), len(s2)
        en = (n1 * n2 / (n1 + n2)) ** 0.5
        p_val = 1.0 - self._kolmogorov((en + 0.12 + 0.11 / en) * max_diff) if en > 0 else 1.0
        return max_diff, max(0.001, min(1.0, p_val))

    @staticmethod
    def _kolmogorov(x: float) -> float:
        if x <= 0:
            return 0.0
        s = sum((-1) ** (k - 1) * (2.71828 ** (-2 * k * k * x * x)) for k in range(1, 50))
        return 1.0 - 2.0 * s
