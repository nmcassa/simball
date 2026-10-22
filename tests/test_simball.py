import unittest
from pathlib import Path

from simball.config import ConfigError, load_setup
from simball.engine import Game, GameConfig, MotionPhase
from simball.models import Vec2
from simball.render import render


class VectorTests(unittest.TestCase):
    def test_move_toward_respects_distance(self) -> None:
        moved = Vec2(0, 0).move_toward(Vec2(3, 4), 2.5)
        self.assertAlmostEqual(moved.x, 1.5)
        self.assertAlmostEqual(moved.y, 2.0)


class GameTests(unittest.TestCase):
    def test_game_reaches_final_buzzer(self) -> None:
        game = Game(GameConfig(duration_seconds=3, tick_seconds=0.1, seed=4))
        while not game.state.finished:
            game.tick()
        self.assertEqual(game.state.game_clock, 0)
        self.assertEqual(game.state.events[-1].text, "Final buzzer")

    def test_seed_produces_same_result(self) -> None:
        def result() -> tuple[int, int, list[str]]:
            game = Game(GameConfig(duration_seconds=30, seed=10))
            while not game.state.finished:
                game.tick()
            return game.state.home.score, game.state.away.score, [event.text for event in game.state.events]

        self.assertEqual(result(), result())

    def test_exactly_one_ball_handler(self) -> None:
        game = Game(GameConfig(duration_seconds=10, seed=2))
        for _ in range(100):
            game.tick()
            handlers = [player for team in (game.state.home, game.state.away) for player in team.players if player.has_ball]
            self.assertEqual(len(handlers), 1)

    def test_renderer_contains_scoreboard_and_players(self) -> None:
        output = render(Game(GameConfig(seed=1)).state)
        self.assertIn("Home 0 - 0 Away", output)
        self.assertIn("X Home", output)
        self.assertIn("#", output)

    def test_possession_runs_screen_and_cut_motion(self) -> None:
        game = Game(GameConfig(duration_seconds=20, seed=8))
        seen = set()
        for _ in range(70):
            game.tick()
            seen.add(game.motion.phase)
        self.assertIn(MotionPhase.SCREENING, seen)
        self.assertIn(MotionPhase.CUTTING, seen)
        self.assertTrue(any("screen" in event.text for event in game.state.events))

    def test_screen_can_slow_cutters_defender(self) -> None:
        game = Game(GameConfig(duration_seconds=20, seed=3))
        game.motion.phase = MotionPhase.CUTTING
        screener = game.state.offense_team.players[4]
        cutter_defender = game.state.defense_team.players[1]
        cutter_defender.location = screener.location
        game._assign_targets()
        self.assertEqual(cutter_defender.activity, "fighting screen")
        self.assertLess(cutter_defender.movement_modifier, 1.0)


class ConfigTests(unittest.TestCase):
    def test_example_loads_custom_teams_and_plays(self) -> None:
        config_path = Path(__file__).parents[1] / "configs" / "coach_example.json"
        setup = load_setup(config_path)
        self.assertEqual(setup.home.name, "Blue")
        self.assertEqual(setup.home.players[0].name, "Avery")
        self.assertEqual(setup.home.players[0].ratings.passing, 90)
        self.assertEqual(setup.plays[setup.home.side].name, "Five Out Motion")
        self.assertEqual(setup.plays[setup.away.side].name, "Horns")

    def test_invalid_rating_is_rejected(self) -> None:
        config_path = Path(__file__).parents[1] / "configs" / "coach_example.json"
        text = config_path.read_text(encoding="utf-8").replace('"shooting": 75', '"shooting": 101', 1)
        temporary = Path(__file__).parent / "invalid_config.json"
        temporary.write_text(text, encoding="utf-8")
        try:
            with self.assertRaisesRegex(ConfigError, "shooting"):
                load_setup(temporary)
        finally:
            temporary.unlink()


if __name__ == "__main__":
    unittest.main()
