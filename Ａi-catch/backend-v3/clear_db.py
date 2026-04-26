import asyncio
from app.database.connection import engine
from sqlalchemy import text

async def clear_portfolio():
    async with engine.begin() as conn:
        print("Clearing trade_records table...")
        await conn.execute(text("DELETE FROM trade_records"))
        
        print("Clearing portfolio table...")
        await conn.execute(text("DELETE FROM portfolio"))

        print("Clearing analysis_accuracy table...")
        await conn.execute(text("DELETE FROM analysis_accuracy"))
        
        # Reset sequence to 1
        print("Resetting sequences...")
        try:
            await conn.execute(text("ALTER SEQUENCE portfolio_id_seq RESTART WITH 1"))
            await conn.execute(text("ALTER SEQUENCE trade_records_id_seq RESTART WITH 1"))
            await conn.execute(text("ALTER SEQUENCE analysis_accuracy_id_seq RESTART WITH 1"))
        except Exception as e:
            print(f"Error resetting sequence: {e}")
            
    print("Done! All records have been deleted and reset.")

if __name__ == "__main__":
    asyncio.run(clear_portfolio())
