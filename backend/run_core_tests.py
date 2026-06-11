#!/usr/bin/env python3
"""Executa os testes core (stdlib-only) — funciona em ambiente sem pytest.

Uso: python3 backend/run_core_tests.py [padrao]
"""
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)


def main() -> int:
    pattern = sys.argv[1] if len(sys.argv) > 1 else "test_*.py"
    suite = unittest.defaultTestLoader.discover(
        os.path.join(HERE, "tests", "core"), pattern=pattern, top_level_dir=HERE
    )
    runner = unittest.TextTestRunner(verbosity=1)
    result = runner.run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(main())
