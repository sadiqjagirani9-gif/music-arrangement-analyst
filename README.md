# Music Arrangement Analyst

Music Arrangement Analyst 是一个面向编曲分析的本地优先工具：读取音频，提取可测特征，给出带置信度的调性/和声/曲式/乐器候选，生成 DAW 风格时间轴数据和可编辑 MIDI 编曲草案。

## 已实现

- WAV 原生读取；安装 `librosa` 后支持 MP3、FLAC、M4A 以及 BPM、Chroma、MFCC、频谱、动态范围等特征。
- 保守的调性、和弦、节奏和曲式推断，所有推断均带证据/置信度并标明限制。
- FastAPI 上传、分析、报告、MIDI 和音轨分离降级接口。
- React + TypeScript + Vite 时间轴界面：结构段落、轨道候选、置信度、报告下载。
- 标准 MIDI Type-1 导出：`Chords.mid`、`Bass.mid`、`Drums.mid`、`Melody.mid`、`Full_Arrangement.mid`。这些是可编辑草案，不是原曲完整复原。
- Codex Skill 和音乐制作知识库；pytest 单元测试覆盖音频、调性、和弦、时间轴、MIDI。

## 安装与运行

```bash
python -m venv .venv
# macOS/Linux: source .venv/bin/activate
# Windows: .venv\Scripts\activate
pip install -r backend/requirements.txt
uvicorn backend.main:app --reload --port 8000
```

前端：

```bash
cd frontend
npm install
npm run dev
```

浏览器打开 `http://localhost:5173`。前端可通过 `VITE_API_URL` 指向其他后端地址。

## API

- `GET /api/health`
- `POST /api/analyze`：multipart 字段 `file`
- `GET /api/analysis/{id}`
- `GET /api/analysis/{id}/report.md`
- `POST /api/analysis/{id}/midi`
- `POST /api/separate`：Demucs 未安装时返回明确的降级状态，不伪造分离结果。

## Skill

将 `skill/music-arrangement-analyst` 复制到 Codex skills 目录，按其中 `SKILL.md` 的命令运行本地分析。Skill 不依赖 Web 服务才能完成 WAV 基础分析。

## 测试

```bash
pytest -q
ruff check backend tests
```

真实 Demucs 模型是可选依赖，会下载较大的模型权重；测试默认不下载它。项目不包含用户歌曲、API Key、模型权重或未经授权的数据集。

## 限制与免责声明

在没有多轨、训练模型或人工复核时，具体乐器、和弦转位、混音手法和曲式边界只能是候选推断。请检查版权与模型许可证后再发布分析结果或 MIDI。

## 许可证

MIT，见 `LICENSE`。第三方库和模型仍受各自许可证约束。
