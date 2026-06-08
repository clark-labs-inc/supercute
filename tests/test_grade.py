from __future__ import annotations

import unittest

from supercute.grade import grade, grade_robust


class GradeTests(unittest.TestCase):
    def test_int_robust_takes_final_answer(self) -> None:
        scn = {"kind": "int", "answer": "38"}
        self.assertTrue(grade_robust(scn, "I first thought 37. Answer: 38"))

    def test_exact_is_case_sensitive(self) -> None:
        scn = {"kind": "exact", "answer": '{"A":1}'}
        self.assertTrue(grade(scn, '{"A":1}'))
        self.assertFalse(grade(scn, '{"a":1}'))

    def test_yes_no_robust_takes_last_marker(self) -> None:
        scn = {"kind": "yn", "answer": "no"}
        self.assertTrue(grade_robust(scn, "Could be yes at first glance. Final answer: no."))


if __name__ == "__main__":
    unittest.main()
