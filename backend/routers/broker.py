"""
交易账户管理 + 实盘交易路由
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, timezone

from schemas.common import APIResponse
from database import get_supabase
from routers.auth import get_current_user
from services.brokers.factory import get_broker, create_broker, get_supported_brokers
from core.logger import logger

router = APIRouter()


# ---------- 模型 ----------

class BrokerAccountCreate(BaseModel):
    name: str
    broker_type: str
    api_key: str
    api_secret: str
    passphrase: str = ""
    is_testnet: bool = False
    extra_config: dict = {}


class LiveOrderRequest(BaseModel):
    broker_account_id: int
    symbol: str
    side: str  # buy / sell
    quantity: float
    order_type: str = "market"
    price: Optional[float] = None
    confirm_real_trade: bool = False


# ---------- 交易所/券商列表 ----------

@router.get("/supported")
async def list_supported():
    """获取支持的交易所/券商列表"""
    return APIResponse(data=get_supported_brokers())


# ---------- 账户管理 ----------

@router.get("/accounts")
async def list_accounts(user: dict = Depends(get_current_user)):
    """获取用户所有交易账户"""
    sb = get_supabase()
    result = sb.table("broker_accounts").select(
        "id, name, broker_type, is_active, is_testnet, connection_status, balance_cache, last_connected_at, created_at"
    ).eq("user_id", user["id"]).order("created_at", desc=True).execute()
    return APIResponse(data=result.data)


@router.post("/accounts")
async def create_account(body: BrokerAccountCreate, user: dict = Depends(get_current_user)):
    """添加交易账户"""
    sb = get_supabase()

    result = sb.table("broker_accounts").insert({
        "user_id": user["id"],
        "name": body.name,
        "broker_type": body.broker_type,
        "api_key": body.api_key,
        "api_secret": body.api_secret,
        "passphrase": body.passphrase,
        "is_testnet": body.is_testnet,
        "extra_config": body.extra_config,
    }).execute()

    logger.info(f"用户 {user['username']} 添加交易账户: {body.name} ({body.broker_type})")
    return APIResponse(
        data={"id": result.data[0]["id"], "name": body.name, "broker_type": body.broker_type},
        message="交易账户添加成功",
    )


@router.delete("/accounts/{account_id}")
async def delete_account(account_id: int, user: dict = Depends(get_current_user)):
    """删除交易账户"""
    sb = get_supabase()
    sb.table("broker_accounts").delete().eq("id", account_id).eq("user_id", user["id"]).execute()
    return APIResponse(message="账户已删除")


@router.post("/accounts/{account_id}/test")
async def test_connection(account_id: int, user: dict = Depends(get_current_user)):
    """测试交易账户连接"""
    sb = get_supabase()
    acc = sb.table("broker_accounts").select("*").eq("id", account_id).eq("user_id", user["id"]).single().execute()
    if not acc.data:
        raise HTTPException(status_code=404, detail="账户不存在")

    try:
        broker = create_broker(
            broker_type=acc.data["broker_type"],
            api_key=acc.data["api_key"],
            api_secret=acc.data["api_secret"],
            passphrase=acc.data.get("passphrase", ""),
            testnet=acc.data.get("is_testnet", False),
        )
        ok = await broker.connect()
        await broker.close()

        status = "connected" if ok else "failed"
        sb.table("broker_accounts").update({
            "connection_status": status,
            "last_connected_at": datetime.now(timezone.utc).isoformat(),
        }).eq("id", account_id).execute()

        return APIResponse(data={"connected": ok, "status": status}, message="连接成功" if ok else "连接失败")
    except Exception as e:
        sb.table("broker_accounts").update({"connection_status": "error"}).eq("id", account_id).execute()
        return APIResponse(success=False, message=f"连接异常: {str(e)}")


@router.get("/accounts/{account_id}/balance")
async def get_balance(account_id: int, user: dict = Depends(get_current_user)):
    """查询账户余额和持仓"""
    try:
        broker = await get_broker(account_id)
        balance = await broker.get_balance()
        await broker.close()

        sb = get_supabase()
        sb.table("broker_accounts").update({
            "balance_cache": {
                "total_equity": balance.total_equity,
                "available_balance": balance.available_balance,
                "positions_count": len(balance.positions),
            },
            "connection_status": "connected",
            "last_connected_at": datetime.now(timezone.utc).isoformat(),
        }).eq("id", account_id).execute()

        return APIResponse(data={
            "total_equity": balance.total_equity,
            "available_balance": balance.available_balance,
            "positions": balance.positions,
        })
    except Exception as e:
        return APIResponse(success=False, message=str(e))


# ---------- 实盘交易 ----------

@router.post("/trade")
async def place_live_order(body: LiveOrderRequest, user: dict = Depends(get_current_user)):
    """实盘下单"""
    if not body.confirm_real_trade:
        return APIResponse(
            success=False,
            message="⚠️ 实盘交易确认: 此操作将使用真实资金在交易所下单。"
                    "请设置 confirm_real_trade=true 确认执行。"
        )

    sb = get_supabase()
    acc = sb.table("broker_accounts").select("*").eq("id", body.broker_account_id).eq("user_id", user["id"]).single().execute()
    if not acc.data:
        raise HTTPException(status_code=404, detail="交易账户不存在")

    # 创建订单记录
    order_record = sb.table("live_orders").insert({
        "user_id": user["id"],
        "broker_account_id": body.broker_account_id,
        "symbol": body.symbol,
        "side": body.side,
        "order_type": body.order_type,
        "quantity": body.quantity,
        "price": body.price,
        "status": "submitting",
        "source": "manual",
    }).execute()
    order_id = order_record.data[0]["id"]

    try:
        broker = await get_broker(body.broker_account_id)
        result = await broker.place_order(
            symbol=body.symbol,
            side=body.side,
            quantity=body.quantity,
            order_type=body.order_type,
            price=body.price,
        )
        await broker.close()

        sb.table("live_orders").update({
            "exchange_order_id": result.order_id,
            "filled_quantity": result.filled_quantity,
            "filled_price": result.filled_price,
            "commission": result.commission,
            "status": "filled" if result.success else "failed",
            "error_message": result.error if not result.success else None,
        }).eq("id", order_id).execute()

        if result.success:
            logger.info(f"实盘交易: {user['username']} {body.side} {body.symbol} x{body.quantity} -> {result.status}")
            return APIResponse(data={
                "order_id": order_id,
                "exchange_order_id": result.order_id,
                "status": result.status,
                "filled_quantity": result.filled_quantity,
                "filled_price": result.filled_price,
                "commission": result.commission,
            }, message="下单成功")
        else:
            return APIResponse(success=False, message=f"下单失败: {result.error}")

    except Exception as e:
        sb.table("live_orders").update({"status": "error", "error_message": str(e)}).eq("id", order_id).execute()
        logger.error(f"实盘下单异常: {e}")
        return APIResponse(success=False, message=f"下单异常: {str(e)}")


@router.get("/orders")
async def list_orders(user: dict = Depends(get_current_user), limit: int = 50):
    """查询实盘订单记录"""
    sb = get_supabase()
    result = sb.table("live_orders").select("*").eq("user_id", user["id"]).order("created_at", desc=True).limit(limit).execute()
    return APIResponse(data=result.data)


@router.post("/orders/{order_id}/cancel")
async def cancel_live_order(order_id: int, user: dict = Depends(get_current_user)):
    """撤销实盘订单"""
    sb = get_supabase()
    order = sb.table("live_orders").select("*").eq("id", order_id).eq("user_id", user["id"]).single().execute()
    if not order.data:
        raise HTTPException(status_code=404, detail="订单不存在")

    o = order.data
    if not o.get("exchange_order_id"):
        return APIResponse(success=False, message="无交易所订单号，无法撤单")

    try:
        broker = await get_broker(o["broker_account_id"])
        ok = await broker.cancel_order(o["exchange_order_id"], o["symbol"])
        await broker.close()

        if ok:
            sb.table("live_orders").update({"status": "cancelled"}).eq("id", order_id).execute()
            return APIResponse(message="撤单成功")
        return APIResponse(success=False, message="撤单失败")
    except Exception as e:
        return APIResponse(success=False, message=str(e))
