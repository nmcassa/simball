import unittest
from contextlib import redirect_stdout
from io import StringIO
import json
from pathlib import Path
from tempfile import TemporaryDirectory

from simball.cli import main
from simball.config import ConfigError, load_setup
from simball.engine import Game, GameConfig, MotionPhase
from simball.models import TeamSide, Vec2
from simball.plays import FIVE_OUT, HORNS, PlayOption
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

    def test_play_is_selected_for_each_possession(self) -> None:
        playbooks = {
            TeamSide.HOME: (PlayOption(FIVE_OUT, 1.0),),
            TeamSide.AWAY: (PlayOption(HORNS, 1.0),),
        }
        game = Game(GameConfig(seed=3), team_playbooks=playbooks)
        self.assertIs(game.active_play, FIVE_OUT)
        game._change_possession()
        self.assertIs(game.active_play, HORNS)
        self.assertEqual(game.state.events[-1].text, "Away calls Horns")

    def test_seed_reproduces_weighted_play_sequence(self) -> None:
        playbooks = {
            side: (PlayOption(FIVE_OUT, 3.0), PlayOption(HORNS, 1.0))
            for side in TeamSide
        }

        def sequence() -> list[str]:
            game = Game(GameConfig(seed=14), team_playbooks=playbooks)
            names = [game.active_play.name]
            for _ in range(12):
                game._change_possession()
                names.append(game.active_play.name)
            return names

        self.assertEqual(sequence(), sequence())
        self.assertEqual(set(sequence()), {"Five Out", "Horns"})

    def test_seed_reproduces_agent_movement_variation(self) -> None:
        def movement() -> list[tuple[float, float, float, float]]:
            game = Game(GameConfig(seed=22))
            return [
                (player.reaction_time, player.route_offset, player.location.x, player.location.y)
                for team in (game.state.home, game.state.away)
                for player in team.players
            ]

        self.assertEqual(movement(), movement())

    def test_different_seeds_vary_agent_reactions_and_routes(self) -> None:
        first = Game(GameConfig(seed=22))
        second = Game(GameConfig(seed=23))
        first_variation = [(player.reaction_time, player.route_offset) for player in first.state.home.players]
        second_variation = [(player.reaction_time, player.route_offset) for player in second.state.home.players]
        self.assertNotEqual(first_variation, second_variation)

    def test_route_variation_curves_and_converges(self) -> None:
        game = Game(GameConfig(seed=5))
        player = game.state.home.players[0]
        player.location = Vec2(10, 10)
        player.target = Vec2(30, 10)
        player.route_offset = 2.0
        route_target = player.route_target()
        self.assertEqual(route_target.x, 30)
        self.assertGreater(route_target.y, 10)
        player.location = Vec2(29, 10)
        self.assertLess(player.route_target().y - 10, route_target.y - 10)

    def test_players_wait_for_reaction_before_moving(self) -> None:
        game = Game(GameConfig(seed=9))
        player = game.state.home.players[0]
        player.location = Vec2(10, 10)
        player.target = Vec2(30, 10)
        player.reaction_remaining = 0.2
        game._move_players(0.1)
        self.assertEqual(player.location, Vec2(10, 10))
        game._move_players(0.1)
        game._move_players(0.1)
        self.assertGreater(player.location.x, 10)


