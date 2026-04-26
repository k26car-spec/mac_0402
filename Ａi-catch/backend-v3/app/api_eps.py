from fastapi import APIRouter
import yfinance as yf

router = APIRouter()

@router.get("/api/analysis/eps/{symbol}")
async def get_eps_evaluation(symbol: str):
    try:
        ticker = yf.Ticker(f"{symbol}.TW" if len(symbol) == 4 else symbol)
        info = ticker.info
        
        trailing_eps = info.get("trailingEps", 0)
        forward_eps = info.get("forwardEps", 0)
        trailing_pe = info.get("trailingPE", 0)
        forward_pe = info.get("forwardPE", 0)
        book_value = info.get("bookValue", 0)
        price_to_book = info.get("priceToBook", 0)
        revenue_growth = info.get("revenueGrowth", 0)
        earnings_growth = info.get("earningsGrowth", 0)
        
        # 簡單評估邏輯
        evaluation = "中性"
        if forward_eps > trailing_eps and earnings_growth > 0:
            evaluation = "正向成長"
        elif forward_eps < trailing_eps and earnings_growth < 0:
            evaluation = "衰退風險"
            
        summary = f"目前近四季EPS為 {trailing_eps}，預估未來EPS為 {forward_eps}。盈餘成長率預測為 {earnings_growth*100:.1f}%。"
        if evaluation == "正向成長":
            summary += " 顯示公司具備良好的獲利成長動能，適合偏多操作。"
        elif evaluation == "衰退風險":
            summary += " 顯示公司未來獲利可能面臨衰退，建議保守評估。"
        else:
            summary += " 獲利表現相對平穩，建議搭配技術面觀察。"
            
        return {
            "success": True,
            "data": {
                "trailing_eps": trailing_eps,
                "forward_eps": forward_eps,
                "trailing_pe": trailing_pe,
                "forward_pe": forward_pe,
                "book_value": book_value,
                "price_to_book": price_to_book,
                "revenue_growth": revenue_growth,
                "earnings_growth": earnings_growth,
                "evaluation": evaluation,
                "summary": summary
            }
        }
    except Exception as e:
        return {"success": False, "error": str(e)}
