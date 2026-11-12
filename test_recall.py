import os
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

import relate

from recall import load_demo, trace_batch


class RecallTests(unittest.TestCase):
    def test_reopens_database_and_resolves_active_path_and_loan(self):
        with TemporaryDirectory(dir=os.environ['CONTEST_TEST_SCRATCH']) as temp:
            database = str(Path(temp) / 'recall.rl')
            with relate.connect(database) as connection:
                load_demo(connection)
                load_demo(connection)
            with relate.connect(database) as connection:
                self.assertEqual(trace_batch(connection, 'LOT-7'), [
                    {'part': 'P-104', 'asset': 'KIT-02', 'route': ['P-104', 'HEAD-2', 'KIT-02'], 'loan': 'LOAN-9'},
                ])

    def test_checked_in_asset_has_no_current_loan(self):
        with relate.connect(':memory:') as connection:
            load_demo(connection)
            self.assertEqual(trace_batch(connection, 'LOT-8'), [
                {'part': 'P-105', 'asset': 'KIT-03', 'route': ['P-105', 'KIT-03'], 'loan': None},
            ])

    def test_unknown_batch_does_not_invent_a_hit(self):
        with relate.connect(':memory:') as connection:
            load_demo(connection)
            self.assertEqual(trace_batch(connection, "LOT-7' OR true"), [])


if __name__ == '__main__':
    unittest.main()
