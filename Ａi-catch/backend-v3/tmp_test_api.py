import asyncio
import json
import os
import sys

# Add the root directory to sys.path to import local modules
sys.path.append("/Users/Mac/Documents/ETF/AI/Ａi-catch")
sys.path.append("/Users/Mac/Documents/ETF/AI/Ａi-catch/backend-v3")

from app.services.stock_comprehensive_analyzer import analyze_stock_comprehensive

async def run():
    print("Starting Comprehensive Analysis for 2330...")
    try:
        # We need to set up logging to see what's happening
        import logging
        logging.basicConfig(level=logging.INFO)
        
        # Override some config if needed
        os.environ["TWSE_RETRIES"] = "1" 
        
        res = await analyze_stock_comprehensive('2330', quick_mode=True)
        
        financial = res.get('financial_health', {})
        institutional = res.get('institutional_trading', {})
        macro = res.get('macro_summary', {})
        
        output = {
            "has_institutional": bool(institutional),
            "has_financial": bool(financial),
            "has_macro": bool(macro),
            "quarterly_eps": financial.get('quarterly_eps', []) if financial else [],
            "macro_sentiment": macro.get('sentiment', 'N/A') if macro else 'N/A',
            "macro_summary": macro.get('summary', 'N/A') if macro else 'N/A'
        }
        
        print("\n--- Summary Results ---")
        print(json.dumps(output, indent=2, ensure_ascii=False))
        
    except Exception as e:
        print(f"\n❌ Error during analysis: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(run())
