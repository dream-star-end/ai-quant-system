"""
路由模块
"""
from fastapi import APIRouter

router = APIRouter()

# 导入各模块路由
from . import stocks, crypto, analysis
