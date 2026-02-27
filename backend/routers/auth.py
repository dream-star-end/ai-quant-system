"""
认证路由 - 注册/登录/用户信息
"""
from fastapi import APIRouter, HTTPException, Depends, Request
from schemas.user import UserRegister, UserLogin, UserResponse, TokenResponse
from schemas.common import APIResponse
from core.security import hash_password, verify_password, create_access_token, decode_access_token
from database import get_supabase
from core.logger import logger

router = APIRouter()


async def get_current_user(request: Request) -> dict:
    """从 Authorization header 解析当前用户"""
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="未登录")
    token = auth.split(" ", 1)[1]
    payload = decode_access_token(token)
    if payload is None:
        raise HTTPException(status_code=401, detail="Token 无效或已过期")
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Token 无效")

    sb = get_supabase()
    result = sb.table("users").select("*").eq("id", int(user_id)).single().execute()
    if not result.data:
        raise HTTPException(status_code=401, detail="用户不存在")
    return result.data


@router.post("/register", response_model=APIResponse)
async def register(body: UserRegister):
    sb = get_supabase()
    existing = sb.table("users").select("id").eq("username", body.username).execute()
    if existing.data:
        raise HTTPException(status_code=400, detail="用户名已存在")

    existing_email = sb.table("users").select("id").eq("email", body.email).execute()
    if existing_email.data:
        raise HTTPException(status_code=400, detail="邮箱已注册")

    hashed = hash_password(body.password)
    result = sb.table("users").insert({
        "username": body.username,
        "email": body.email,
        "hashed_password": hashed,
    }).execute()

    user = result.data[0]
    logger.info(f"新用户注册: {body.username}")

    # 自动创建默认模拟组合
    sb.table("portfolios").insert({
        "user_id": user["id"],
        "name": "默认模拟组合",
        "description": "系统自动创建的模拟交易组合",
        "initial_capital": 1000000.0,
        "current_value": 1000000.0,
        "cash_balance": 1000000.0,
        "is_paper": True,
    }).execute()

    # 自动创建默认自选
    sb.table("watchlists").insert({
        "user_id": user["id"],
        "name": "默认自选",
        "symbols": ["000300.SS", "600519.SS", "BTC/USDT", "ETH/USDT"],
    }).execute()

    token = create_access_token({"sub": str(user["id"])})
    return APIResponse(
        data={
            "access_token": token,
            "token_type": "bearer",
            "user": {
                "id": user["id"],
                "username": user["username"],
                "email": user["email"],
                "is_active": user["is_active"],
            },
        },
        message="注册成功",
    )


@router.post("/login", response_model=APIResponse)
async def login(body: UserLogin):
    sb = get_supabase()
    result = sb.table("users").select("*").eq("username", body.username).execute()
    if not result.data:
        raise HTTPException(status_code=401, detail="用户名或密码错误")

    user = result.data[0]
    if not verify_password(body.password, user["hashed_password"]):
        raise HTTPException(status_code=401, detail="用户名或密码错误")

    token = create_access_token({"sub": str(user["id"])})
    logger.info(f"用户登录: {body.username}")
    return APIResponse(
        data={
            "access_token": token,
            "token_type": "bearer",
            "user": {
                "id": user["id"],
                "username": user["username"],
                "email": user["email"],
                "is_active": user["is_active"],
            },
        },
        message="登录成功",
    )


@router.get("/me", response_model=APIResponse)
async def get_me(user: dict = Depends(get_current_user)):
    return APIResponse(data={
        "id": user["id"],
        "username": user["username"],
        "email": user["email"],
        "is_active": user["is_active"],
        "preferences": user.get("preferences", {}),
        "created_at": user.get("created_at"),
    })
