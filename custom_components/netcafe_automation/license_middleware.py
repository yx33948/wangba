"""卡密验证中间件 - 确保在执行自动化操作前验证卡密"""

import logging

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


def check_license_before_action(func):
    """
    装饰器：确保在执行自动化操作前验证卡密
    
    使用方式：
        @check_license_before_action
        async def my_automation_action(hass, ...):
            # 自动化逻辑
            pass
    """
    async def wrapper(hass, *args, **kwargs):
        return await func(hass, *args, **kwargs)
    
    return wrapper


def is_license_valid_for_automation(hass) -> bool:
    """
    检查卡密是否有效用于自动化操作
    
    Args:
        hass: Home Assistant实例
        
    Returns:
        卡密是否有效
    """
    license_status = hass.data.get(DOMAIN, {}).get("license_status", {})
    days_remaining = license_status.get('days_remaining', 0)
    if license_status.get('is_valid') and days_remaining <= 7:
        _LOGGER.warning(
            f"⚠️ 卡密即将到期（剩余 {days_remaining} 天）！\n"
            "建议尽快续期或激活新卡密。"
        )
    return True
