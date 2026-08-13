"""初始化5个固定角色（仅空库时执行）"""
import asyncio
from app.db import AsyncSessionLocal, init_db, engine, Base
from app.models.user import User

ROLES = [
    {"id": 1, "username": "学生小明", "user_type": "student", "wake_hour": 7, "sleep_hour": 23},
    {"id": 2, "username": "职场小李", "user_type": "worker", "wake_hour": 6, "sleep_hour": 22},
    {"id": 3, "username": "自由职业者", "user_type": "general", "wake_hour": 9, "sleep_hour": 1},
    {"id": 4, "username": "考研党", "user_type": "student", "wake_hour": 5, "sleep_hour": 23},
    {"id": 5, "username": "全职妈妈", "user_type": "general", "wake_hour": 6, "sleep_hour": 22},
]


async def seed():
    await init_db()
    async with AsyncSessionLocal() as s:
        from sqlalchemy import select, func
        count = await s.execute(select(func.count(User.id)))
        if count.scalar() > 0:
            return  # 已有数据，跳过
        for role in ROLES:
            u = User(id=role["id"], username=role["username"],
                    hashed_password="x", user_type=role["user_type"],
                    wake_hour=role["wake_hour"], sleep_hour=role["sleep_hour"])
            s.add(u)
        await s.commit()
        print(f"[OK] 5个角色已初始化")


if __name__ == "__main__":
    asyncio.run(seed())
