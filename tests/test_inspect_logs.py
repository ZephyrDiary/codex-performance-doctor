import importlib.util
import sqlite3
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / 'scripts' / 'inspect_logs.py'


class InspectLogsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not SCRIPT.is_file():
            raise AssertionError('The read-only inspector has not been implemented')
        spec = importlib.util.spec_from_file_location('inspect_logs', SCRIPT)
        cls.module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.module)

    def setUp(self):
        # Retain synthetic fixtures: never delete files as part of this test suite.
        self.root = Path(tempfile.mkdtemp(prefix='codex-doctor-test-'))
        self.db = self.root / 'logs with spaces #1.sqlite'
        with sqlite3.connect(self.db) as con:
            con.execute('CREATE TABLE logs(id INTEGER PRIMARY KEY, ts INTEGER, level TEXT, feedback_log_body TEXT)')
            con.executemany('INSERT INTO logs VALUES(?,?,?,?)', [
                (1, 1, 'TRACE', 'SYNTHETIC_PRIVATE_BODY'),
                (2, 2, 'INFO', 'SYNTHETIC_PRIVATE_BODY'),
            ])

    def test_snapshot_counts_without_exposing_bodies(self):
        result = self.module.snapshot(self.db)
        self.assertEqual(result['rows'], 2)
        self.assertEqual(result['max_id'], 2)
        self.assertEqual(result['trace_rows'], 1)
        self.assertEqual(result['trace_max_id'], 1)
        self.assertNotIn('SYNTHETIC_PRIVATE_BODY', str(result))

    def test_missing_database_is_not_created(self):
        missing = self.root / 'missing.sqlite'
        with self.assertRaises(FileNotFoundError):
            self.module.snapshot(missing)
        self.assertFalse(missing.exists())

    def test_database_bytes_unchanged(self):
        before = self.db.read_bytes()
        self.module.snapshot(self.db)
        self.assertEqual(before, self.db.read_bytes())

    def test_retention_does_not_hide_new_ids(self):
        before = self.module.snapshot(self.db)
        with sqlite3.connect(self.db) as con:
            con.execute('DELETE FROM logs')
            con.execute("INSERT INTO logs VALUES(3,3,'INFO','synthetic')")
        after = self.module.snapshot(self.db)
        self.assertLess(after['rows'], before['rows'])
        self.assertGreater(after['max_id'], before['max_id'])

    def test_live_wal_rows_visible(self):
        writer = sqlite3.connect(self.db)
        try:
            writer.execute('PRAGMA journal_mode=WAL')
            writer.execute("INSERT INTO logs VALUES(3,3,'TRACE','synthetic')")
            writer.commit()
            self.assertEqual(self.module.snapshot(self.db)['trace_max_id'], 3)
        finally:
            writer.close()

    def test_incompatible_schema_fails_closed(self):
        with sqlite3.connect(self.db) as con:
            con.execute('ALTER TABLE logs RENAME TO other_logs')
        with self.assertRaises(ValueError):
            self.module.snapshot(self.db)

    def test_view_cannot_masquerade_as_logs(self):
        with sqlite3.connect(self.db) as con:
            con.execute('ALTER TABLE logs RENAME TO private_logs')
            con.execute('CREATE VIEW logs AS SELECT id, feedback_log_body AS ts, level FROM private_logs')
        with self.assertRaises(ValueError):
            self.module.snapshot(self.db)

    def test_text_in_timestamp_fails_without_exposing_it(self):
        with sqlite3.connect(self.db) as con:
            con.execute("UPDATE logs SET ts='SYNTHETIC_PRIVATE_BODY' WHERE id=1")
        with self.assertRaises(ValueError) as error:
            self.module.snapshot(self.db)
        self.assertNotIn('SYNTHETIC_PRIVATE_BODY', str(error.exception))

    def test_observation_interval_includes_first_query_uncertainty(self):
        result = self.module.observation_interval(
            {'query_started_monotonic': 0, 'query_finished_monotonic': 4},
            {'query_started_monotonic': 19, 'query_finished_monotonic': 19.5},
        )
        self.assertEqual(result['query_start_interval_seconds'], 19)
        self.assertEqual(result['snapshot_interval_bounds_seconds'], [15, 19.5])


if __name__ == '__main__':
    unittest.main()
