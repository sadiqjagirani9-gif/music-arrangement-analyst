# QQ 音乐手动测试

## 无账号流程

1. 启动 API 和前端，搜索歌曲名、歌手名和专辑名。
2. 检查封面、歌手、专辑、时长和 MID。
3. 翻页后确认 URL 参数改变，重复查询确认响应中的 `cached: true`。
4. 对会员歌曲点击“添加到分析”，应返回本地上传提示且不发起音频下载。
5. 上传合法本地音频后，分析 JSON 的 `source` 应保留 QQ 歌曲信息，`audio_origin` 为 `local_upload`。

## QQ Connect 授权

需要用户自己的 QQ Connect 应用，不纳入自动测试：

1. 配置 `.env` 中三个 `QQ_CONNECT_*` 变量，并在 QQ Connect 控制台登记完全相同的回调地址。
2. 调用 `POST /api/sources/qq/auth/start`，在浏览器完成官方授权。
3. 回调后检查 `GET /api/sources/qq/auth/status`。不得在日志或任务 JSON 中出现 token。
4. 调用 `POST /api/sources/qq/auth/logout`，确认系统 keyring 中凭据被删除。
5. 等待 token 过期或修改 keyring 中的到期时间，确认状态提示重新授权。

QQ Connect 仅证明身份，不应用来解锁 QQ 音乐会员音频。
