
import sys
import os
import asyncio

# Setup path
PROJECT_ROOT = "/Users/Mac/Documents/ETF/AI/Ａi-catch"
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# Load env variables manually for test env
from dotenv import load_dotenv
env_path = os.path.join(PROJECT_ROOT, "fubon.env")
if os.path.exists(env_path):
    load_dotenv(env_path)
    print("Loaded fubon.env")
else:
    print("fubon.env not found")

try:
    from fubon_client import fubon_client
    
    async def test():
        print("Testing Fubon API connection...")
        try:
            connected = await fubon_client.connect()
            if connected:
                print("✅ Fubon API Connection Successful!")
                # Get a quote just to be sure
                try:
                    quote = await fubon_client.get_quote("2330")
                    print(f"Sample Quote (2330): {quote}")
                except Exception as e:
                    print(f"Quote Error: {e}")
            else:
                print("❌ Fubon API Connection Failed (Login returned False)")
                
        except Exception as e:
            print(f"❌ Connection Error: {e}")
        finally:
            fubon_client.logout()

    if __name__ == "__main__":
        asyncio.run(test())

except ImportError as e:
    print(f"Import Error: {e}")
