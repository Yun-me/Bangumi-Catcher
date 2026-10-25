"""Local snapshots and user input shared by the desktop and CLI."""

from __future__ import annotations

import json
import re
from pathlib import Path
from urllib.parse import unquote, urlparse

from ..core.models import UserCollection

SUBJECT_TYPES = {2: "动画", 1: "书籍", 3: "音乐", 4: "游戏", 6: "三次元"}
MAX_IMPORT_BYTES = 64 * 1024 * 1024


def normalize_username(value: str) -> str:
    username = value.strip()
    if "://" in username or username.startswith(("bgm.tv/", "bangumi.tv/", "chii.in/")):
        parsed = urlparse(username if "://" in username else f"https://{username}")
        if parsed.scheme not in {"http", "https"} or parsed.hostname not in {
            "bgm.tv", "bangumi.tv", "chii.in", "www.bgm.tv", "www.bangumi.tv", "www.chii.in",
        }:
            raise ValueError("请粘贴 Bangumi 用户主页链接，或直接输入用户名 / UID。")
        parts = parsed.path.strip("/").split("/")
        if len(parts) != 2 or parts[0] != "user":
            raise ValueError("用户主页链接应为 https://bgm.tv/user/用户名。")
        username = unquote(parts[1])
    if not re.fullmatch(r"[A-Za-z0-9_-]+", username):
        raise ValueError("请输入有效的用户名 / UID（不是昵称），也可以粘贴用户主页链接。")
    return username


def load_collection(path: str | Path) -> UserCollection:
    source = Path(path)
    with source.open("rb") as stream:
        payload = stream.read(MAX_IMPORT_BYTES + 1)
    if len(payload) > MAX_IMPORT_BYTES:
        raise ValueError("JSON 文件超过 64 MB，请拆分后导入。")
    data = json.loads(payload.decode("utf-8-sig"))
    if not isinstance(data, dict) or not isinstance(data.get("items"), list) or not data.get("username"):
        raise ValueError("请选择本应用导出的收藏 JSON（含 username 和 items），而非报告 JSON。")
    collection = UserCollection.model_validate(data)
    collection.total = len(collection.items)
    return collection
