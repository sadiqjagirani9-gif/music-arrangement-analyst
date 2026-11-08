from __future__ import annotations

import json
import os
import secrets
import time
import urllib.parse
import urllib.request

from backend.sources.qq_music.qq_models import QQAuthStatus


class QQAuth:
    """Optional QQ Connect OAuth identity authorization.

    QQ Connect is an official OAuth mechanism, but it does not grant QQ Music
    membership or audio entitlements. Tokens are stored in the OS keyring and
    are never logged. Password and cookie based login are intentionally absent.
    """

    service_name = "music-arrangement-analyst.qq-connect"

    def __init__(self):
        self.client_id = os.getenv("QQ_CONNECT_APP_ID", "")
        self.client_secret = os.getenv("QQ_CONNECT_APP_KEY", "")
        self.redirect_uri = os.getenv("QQ_CONNECT_REDIRECT_URI", "http://127.0.0.1:8000/api/sources/qq/auth/callback")
        self._states: dict[str, float] = {}

    @property
    def configured(self) -> bool:
        return bool(self.client_id and self.client_secret and self.redirect_uri)

    def _keyring(self):
        try:
            import keyring
            return keyring
        except ImportError as exc:
            raise RuntimeError("keyring 未安装，无法安全保存授权凭据") from exc

    def status(self) -> QQAuthStatus:
        if not self.configured:
            return QQAuthStatus(False, False, False, message="未配置 QQ Connect 应用；搜索不需要登录。")
        raw = self._keyring().get_password(self.service_name, self.client_id)
        if not raw:
            return QQAuthStatus(True, False, False, message="尚未授权；搜索仍可使用。")
        try:
            token = json.loads(raw)
            expired = float(token.get("expires_at") or 0) <= time.time()
        except (ValueError, TypeError):
            return QQAuthStatus(True, False, True, message="本地授权凭据损坏，请退出后重新授权。")
        return QQAuthStatus(True, not expired, expired, message="授权已失效，请重新授权。" if expired else "QQ Connect 身份授权有效；不代表拥有 QQ 音乐会员音频权限。")

    def authorization_url(self) -> str:
        if not self.configured:
            raise RuntimeError("请先配置 QQ_CONNECT_APP_ID、QQ_CONNECT_APP_KEY 和 QQ_CONNECT_REDIRECT_URI")
        state = secrets.token_urlsafe(24)
        self._states[state] = time.time() + 600
        params = {"response_type": "code", "client_id": self.client_id, "redirect_uri": self.redirect_uri, "state": state, "scope": "get_user_info"}
        return f"https://graph.qq.com/oauth2.0/authorize?{urllib.parse.urlencode(params)}"

    def handle_callback(self, code: str, state: str) -> QQAuthStatus:
        expires = self._states.pop(state, 0)
        if not expires or expires < time.time():
            raise RuntimeError("授权 state 无效或已过期")
        params = urllib.parse.urlencode({"grant_type": "authorization_code", "client_id": self.client_id, "client_secret": self.client_secret, "code": code, "redirect_uri": self.redirect_uri, "fmt": "json"})
        request = urllib.request.Request(f"https://graph.qq.com/oauth2.0/token?{params}", headers={"User-Agent": "Music Arrangement Analyst"})
        with urllib.request.urlopen(request, timeout=15) as response:
            payload = json.loads(response.read().decode())
        token = payload.get("access_token")
        if not token:
            raise RuntimeError("QQ Connect 授权失败或未返回 access_token")
        safe_value = json.dumps({"access_token": token, "expires_at": time.time() + int(payload.get("expires_in") or 0), "refresh_token": payload.get("refresh_token")})
        self._keyring().set_password(self.service_name, self.client_id, safe_value)
        return self.status()

    def logout(self) -> QQAuthStatus:
        if self.configured:
            keyring = self._keyring()
            if keyring.get_password(self.service_name, self.client_id):
                keyring.delete_password(self.service_name, self.client_id)
        return self.status()
