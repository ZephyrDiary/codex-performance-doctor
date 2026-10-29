# Codex Performance Doctor

Codex 越用越卡、风扇转得快？先检查，别急着删除。 / Codex slowing down or running hot? Inspect before cleaning.

一个默认只读的 Codex Skill，检查 `logs_2.sqlite` 的 15 秒逻辑增长，以及工作区 Git 元数据异常。它不证明发热根因，也不是一键清理器。 / A read-only-first Codex skill for timed SQLite log growth and suspicious Git metadata. It does not prove thermal causation and is not a one-click cleaner.

## Install / 安装

在 Codex 中使用已安装的 Skill Installer： / Ask Codex's installed Skill Installer:

```text
Use $skill-installer to install https://github.com/ZephyrDiary/codex-performance-doctor
```

也可将整个仓库目录作为 `codex-performance-doctor` 放入你的 Skill 目录。按客户端要求刷新或重启后确认已加载。 / Alternatively place the complete repository folder in your skill directory and confirm discovery after the refresh or restart required by your client.

## Use / 使用

```text
用 $codex-performance-doctor 只读检查 Codex 日志近15秒的增长，
以及当前工作区的 .git、tmp_pack_*、tmp_obj_*。
不要修改、移动或删除文件。用中文给我风险、证据和建议。
```

```text
Use $codex-performance-doctor to inspect Codex log growth for 15 seconds
and the current workspace's Git metadata. Do not modify, move or delete files.
Report risk, evidence, unknowns and recommended next steps.
```

独立运行日志检测，需要 Python 3.9+，无需安装第三方包： / Standalone log inspection needs Python 3.9+ and no third-party packages:

```text
python -B scripts/inspect_logs.py --seconds 15
python -B scripts/inspect_logs.py --db "<absolute database path>" --seconds 15
```

默认数据库位置是 `CODEX_HOME/logs_2.sqlite`，未设置该环境变量时为 `~/.codex/logs_2.sqlite`。找不到就停止，不创建新库。 / The default uses `CODEX_HOME`, otherwise `~/.codex`; a missing database is never created.

## Safety / 安全约束

- 不输出日志正文，不联网、不上传检测数据、不删除文件。 / No log bodies, networking, diagnostic uploads or file deletion.
- 修复说明是经确认后才能执行的非官方方案，包含在线备份、可选 TRACE trigger 和 WAL checkpoint。 / Repair guidance is an unsupported, consent-gated workaround with a verified online backup first.
- 普通日志仍可写入；WAL 固定大小也可能在持续复用。 / Non-TRACE writes can continue and fixed-size WAL files may be reused.
- 不自动清理 Temp、不创建每周任务、不关闭程序或修改防护设置。 / No automatic Temp cleanup, schedules, app termination or security changes.
- SQLite 只读连接仍可能涉及 SHM 锁管理，不是物理零写入取证工具。 / Read-only SQLite can participate in SHM locking; this is not a forensic zero-write tool.

## Tests / 测试

```text
python -B -m unittest discover -s tests -v
```

测试仅使用模拟数据库，保留生成的临时样本而不删除；不会访问真实 Codex 数据。 / Tests use only synthetic databases and retain temporary fixtures rather than delete them. They do not access real Codex data.

Skill format / Skill 格式: [Official OpenAI documentation](https://developers.openai.com/plugins/build/skills).
