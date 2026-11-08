"""QQ Music source integration.

Search uses a reverse-engineered public web endpoint, not an official Tencent
developer API. It is isolated here because compatibility is not guaranteed.
"""

from backend.sources.qq_music.qq_client import QQMusicClient
from backend.sources.qq_music.qq_search import QQSearchService

__all__ = ["QQMusicClient", "QQSearchService"]
