# Consent-Gated Repair / 经确认的修复

这是针对内部日志库的非官方规避方案，不是 OpenAI 支持的配置。可能丢失 TRACE 诊断能力、影响排错或在升级后失效。优先检查当前版本可用的受支持日志设置；不能编造配置项。 / This is an unsupported internal-database workaround, not an official setting. It suppresses TRACE diagnostics and may break across upgrades. Prefer verified supported settings when available.

## Preconditions / 前置条件

展示活动写入证据、数据库绝对路径、拟修改 SQL、备份位置和风险，请用户明确授权。仅授权排查、安装 Skill 或发布 GitHub 不代表允许修复。 / Show evidence, exact database path, proposed SQL, backup location and risks. Audit, skill installation and GitHub publication do not authorize repairs.

1. 验证 `logs` 是实际表且有 `id`、`level` 字段。检查当前 trigger 定义；重名但不同逻辑时停止，不覆盖。 / Verify table and schema; inspect existing trigger SQL and stop on a name collision with different logic.
2. 选择全新且不与数据库或 sidecar 重合的备份文件名，确认可用空间。用 SQLite online backup API 创建独立备份，关闭目标连接，再只读运行 `PRAGMA quick_check` 并验证日志表可读。备份或验证失败立即停止，不修改源库。 / Use a unique destination and SQLite's online backup API. Close and reopen the backup read-only, verify `quick_check` returns `ok` and confirm the log table is readable before mutation.
3. 逐个复制正在变化的 DB/WAL/SHM 不是一致性备份；online backup 自身已包含已提交 WAL 数据，不需要额外 sidecar 才能恢复。不要上传备份。 / Sequential live file copies are not a consistent backup; the online backup is self-contained. Keep it private.
4. 使用 `mode=rw` 打开已存在的源库，避免误建数据库。采用有限超时；忙/锁定时停止并告知，不循环强行重试。 / Open the existing database with `mode=rw` and a bounded timeout; stop on lock contention.

## TRACE Trigger / TRACE 拦截

只在没有同名 trigger 或已确认定义相同后执行： / Execute only when the name is absent or its definition has been verified equivalent:

```sql
CREATE TRIGGER IF NOT EXISTS codex_drop_trace_logs
BEFORE INSERT ON logs
WHEN NEW.level = 'TRACE'
BEGIN
    SELECT RAISE(IGNORE);
END;
```

提交后验证实际存储的 trigger 定义，不仅仅检查名字存在。只匹配大写 TRACE；不拦截 DEBUG/INFO/WARN/ERROR，不删除历史日志，也不保证无其他数据库写入。 / Commit and verify the stored definition. Only uppercase TRACE inserts are ignored; other levels, retention and other database writes remain possible.

## Checkpoint And Verification / Checkpoint 与复查

先释放本次排查的读事务。仅在用户同意 checkpoint 后、写连接不处于事务中执行： / Release audit readers and run outside a write transaction, only with checkpoint consent:

```sql
PRAGMA wal_checkpoint(TRUNCATE);
```

记录原始返回值 `(busy, log_frames, checkpointed_frames)`。`busy=1` 表示未完成预期阻塞操作，不能宣称截断成功；非 WAL 模式可能返回帧数 `-1`，应报告不适用。成功 TRUNCATE 通常返回 `(0,0,0)`，但其他写入可立刻重新扩展 WAL。不要删除 WAL/SHM、切换 journal mode 或执行 VACUUM。 / Report the raw result; busy is not success and negative frames can mean non-WAL mode. New writes may immediately regrow a successfully truncated WAL. Never remove sidecars or change journal mode.

重新只读采样至少 15 秒，比较 TRACE 最大 ID、TRACE 行数、总最大 ID 和 WAL。若没有 TRACE 生产活动，稳定 ID 只说明没有观察到新增 TRACE，不能独立证明 trigger 有效。不要为测试向活动库插入伪造日志。若新 TRACE 仍出现、应用报错或锁定，停止并报告，不叠加更多 trigger。 / Resample for at least 15 seconds. Stable TRACE IDs without producer activity are inconclusive. Never inject test logs into the live database. Stop on continued TRACE inserts, app errors or locks.

## Rollback / 撤销

用户明确授权撤销后，先核对该 trigger 确为本次方案创建且定义吻合，再删除该 trigger；不触及其他 trigger 或历史数据。 / With explicit rollback consent, verify ownership and definition before dropping only this trigger:

```sql
DROP TRIGGER codex_drop_trace_logs;
```

不能把旧备份直接覆盖仍在运行的数据库；这会丢失备份后日志并造成 WAL 不匹配。恢复整库需另行制定停写、保留当前文件和验证方案，并征得用户同意。 / Never overwrite a live database with an old backup. Full restoration needs separately approved quiescence, preservation and validation.

Sources / 参考: [SQLite WAL](https://www.sqlite.org/wal.html), [Online backup](https://www.sqlite.org/backup.html), [Checkpoint pragma](https://www.sqlite.org/pragma.html#pragma_wal_checkpoint).
