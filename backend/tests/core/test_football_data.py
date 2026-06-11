import unittest

from app.domain.entities import MatchStatus
from app.providers.football_data import FootballDataProvider, parse_match, team_code


def raw_match(**over):
    base = {
        "id": 555001,
        "utcDate": "2026-06-11T19:00:00Z",
        "status": "TIMED",
        "minute": None,
        "homeTeam": {"name": "Mexico", "tla": "MEX"},
        "awayTeam": {"name": "South Africa", "tla": "RSA"},
        "score": {"winner": None, "duration": "REGULAR",
                  "fullTime": {"home": None, "away": None},
                  "regularTime": {"home": None, "away": None}},
    }
    base.update(over)
    return base


class TestFootballData(unittest.TestCase):
    def test_status_mapping(self):
        cases = {
            "TIMED": MatchStatus.SCHEDULED, "SCHEDULED": MatchStatus.SCHEDULED,
            "IN_PLAY": MatchStatus.LIVE, "PAUSED": MatchStatus.LIVE,
            "FINISHED": MatchStatus.FINISHED, "DESCONHECIDO": MatchStatus.SCHEDULED,
        }
        for raw_status, expected in cases.items():
            upd = parse_match(raw_match(status=raw_status))
            self.assertEqual(upd.status, expected, raw_status)

    def test_parse_basico(self):
        upd = parse_match(raw_match(
            status="IN_PLAY", minute=23,
            score={"winner": None, "fullTime": {"home": 1, "away": 0}},
        ))
        self.assertEqual(upd.external_id, "555001")
        self.assertEqual((upd.home_code, upd.away_code), ("MEX", "RSA"))
        self.assertEqual((upd.home_score, upd.away_score, upd.minute), (1, 0, 23))
        self.assertEqual(upd.kickoff_utc.isoformat(), "2026-06-11T19:00:00+00:00")

    def test_aliases_de_nomes(self):
        self.assertEqual(team_code({"name": "South Korea"}), "KOR")
        self.assertEqual(team_code({"name": "Czech Republic"}), "CZE")
        self.assertEqual(team_code({"name": "Ivory Coast"}), "CIV")
        self.assertEqual(team_code({"name": "Time Misterioso", "tla": "BRA"}), "BRA")
        self.assertIsNone(team_code(None))
        self.assertIsNone(team_code({}))

    def test_mata_mata_90min_e_winner(self):
        upd = parse_match(raw_match(
            status="FINISHED",
            score={
                "winner": "AWAY_TEAM", "duration": "PENALTY_SHOOTOUT",
                "fullTime": {"home": 1, "away": 1},
                "regularTime": {"home": 1, "away": 1},
                "penalties": {"home": 3, "away": 4},
            },
        ))
        self.assertEqual((upd.home_score, upd.away_score), (1, 1))  # 90min
        self.assertEqual(upd.winner_code, "RSA")

    def test_regular_time_preferido_sobre_fulltime(self):
        upd = parse_match(raw_match(
            status="FINISHED",
            score={"winner": "HOME_TEAM", "duration": "EXTRA_TIME",
                   "fullTime": {"home": 2, "away": 1},
                   "regularTime": {"home": 1, "away": 1}},
        ))
        self.assertEqual((upd.home_score, upd.away_score), (1, 1))

    def test_provider_fetch_com_http_fake(self):
        def fake_get(url, token):
            self.assertIn("football-data.org", url)
            self.assertEqual(token, "tok")
            return {"matches": [raw_match(), raw_match(id=555002)]}

        provider = FootballDataProvider("tok", http_get=fake_get)
        updates = provider.fetch()
        self.assertEqual(len(updates), 2)
        with self.assertRaises(ValueError):
            FootballDataProvider("")


if __name__ == "__main__":
    unittest.main()
