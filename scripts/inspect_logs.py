"""Aggregate-only SQLite log inspection. No repair operations or file deletion."""

import argparse
import json
import math
import os
import sqlite3
import time
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path


def file_stats(path):
    try:
        stat = path.stat()
        return {'bytes': stat.st_size, 'mtime_ns': stat.st_mtime_ns}
    except FileNotFoundError:
        return None


def snapshot(path):
    path = Path(path).expanduser().resolve(strict=True)
    if not path.is_file():
        raise ValueError('Database path must be an existing regular file')
    wal = Path(str(path) + '-wal')
    shm = Path(str(path) + '-shm')
    if wal.exists() and not shm.exists():
        raise ValueError('Live WAL without SHM: stop rather than create a sidecar')
    deadline = time.monotonic() + 5
    with closing(sqlite3.connect(path.as_uri() + '?mode=ro', uri=True, timeout=2)) as con:
        con.execute('PRAGMA query_only=ON')
        con.set_progress_handler(lambda: int(time.monotonic() > deadline), 10000)
        table = con.execute("SELECT type, sql FROM sqlite_master WHERE name='logs'").fetchone()
        if not table or table[0] != 'table' or (table[1] or '').lstrip().upper().startswith('CREATE VIRTUAL'):
            raise ValueError('Expected an ordinary logs table, not a view or virtual table')
        columns = {item[1]: item for item in con.execute('PRAGMA table_xinfo(logs)')}
        if not {'id', 'ts', 'level'} <= columns.keys():
            raise ValueError('Unsupported logs schema: expected id, ts, level')
        for name, declared_type in [('id', 'INTEGER'), ('ts', 'INTEGER'), ('level', 'TEXT')]:
            if columns[name][2].upper() != declared_type or columns[name][6] != 0:
                raise ValueError('Unsupported logs metadata column type')
        query_started = time.monotonic()
        observed_at = datetime.now(timezone.utc).isoformat()
        # One statement keeps the aggregates on the same database snapshot.
        row = con.execute("""
            SELECT COUNT(*), MAX(id), MAX(ts),
                   COALESCE(SUM(CASE WHEN level='TRACE' THEN 1 ELSE 0 END),0),
                   MAX(CASE WHEN level='TRACE' THEN id END),
                   COALESCE(SUM(CASE WHEN typeof(id)='integer' AND typeof(ts)='integer'
                                     AND typeof(level)='text' THEN 0 ELSE 1 END),0)
            FROM logs
        """).fetchone()
        query_finished = time.monotonic()
        if row[5]:
            raise ValueError('Invalid logs metadata values; no values disclosed')
        triggers = [item[0] for item in con.execute(
            "SELECT name FROM sqlite_master WHERE type='trigger' AND tbl_name='logs'"
        )]
    return {
        'observed_at_utc': observed_at,
        'query_started_monotonic': query_started,
        'query_finished_monotonic': query_finished,
        'query_seconds': round(query_finished - query_started, 6),
        'rows': row[0], 'max_id': row[1], 'newest_ts': row[2],
        'trace_rows': row[3], 'trace_max_id': row[4],
        'trigger_names': triggers, 'database': file_stats(path),
        'wal': file_stats(wal), 'shm': file_stats(shm),
    }


def observation_interval(before, after):
    return {
        'query_start_interval_seconds': round(
            after['query_started_monotonic'] - before['query_started_monotonic'], 6),
        'snapshot_interval_bounds_seconds': [
            round(after['query_started_monotonic'] - before['query_finished_monotonic'], 6),
            round(after['query_finished_monotonic'] - before['query_started_monotonic'], 6),
        ],
    }


def main():
    home = Path(os.environ.get('CODEX_HOME', str(Path.home() / '.codex')))
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--db', type=Path, default=home / 'logs_2.sqlite')
    parser.add_argument('--seconds', type=float, default=15)
    args = parser.parse_args()
    if not math.isfinite(args.seconds) or not 0 <= args.seconds <= 300:
        parser.error('--seconds must be finite and between 0 and 300')
    try:
        before = snapshot(args.db)
        time.sleep(args.seconds)
        after = snapshot(args.db)
    except (OSError, ValueError, sqlite3.Error) as error:
        parser.exit(1, f'Inspection stopped without repair: {error}\n')
    print(json.dumps({
        **observation_interval(before, after),
        'before': before, 'after': after,
        'limits': 'Logical growth is not physical disk throughput. WAL can be reused. '
                  'Read-only SQL may participate in SQLite SHM locking. '
                  'Query durations bound snapshot timing uncertainty; file sizes are observed afterward. '
                  'No log bodies are returned.',
    }, indent=2))


if __name__ == '__main__':
    main()
