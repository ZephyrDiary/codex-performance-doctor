---
name: codex-performance-doctor
description: Use when Codex feels slow or hot, logs_2.sqlite or its WAL appears to grow excessively, or a workspace may contain incomplete Git metadata, oversized .git directories, tmp_pack_* or tmp_obj_* files.
---

# Codex Performance Doctor / Codex 性能排查

默认只读，先收集证据。修复不是自动清理。 / Read-only first; evidence before intervention. Repair is not automatic cleanup.

## Boundaries / 边界

- 仅检查用户指定的工作区和 Codex 数据目录；不要扫描整盘。 / Stay within the requested workspace and Codex data directory.
- 不读取日志正文、请求内容或令牌；不上传诊断结果。 / Do not read log bodies, requests or tokens, or upload diagnostic results.
- 未经具体授权，不修改数据库、不 checkpoint、不移动或删除文件、不结束进程、不创建定时任务。 / Require explicit authorization for database changes, checkpoints, moves, deletions, process termination or schedules.
- 缺失、锁定、无权限或未知结构应如实报告，禁止创建空数据库或绕过限制。 / Report missing, locked, inaccessible or incompatible databases; never create a replacement or bypass restrictions.

## Inspect / 排查

1. 确认系统、工作区绝对路径及数据库位置。优先检查 `CODEX_HOME`，否则使用 `~/.codex`；不要假设此前机器上的路径仍有效。 / Resolve the OS, absolute workspace and active database path using `CODEX_HOME` or `~/.codex`; verify current existence.
2. 在 Skill 目录运行 `python -B scripts/inspect_logs.py --db "<absolute database path>" --seconds 15`。只有 Python 标准库依赖。 / Run the bundled inspector from the skill directory; it requires only Python 3 standard libraries.
3. 比较前后行数、总 `MAX(id)`、TRACE 行数与最大 ID，以及 DB/WAL 的字节大小和修改时间；记录查询起点间隔及时间不确定性范围，文件状态在查询后读取。 / Compare counts, overall and TRACE maximum IDs, DB/WAL bytes and timestamps; report query-start intervals and timing bounds. File stats are observed after each query.
4. 按 [Git 检查说明 / Git checks](references/git-checks.md) 检查工作区和子目录。 / Inspect Git metadata using the linked reference.

只读连接使用 `mode=ro` 和 `query_only`，不执行 checkpoint 或 VACUUM。活动 WAL 禁用 `immutable=1`。SQLite 可能参与 SHM 锁管理；不承诺取证级零文件写入。若用户要求物理零写入，应停止活动库 SQL 检查并先商议离线取证。 / Use read-only connections, never immutable mode on a live WAL database. SQLite SHM coordination means this is not a forensic zero-write guarantee.

## Interpret / 判断

- WAL 大小不变不等于没有写盘；WAL 可循环复用。 / A fixed WAL size does not prove absence of writes; WAL can be reused.
- 保留策略可能使行数下降而 ID 上升；ID 增量也不等于精确插入数。 / Retention can lower row counts while IDs rise; ID deltas are not exact insert counts.
- TRACE 最大 ID 不变仅说明采样期未观察到新增保留的 TRACE，不证明所有写入停止。 / A stable TRACE maximum only indicates no newly retained TRACE rows were observed.
- 数据库体积、逻辑增长和 CPU 累计时间不能单独证明发热根因。需要时经用户同意采样进程 CPU 差值、物理磁盘 I/O 和内存压力。 / Sizes, logical growth and cumulative CPU time alone cannot establish thermal causation; use timed process and system metrics when needed.

用用户语言给出风险等级、采样证据、发现的问题、未验证事项和下一步。无数据或权限不足写“未知”，不要判为低风险；只发现活动写入不能判为高风险。 / Report risk, timed evidence, findings, unknowns and next steps. Unknown is not low risk; activity alone is not high risk.

## Repair / 修复

仅在用户明确选择修复后阅读 [修复说明 / Repair guidance](references/repair.md)。备份成功且验证后才允许变更。 / Read the repair reference only after explicit repair authorization; verify a backup before changes.
