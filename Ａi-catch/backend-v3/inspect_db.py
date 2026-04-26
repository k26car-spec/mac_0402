
import asyncio
from sqlalchemy import inspect
from app.database.connection import engine

async def inspect_table():
    async with engine.connect() as conn:
        def get_columns(connection):
            inspector = inspect(connection)
            return inspector.get_columns('portfolio')
            
        columns = await conn.run_sync(get_columns)
        print("Existing columns in 'portfolio' table:")
        for col in columns:
            print(f"- {col['name']} ({col['type']})")

if __name__ == "__main__":
    try:
        asyncio.run(inspect_table())
    except Exception as e:
        print(f"Error: {e}")
