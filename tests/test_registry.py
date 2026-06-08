from __future__ import annotations

import unittest

from supercute.scenarios import TASKS
from supercute import scenarios_publiclift, scenarios_realtok, scenarios_tok, scenarios_hard


class RegistryTests(unittest.TestCase):
    def test_key_modules_are_registered(self) -> None:
        for module in (scenarios_tok, scenarios_hard, scenarios_realtok, scenarios_publiclift):
            for name in module.TASKS:
                with self.subTest(task=name):
                    self.assertIn(name, TASKS)

    def test_publiclift_count(self) -> None:
        self.assertGreaterEqual(len(scenarios_publiclift.TASKS), 8)


if __name__ == "__main__":
    unittest.main()
