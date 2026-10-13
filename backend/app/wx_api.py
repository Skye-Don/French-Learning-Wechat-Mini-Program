# 微信服务端 API 封装（jscode2session）
# 官方文档：https://developers.weixin.qq.com/miniprogram/dev/OpenApiDoc/user-login/code2Session.html
# 红线：AppSecret 只存在服务端 .env；本模块禁止打日志输出 openid/session_key
import httpx

from .config import settings

JSCODE2SESSION_URL = "https://api.weixin.qq.com/sns/jscode2session"
WX_LOGIN_TIMEOUT = 5.0  # PRD 5.1：微信登录接口超时 5 秒


class WxLoginError(Exception):
    """微信登录失败（网络/invalid code/接口错误）"""


async def code_to_openid(code: str) -> dict:
    """
    用 wx.login 的临时 code 换 openid。
    返回 {"openid": ..., "session_key": ..., "unionid": ...}
    失败抛 WxLoginError，由路由层转成 401/502。
    """
    params = {
        "appid": settings.WX_APPID,
        "secret": settings.WX_SECRET,
        "js_code": code,
        "grant_type": "authorization_code",
    }
    try:
        async with httpx.AsyncClient(timeout=WX_LOGIN_TIMEOUT) as client:
            resp = await client.get(JSCODE2SESSION_URL, params=params)
            resp.raise_for_status()
            data = resp.json()
    except Exception as e:
        raise WxLoginError("微信登录接口请求失败") from e

    if data.get("errcode"):
        # 常见：40029 invalid code / 45011 频率限制
        raise WxLoginError(f"code 换取 openid 失败: errcode={data.get('errcode')}")
    if not data.get("openid"):
        raise WxLoginError("微信登录返回缺少 openid")
    return data
