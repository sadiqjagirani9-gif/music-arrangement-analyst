from __future__ import annotations

from pathlib import Path


def separate_stems(path: str | Path, output_dir: str | Path) -> dict:
    """Run Demucs when installed; otherwise return an explicit degradation result."""
    try:
        import demucs  # type: ignore  # noqa: F401
    except (ImportError, ModuleNotFoundError):
        return {"status": "unavailable", "message": "Demucs 未安装；请安装 demucs 后重试，原始音频未被修改。", "stems": []}
    return {"status": "queued", "message": "Demucs 可用，请通过任务队列运行分离。", "stems": [], "input": str(path), "output_dir": str(output_dir)}
