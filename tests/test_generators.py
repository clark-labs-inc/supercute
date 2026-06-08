from __future__ import annotations

import hashlib
import importlib
import random
import unittest

from supercute.grade import grade, grade_robust


def rng_for(name: str, i: int) -> random.Random:
    return random.Random(int(hashlib.md5(f"{name}:{i}".encode()).hexdigest(), 16))


class GeneratorSelfCheckTests(unittest.TestCase):
    MODULES = ["tok", "hard", "realtok", "publiclift"]

    def test_selected_modules_are_self_consistent(self) -> None:
        for suffix in self.MODULES:
            module = importlib.import_module(f"supercute.scenarios_{suffix}")
            for task_name, fn in sorted(module.TASKS.items()):
                for i in range(3):
                    with self.subTest(module=suffix, task=task_name, seed=i):
                        scn = fn(rng_for(task_name, i))
                        self.assertIn(scn["kind"], {"int", "yn", "str", "exact"})
                        self.assertTrue(grade(scn, scn["answer"]))
                        self.assertTrue(grade_robust(scn, scn["answer"]))


if __name__ == "__main__":
    unittest.main()
