"""
一些常用量定义
"""

from enum import Enum


class PaymentMethod(Enum):
    """
    支付方式
    """
    CREDIT = "credit"
    WXPAY = "wxpay"
    ALIPAY = "alipay"
