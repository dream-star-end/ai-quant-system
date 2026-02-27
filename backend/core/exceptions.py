"""
自定义异常类和全局异常处理
"""
from fastapi import HTTPException, status


class QuantBaseException(HTTPException):
    def __init__(self, detail: str, status_code: int = 400):
        super().__init__(status_code=status_code, detail=detail)


class DataFetchError(QuantBaseException):
    def __init__(self, source: str, detail: str = ""):
        super().__init__(
            detail=f"数据获取失败 [{source}]: {detail}",
            status_code=status.HTTP_502_BAD_GATEWAY,
        )


class StrategyError(QuantBaseException):
    def __init__(self, detail: str):
        super().__init__(detail=f"策略错误: {detail}", status_code=400)


class BacktestError(QuantBaseException):
    def __init__(self, detail: str):
        super().__init__(detail=f"回测错误: {detail}", status_code=400)


class RiskLimitExceeded(QuantBaseException):
    def __init__(self, detail: str):
        super().__init__(detail=f"超出风控限制: {detail}", status_code=403)


class InsufficientData(QuantBaseException):
    def __init__(self, required: int, provided: int):
        super().__init__(
            detail=f"数据不足: 需要至少 {required} 条数据, 当前仅有 {provided} 条",
            status_code=400,
        )


class ResourceNotFound(QuantBaseException):
    def __init__(self, resource: str, identifier: str):
        super().__init__(
            detail=f"未找到{resource}: {identifier}",
            status_code=status.HTTP_404_NOT_FOUND,
        )
