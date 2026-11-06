from __future__ import annotations


def build_reasoning(analysis: dict) -> dict:
    return {"provider": "local", "status": "complete", "claims": [
        {"type": "algorithm", "text": f"音频时长 {analysis.get('audio', {}).get('duration', 0)} 秒。"},
        {"type": "algorithm", "text": f"BPM 候选 {analysis.get('audio', {}).get('bpm') or '未知'}。"},
        {"type": "inference", "text": "结构与乐器结果属于启发式候选，需结合分离音轨复核。"},
    ], "limitations": ["未连接外部大模型 API；本报告没有把候选推断包装成确定事实。"]}
