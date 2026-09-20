import importlib.util
from pathlib import Path
import unittest


MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "rh56e2_bench_test.py"
SPEC = importlib.util.spec_from_file_location("rh56e2_bench_test", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
BENCH = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(BENCH)
authorize_motion = BENCH.authorize_motion
bounded_target = BENCH.bounded_target
validate_delta = BENCH.validate_delta


class BenchTargetTests(unittest.TestCase):
    def test_relative_target(self):
        self.assertEqual(bounded_target(500, 50), 550)

    def test_target_clamps_to_controller_range(self):
        self.assertEqual(bounded_target(980, 100), 1000)
        self.assertEqual(bounded_target(20, -100), 0)

    def test_delta_must_be_small_and_nonzero(self):
        for value in (-100, -1, 1, 100):
            validate_delta(value)
        for value in (-101, 0, 101):
            with self.assertRaises(ValueError):
                validate_delta(value)

    def test_motion_requires_both_gates(self):
        with self.assertRaises(ValueError):
            authorize_motion(False, "MOVE_RH56E2")
        with self.assertRaises(ValueError):
            authorize_motion(True, "move_rh56e2")
        authorize_motion(True, "MOVE_RH56E2")


if __name__ == "__main__":
    unittest.main()
