"""通用响应模型"""
from pydantic import BaseModel
from typing import Any, Optional


class APIResponse(BaseModel):
    success: bool = True
    data: Any = None
    message: str = ""


class PaginatedResponse(BaseModel):
    success: bool = True
    data: list = []
    total: int = 0
    page: int = 1
    page_size: int = 20


class ErrorResponse(BaseModel):
    success: bool = False
    error: str
    detail: Optional[str] = None
