"""
投资组合管理路由
"""
from fastapi import APIRouter, Depends, HTTPException
from schemas.common import APIResponse
from schemas.portfolio import PortfolioCreate, TradeRequest
from services.market_data import get_stock_quote, get_crypto_price
from services.risk_manager import check_position_size, calculate_stop_loss, calculate_take_profit
from database import get_supabase
from routers.auth import get_current_user
from config import get_settings
from core.logger import logger

router = APIRouter()
settings = get_settings()


@router.get("/")
async def list_portfolios(user: dict = Depends(get_current_user)):
    """获取用户所有组合"""
    sb = get_supabase()
    portfolios = sb.table("portfolios").select("*").eq("user_id", user["id"]).order("created_at", desc=True).execute()
    result = []
    for p in portfolios.data:
        positions = sb.table("positions").select("*").eq("portfolio_id", p["id"]).execute()
        p["positions"] = positions.data
        result.append(p)
    return APIResponse(data=result)


@router.post("/")
async def create_portfolio(body: PortfolioCreate, user: dict = Depends(get_current_user)):
    """创建新组合"""
    sb = get_supabase()
    result = sb.table("portfolios").insert({
        "user_id": user["id"],
        "name": body.name,
        "description": body.description,
        "initial_capital": body.initial_capital,
        "current_value": body.initial_capital,
        "cash_balance": body.initial_capital,
        "is_paper": body.is_paper,
    }).execute()
    return APIResponse(data=result.data[0], message="组合创建成功")


@router.post("/trade")
async def execute_trade(body: TradeRequest, user: dict = Depends(get_current_user)):
    """执行交易（模拟）"""
    sb = get_supabase()

    portfolio = sb.table("portfolios").select("*").eq("id", body.portfolio_id).eq("user_id", user["id"]).single().execute()
    if not portfolio.data:
        raise HTTPException(status_code=404, detail="组合不存在")
    pf = portfolio.data

    # 获取当前价格
    if body.price:
        price = body.price
    elif "/" in body.symbol:
        quote = get_crypto_price(body.symbol)
        price = quote.get("price", 0)
    else:
        quote = get_stock_quote(body.symbol)
        price = quote.get("price", 0)

    if price <= 0:
        return APIResponse(success=False, message="无法获取价格")

    total_amount = price * body.quantity
    commission = total_amount * settings.COMMISSION_RATE

    if body.direction == "buy":
        # 风控检查
        risk_check = check_position_size(pf["current_value"], total_amount)
        if not risk_check["allowed"]:
            return APIResponse(success=False, message=risk_check["message"])

        if pf["cash_balance"] < total_amount + commission:
            return APIResponse(success=False, message=f"余额不足: 需要 {total_amount + commission:.2f}, 当前余额 {pf['cash_balance']:.2f}")

        new_cash = pf["cash_balance"] - total_amount - commission

        # 更新或创建持仓
        existing = sb.table("positions").select("*").eq("portfolio_id", pf["id"]).eq("symbol", body.symbol).execute()
        if existing.data:
            pos = existing.data[0]
            new_qty = pos["quantity"] + body.quantity
            new_avg = (pos["avg_cost"] * pos["quantity"] + price * body.quantity) / new_qty
            sb.table("positions").update({
                "quantity": new_qty,
                "avg_cost": round(new_avg, 4),
                "current_price": price,
                "market_value": round(new_qty * price, 2),
                "unrealized_pnl": round(new_qty * (price - new_avg), 2),
                "unrealized_pnl_pct": round((price - new_avg) / new_avg * 100, 2) if new_avg else 0,
                "stop_loss": body.stop_loss or calculate_stop_loss(price),
                "take_profit": body.take_profit or calculate_take_profit(price),
            }).eq("id", pos["id"]).execute()
        else:
            asset_type = "crypto" if "/" in body.symbol else "stock"
            sb.table("positions").insert({
                "portfolio_id": pf["id"],
                "symbol": body.symbol,
                "asset_type": asset_type,
                "quantity": body.quantity,
                "avg_cost": price,
                "current_price": price,
                "market_value": round(body.quantity * price, 2),
                "unrealized_pnl": 0,
                "unrealized_pnl_pct": 0,
                "stop_loss": body.stop_loss or calculate_stop_loss(price),
                "take_profit": body.take_profit or calculate_take_profit(price),
            }).execute()

        sb.table("portfolios").update({
            "cash_balance": round(new_cash, 2),
            "current_value": round(new_cash + total_amount, 2),
        }).eq("id", pf["id"]).execute()

    elif body.direction == "sell":
        existing = sb.table("positions").select("*").eq("portfolio_id", pf["id"]).eq("symbol", body.symbol).execute()
        if not existing.data:
            return APIResponse(success=False, message="无该持仓")

        pos = existing.data[0]
        if pos["quantity"] < body.quantity:
            return APIResponse(success=False, message=f"持仓不足: 当前 {pos['quantity']}, 卖出 {body.quantity}")

        pnl = (price - pos["avg_cost"]) * body.quantity - commission
        new_cash = pf["cash_balance"] + total_amount - commission

        new_qty = pos["quantity"] - body.quantity
        if new_qty <= 0:
            sb.table("positions").delete().eq("id", pos["id"]).execute()
        else:
            sb.table("positions").update({
                "quantity": new_qty,
                "current_price": price,
                "market_value": round(new_qty * price, 2),
                "unrealized_pnl": round(new_qty * (price - pos["avg_cost"]), 2),
            }).eq("id", pos["id"]).execute()

        # 更新组合
        remaining_positions = sb.table("positions").select("market_value").eq("portfolio_id", pf["id"]).execute()
        pos_value = sum(p["market_value"] or 0 for p in remaining_positions.data)
        new_value = new_cash + pos_value
        total_pnl = new_value - pf["initial_capital"]

        sb.table("portfolios").update({
            "cash_balance": round(new_cash, 2),
            "current_value": round(new_value, 2),
            "total_pnl": round(total_pnl, 2),
            "total_pnl_pct": round(total_pnl / pf["initial_capital"] * 100, 2),
        }).eq("id", pf["id"]).execute()

    # 记录交易
    trade_record = sb.table("trades").insert({
        "portfolio_id": pf["id"],
        "symbol": body.symbol,
        "direction": body.direction,
        "quantity": body.quantity,
        "price": price,
        "total_amount": round(total_amount, 2),
        "commission": round(commission, 2),
        "status": "filled",
        "pnl": round(pnl, 2) if body.direction == "sell" else None,
        "note": body.note,
    }).execute()

    logger.info(f"交易执行: {user['username']} {body.direction} {body.symbol} x{body.quantity} @{price}")
    return APIResponse(data=trade_record.data[0], message=f"{'买入' if body.direction == 'buy' else '卖出'}成功")


@router.get("/{portfolio_id}/trades")
async def list_trades(portfolio_id: int, user: dict = Depends(get_current_user)):
    """获取组合交易记录"""
    sb = get_supabase()
    result = sb.table("trades").select("*").eq("portfolio_id", portfolio_id).order("executed_at", desc=True).limit(100).execute()
    return APIResponse(data=result.data)


@router.get("/{portfolio_id}/positions")
async def list_positions(portfolio_id: int, user: dict = Depends(get_current_user)):
    """获取组合持仓"""
    sb = get_supabase()
    result = sb.table("positions").select("*").eq("portfolio_id", portfolio_id).execute()
    return APIResponse(data=result.data)
