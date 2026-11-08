# Music Arrangement Analyst

Music Arrangement Analyst 是一个面向编曲分析的本地优先工具：读取音频，提取可测特征，给出带置信度的调性/和声/曲式/乐器候选，生成 DAW 风格时间轴数据和可编辑 MIDI 编曲草案。

## 已实现

- WAV 原生读取；安装 `librosa` 后支持 MP3、FLAC、M4A 以及 BPM、Chroma、MFCC、频谱、动态范围等特征。
- 保守的调性、和弦、节奏和曲式推断，所有推断均带证据/置信度并标明限制。
- FastAPI 上传、分析、报告、MIDI 和音轨分离降级接口。
- React + TypeScript + Vite 时间轴界面：结构段落、轨道候选、置信度、报告下载。
- 标准 MIDI Type-1 导出：`Chords.mid`、`Bass.mid`、`Drums.mid`、`Melody.mid`、`Full_Arrangement.mid`。这些是可编辑草案，不是原曲完整复原。
- Codex Skill 和音乐制作知识库；pytest 单元测试覆盖音频、调性、和弦、时间轴、MIDI。
- QQ 音乐歌曲搜索、分页、缓存、封面/歌手/专辑/时长/歌曲 MID 展示，以及统一来源任务元数据。
- 对 QQ 音乐公开音频进行权限检查；没有匿名公开地址时保留歌曲信息并引导本地上传，不绕过会员或 DRM。

## 安装与运行

```bash
python -m venv .venv
# macOS/Linux: source .venv/bin/activate
# Windows: .venv\Scripts\activate
pip install -r backend/requirements.txt
uvicorn backend.main:app --reload --port 8000 --no-access-log
```

前端：

```bash
cd frontend
npm install
npm run dev
```

浏览器打开 `http://localhost:5173`。前端可通过 `VITE_API_URL` 指向其他后端地址。

也可运行 `docker compose up --build`，镜像会构建前端并在 `http://localhost:8000` 提供完整界面。

## API

- `GET /api/health`
- `POST /api/analyze`：multipart 字段 `file`
- `GET /api/analysis/{id}`
- `GET /api/analysis/{id}/report.md`
- `POST /api/analysis/{id}/midi`
- `POST /api/separate`：Demucs 未安装时返回明确的降级状态，不伪造分离结果。
- `GET /api/sources/qq/search?q=关键词&scope=all&page=1&page_size=20`
- `GET /api/sources/qq/songs/{song_mid}`
- `POST /api/sources/qq/import`：请求体 `{"song_id":"..."}`；无合法公开音频时返回 HTTP 409。
- `GET /api/sources/qq/auth/status`
- `POST /api/sources/qq/auth/start`、`GET /api/sources/qq/auth/callback`、`POST /api/sources/qq/auth/logout`

## QQ 音乐接入

搜索和歌曲详情使用 QQ 音乐网页当前使用的公开网络端点，并被隔离在 `backend/sources/qq_music` 中。它是**非官方、未承诺长期稳定的网页接口**，不得描述为腾讯官方开放 API。接口变化时，本地文件上传和原分析功能仍可独立使用。

搜索不需要登录。歌曲导入会先读取付费状态，再向 QQ 音乐请求匿名公开播放地址：只有标记为免费且服务器实际返回公开地址时才下载到临时目录分析；会员、付费、无地址或接口失败时均返回“请上传本地音频”。系统不会接收 QQ 密码、Cookie，也不会构造或绕过受限 URL。

可选授权使用官方 QQ Connect OAuth 2.0，仅用于 QQ 身份授权。需自行注册合法的 QQ Connect 应用并设置：

```env
QQ_CONNECT_APP_ID=...
QQ_CONNECT_APP_KEY=...
QQ_CONNECT_REDIRECT_URI=http://127.0.0.1:8000/api/sources/qq/auth/callback
```

Token 使用操作系统 keyring 保存且不写日志。建议保持示例中的 `--no-access-log`，避免 OAuth 回调短期 code 出现在 Web 访问日志中。QQ Connect 身份授权**不授予 QQ 音乐会员或受限音频权限**；未配置授权时搜索仍正常工作。

每个分析任务保存歌曲名、歌手、专辑、封面、来源平台、歌曲 ID、音频来源、SHA-256 和 UTC 分析时间。QQ 音乐歌曲详情不会被重复要求手工填写。

## Skill

将 `skill/music-arrangement-analyst` 复制到 Codex skills 目录，按其中 `SKILL.md` 的命令运行本地分析。Skill 不依赖 Web 服务才能完成 WAV 基础分析。

## 测试

```bash
pytest -q
ruff check backend tests
cd frontend && npm test && npm run build
```

真实 Demucs 模型是可选依赖，会下载较大的模型权重；测试默认不下载它。项目不包含用户歌曲、API Key、模型权重或未经授权的数据集。

## 限制与免责声明

在没有多轨、训练模型或人工复核时，具体乐器、和弦转位、混音手法和曲式边界只能是候选推断。请检查版权与模型许可证后再发布分析结果或 MIDI。

QQ 音乐元数据、封面和音频仍受腾讯及权利人的条款和版权约束。本项目仅提供来源适配和分析工具，不授予下载、复制、传播或规避访问控制的权利。用户应只分析自己合法访问和有权处理的音频。真实账号/OAuth 手动测试见 `docs/qq_music_manual_testing.md`。

常见问题：搜索可用但不能分析通常表示歌曲没有匿名公开音频或属于会员/付费内容；这是预期的版权保护降级，请使用侧栏上传合法本地文件。网页接口返回 503 时稍后重试，原本地分析功能不受影响。

## 许可证

MIT，见 `LICENSE`。第三方库和模型仍受各自许可证约束。

QQ 音乐名称、接口数据和封面不属于本项目 MIT 授权内容。依赖许可证检查记录见 `docs/third_party_licenses.md`。