class ConfigTests(unittest.TestCase):
    def test_example_loads_custom_teams_and_plays(self) -> None:
        config_path = Path(__file__).parents[1] / "configs" / "coach_example.json"
        setup = load_setup(config_path)
        self.assertEqual(setup.home.name, "Blue")
        self.assertEqual(setup.home.players[0].name, "Avery")
        self.assertEqual(setup.home.players[0].player_id, "blue-avery")
        self.assertEqual(setup.home.players[0].ratings.passing, 90)
        self.assertEqual(setup.plays[setup.home.side].name, "Five Out Motion")
        self.assertEqual(setup.plays[setup.away.side].name, "Horns")
        self.assertEqual([option.usage for option in setup.playbooks[setup.home.side]], [0.75, 0.25])

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

    def test_duplicate_player_id_is_rejected(self) -> None:
        config_path = Path(__file__).parents[1] / "configs" / "coach_example.json"
        text = config_path.read_text(encoding="utf-8").replace('"id": "blue-blake"', '"id": "blue-avery"', 1)
        temporary = Path(__file__).parent / "invalid_config.json"
        temporary.write_text(text, encoding="utf-8")
        try:
            with self.assertRaisesRegex(ConfigError, "IDs must be unique"):
                load_setup(temporary)
        finally:
            temporary.unlink()

    def test_lineup_requires_one_player_at_each_position(self) -> None:
        config_path = Path(__file__).parents[1] / "configs" / "coach_example.json"
        text = config_path.read_text(encoding="utf-8").replace('"position": "SG"', '"position": "PG"', 1)
        temporary = Path(__file__).parent / "invalid_config.json"
        temporary.write_text(text, encoding="utf-8")
        try:
            with self.assertRaisesRegex(ConfigError, "exactly one of each position"):
                load_setup(temporary)
        finally:
            temporary.unlink()

    def test_validate_command_accepts_valid_configuration_without_running_game(self) -> None:
        config_path = Path(__file__).parents[1] / "configs" / "coach_example.json"
        output = StringIO()
        with redirect_stdout(output):
            result = main(["--config", str(config_path), "--validate"])
        self.assertEqual(result, 0)
        self.assertIn("Configuration is valid", output.getvalue())

    def test_validate_command_requires_configuration(self) -> None:
        with self.assertRaises(SystemExit) as error:
            main(["--validate"])
        self.assertEqual(error.exception.code, 2)

    def test_legacy_single_play_configuration_is_supported(self) -> None:
        data = self._example_data()
        data.pop("home_plays")
        data.pop("away_plays")
        data["home_play"] = "motion"
        data["away_play"] = "horns"
        setup = self._load_data(data)
        self.assertEqual(setup.playbooks[TeamSide.HOME], (PlayOption(setup.plays[TeamSide.HOME], 1.0),))
        self.assertEqual(setup.playbooks[TeamSide.AWAY], (PlayOption(setup.plays[TeamSide.AWAY], 1.0),))

    def test_invalid_playbook_usage_is_rejected(self) -> None:
        data = self._example_data()
        data["home_plays"][0]["usage"] = 0
        with self.assertRaisesRegex(ConfigError, "positive finite number"):
            self._load_data(data)

    def test_unknown_playbook_entry_is_rejected(self) -> None:
        data = self._example_data()
        data["away_plays"][0]["play"] = "transition"
        with self.assertRaisesRegex(ConfigError, "unknown play: transition"):
            self._load_data(data)

    def test_duplicate_playbook_entry_is_rejected(self) -> None:
        data = self._example_data()
        data["home_plays"][1]["play"] = "motion"
        with self.assertRaisesRegex(ConfigError, "duplicate play: motion"):
            self._load_data(data)

    def test_configuration_version_is_required(self) -> None:
        data = self._example_data()
        data.pop("version")
        with self.assertRaisesRegex(ConfigError, 'add "version": 1'):
            self._load_data(data)

    def test_obsolete_configuration_version_has_migration_error(self) -> None:
        data = self._example_data()
        data["version"] = 0
        with self.assertRaisesRegex(ConfigError, "obsolete; migrate to version 1"):
            self._load_data(data)

    def test_newer_configuration_version_is_rejected(self) -> None:
        data = self._example_data()
        data["version"] = 2
        with self.assertRaisesRegex(ConfigError, "newer than supported version 1"):
            self._load_data(data)

    def test_configuration_version_must_be_an_integer(self) -> None:
        data = self._example_data()
        data["version"] = "1"
        with self.assertRaisesRegex(ConfigError, "version must be an integer"):
            self._load_data(data)

    def _example_data(self) -> dict:
        config_path = Path(__file__).parents[1] / "configs" / "coach_example.json"
        return json.loads(config_path.read_text(encoding="utf-8"))

    def _load_data(self, data: dict):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "config.json"
            path.write_text(json.dumps(data), encoding="utf-8")
            return load_setup(path)


if __name__ == "__main__":
    unittest.main()
