"""B2: o espelho client-side (frontend/js/points.js) DEVE bater com a fonte de
verdade do backend (domain.entities.MULTIPLIERS / domain.scoring). Sem este teste,
um lado pode mudar sem o outro e o feedback otimista da UI diverge do servidor.
"""
import re
import unittest
from pathlib import Path

from app.domain.entities import MULTIPLIERS
from app.domain.scoring import POINTS_EXACT_BONUS, POINTS_RESULT

_POINTS_JS = Path(__file__).resolve().parents[3] / "frontend" / "js" / "points.js"


def _parse_js_int_map(src: str, name: str) -> dict:
    m = re.search(name + r"\s*=\s*\{([^}]*)\}", src)
    if not m:
        raise AssertionError(f"{name} não encontrado em points.js")
    out = {}
    for pair in m.group(1).split(","):
        pair = pair.strip()
        if not pair:
            continue
        key, value = pair.split(":")
        out[key.strip()] = int(value.strip())
    return out


def _parse_js_int(src: str, name: str) -> int:
    m = re.search(name + r"\s*=\s*(\d+)", src)
    if not m:
        raise AssertionError(f"{name} não encontrado em points.js")
    return int(m.group(1))


class TestMultiplierParity(unittest.TestCase):
    def setUp(self):
        self.src = _POINTS_JS.read_text(encoding="utf-8")

    def test_multiplicadores_batem(self):
        front = _parse_js_int_map(self.src, "MULTIPLIERS")
        back = {stage.value: mult for stage, mult in MULTIPLIERS.items()}
        self.assertEqual(front, back)

    def test_pontos_base_batem(self):
        self.assertEqual(_parse_js_int(self.src, "POINTS_RESULT"), POINTS_RESULT)
        self.assertEqual(
            _parse_js_int(self.src, "POINTS_EXACT_BONUS"), POINTS_EXACT_BONUS
        )


if __name__ == "__main__":
    unittest.main()
