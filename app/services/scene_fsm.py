"""场景状态机全局联动引擎"""
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.fsm import LifeSceneState


class SceneFSM:
    """生活场景状态机

    六大状态：
    - daily: 日常模式
    - exam: 备考模式
    - travel: 出差模式
    - vacation: 假期模式
    - sick: 生病模式
    - overtime: 加班模式

    状态切换时，全模块自动适配。
    """

    # 状态联动配置
    STATE_CONFIGS = {
        "daily": {
            "description": "日常模式",
            "study_weight": 1.0,
            "entertainment_weight": 1.0,
            "budget_factor": 1.0,
            "task_count": 5,
            "difficulty": "medium",
        },
        "exam": {
            "description": "备考模式",
            "study_weight": 2.0,
            "entertainment_weight": 0.3,
            "budget_factor": 0.7,
            "task_count": 8,
            "difficulty": "hard",
            "budget_adjust": {"study": 1.5, "entertainment": 0.3, "food": 0.8},
        },
        "travel": {
            "description": "出差模式",
            "study_weight": 0.3,
            "entertainment_weight": 0.5,
            "budget_factor": 1.5,
            "task_count": 2,
            "difficulty": "easy",
            "budget_adjust": {"transport": 2.0, "food": 1.5, "study": 0.2},
        },
        "vacation": {
            "description": "假期模式",
            "study_weight": 0.2,
            "entertainment_weight": 2.0,
            "budget_factor": 1.8,
            "task_count": 1,
            "difficulty": "easy",
            "budget_adjust": {"entertainment": 2.5, "travel": 2.0, "study": 0.1},
        },
        "sick": {
            "description": "生病模式",
            "study_weight": 0.0,
            "entertainment_weight": 0.3,
            "budget_factor": 0.8,
            "task_count": 0,
            "difficulty": "rest",
            "budget_adjust": {"medical": 3.0, "food": 0.6, "entertainment": 0.1},
        },
        "overtime": {
            "description": "加班模式",
            "study_weight": 0.3,
            "entertainment_weight": 0.2,
            "budget_factor": 0.9,
            "task_count": 3,
            "difficulty": "easy",
            "budget_adjust": {"food": 1.2, "study": 0.3, "entertainment": 0.2},
        },
    }

    def __init__(self, session: AsyncSession, user_id: int):
        self.session = session
        self.user_id = user_id

    async def switch_state(self, new_state: str, params: dict | None = None) -> dict[str, Any]:
        """切换生活状态，全模块联动"""
        if new_state not in self.STATE_CONFIGS:
            return {"success": False, "message": f"未知状态: {new_state}"}

        config = self.STATE_CONFIGS[new_state]

        # 关闭当前状态
        await self._deactivate_current()

        # 创建新状态
        state = LifeSceneState(
            user_id=self.user_id,
            current_state=new_state,
            state_params=params or {},
            expected_end=datetime.utcnow() + timedelta(days=params.get("duration", 7)) if params else None,
            adjustments={},
        )
        self.session.add(state)
        await self.session.flush()

        # 执行联动调整
        adjustments = await self._apply_adjustments(new_state, config)

        state.adjustments = adjustments
        await self.session.flush()

        return {
            "success": True,
            "state": new_state,
            "description": config["description"],
            "adjustments": adjustments,
            "message": f"已切换到{config['description']}，全模块已自动适配",
        }

    async def _deactivate_current(self) -> None:
        """关闭当前状态"""
        from sqlalchemy import select, and_
        result = await self.session.execute(
            select(LifeSceneState).where(and_(
                LifeSceneState.user_id == self.user_id,
                LifeSceneState.is_active == True,
            ))
        )
        current = result.scalar_one_or_none()
        if current:
            current.is_active = False

    async def _apply_adjustments(self, state: str, config: dict) -> dict:
        """应用联动调整"""
        adjustments = {}

        # 1. 调整学习计划
        adjustments["study"] = {
            "weight": config["study_weight"],
            "task_count": config["task_count"],
            "difficulty": config["difficulty"],
        }

        # 2. 调整预算
        if "budget_adjust" in config:
            adjustments["budget"] = config["budget_adjust"]

        # 3. 调整日程密度
        adjustments["schedule"] = {
            "density": "high" if config["task_count"] > 5 else "medium" if config["task_count"] > 2 else "low",
            "flexible": state in ["vacation", "sick"],
        }

        # 4. 调整消费阈值
        adjustments["consume"] = {
            "impulse_alert_threshold": 0.7 if state == "vacation" else 0.5,
            "budget_factor": config["budget_factor"],
        }

        return adjustments

    async def get_current_state(self) -> dict[str, Any]:
        """获取当前状态"""
        from sqlalchemy import select, and_
        result = await self.session.execute(
            select(LifeSceneState).where(and_(
                LifeSceneState.user_id == self.user_id,
                LifeSceneState.is_active == True,
            )).order_by(LifeSceneState.created_at.desc()).limit(1)
        )
        state = result.scalar_one_or_none()

        if not state:
            return {"state": "daily", "description": "日常模式", "adjustments": {}}

        return {
            "state": state.current_state,
            "description": self.STATE_CONFIGS.get(state.current_state, {}).get("description", ""),
            "started_at": state.started_at.isoformat(),
            "expected_end": state.expected_end.isoformat() if state.expected_end else None,
            "adjustments": state.adjustments,
        }
