import asyncio
import sys
from app.database.connection import async_session
from app.models.user import User
from sqlalchemy import select, update

async def set_admin(username: str):
    async with async_session() as session:
        result = await session.execute(
            select(User).where(User.username == username)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            print(f"找不到用戶: {username}")
            return
            
        user.role = "admin"
        await session.commit()
        print(f"成功將用戶 {username} 設為管理員 (admin)")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python set_admin.py <username>")
    else:
        asyncio.run(set_admin(sys.argv[1]))
