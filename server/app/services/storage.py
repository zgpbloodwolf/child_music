"""文件系统操作:音频/封面落盘、路径计算、删除、时长读取(mutagen)。

与业务逻辑解耦,便于后续替换为对象存储。所有写入都先校验 id 防路径穿越。
"""
import os
import re
import shutil
from pathlib import Path

from mutagen import File as MutagenFile  # 自动识别格式的通用入口

from ..config import settings

# id 仅允许字母数字下划线短横,杜绝 ../ 等路径穿越
ID_RE = re.compile(r"^[A-Za-z0-9_-]+$")


def valid_id(song_id: str) -> bool:
    """校验 id 合法性(防路径穿越与非法文件名)。"""
    return bool(ID_RE.match(song_id or ""))


def song_dir(category_id: str, sub_category_id: str) -> Path:
    """歌曲文件存放目录:storage/library/{category}/{sub_dir}。

    sub_dir 从 sub_category_id 推导:去掉重复的大类前缀(如 children-classic
    → classic);若推导不出(非 {cat}- 前缀)则直接用 sub_category_id 作目录名。
    """
    sub_dir = sub_category_id
    if sub_category_id.startswith(f"{category_id}-"):
        sub_dir = sub_category_id[len(category_id) + 1 :]
    return settings.library_dir / category_id / sub_dir


def write_bytes(data: bytes, dest: Path) -> None:
    """字节内容落盘(自动创建父目录)。"""
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(data)


def copy_file(src: Path, dest: Path) -> None:
    """拷贝文件(自动创建父目录)。"""
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dest)


def link_or_copy(src: Path, dest: Path) -> str:
    """优先硬链接(零拷贝),失败回退拷贝。返回 'link' / 'copy'。"""
    dest.parent.mkdir(parents=True, exist_ok=True)
    try:
        os.link(src, dest)
        return "link"
    except OSError:
        shutil.copy2(src, dest)
        return "copy"


def to_rel(abs_path: Path) -> str:
    """绝对路径 → 相对 storage 根的 POSIX 路径(入库 audio_path/cover_path)。"""
    storage_root = settings.library_dir.parent.resolve()  # .../storage
    return abs_path.resolve().relative_to(storage_root).as_posix()


def read_duration(path: Path) -> float | None:
    """读取音频时长(秒)。支持常见格式;失败或非音频返回 None。"""
    try:
        audio = MutagenFile(str(path))
        if audio is not None and audio.info is not None:
            length = getattr(audio.info, "length", None)
            return float(length) if length is not None else None
    except Exception:
        return None
    return None


def safe_remove(path: Path) -> None:
    """删除文件(不存在则忽略,异常吞掉避免删歌连带 500)。"""
    try:
        path.unlink(missing_ok=True)
    except OSError:
        pass
