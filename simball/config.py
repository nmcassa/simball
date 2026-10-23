from __future__ import annotations

from dataclasses import dataclass
import json
import math
from pathlib import Path
from typing import Any

from .models import Player, Ratings, Team, TeamSide, Tendencies, Vec2
from .plays import Play, PlayOption


POSITIONS = ("PG", "SG", "SF", "PF", "C")


class ConfigError(ValueError):
    pass


@dataclass(frozen=True)
class SimulationSetup:
    home: Team
    away: Team
    playbooks: dict[TeamSide, tuple[PlayOption, ...]]

    @property
    def plays(self) -> dict[TeamSide, Play]:
        return {side: options[0].play for side, options in self.playbooks.items()}


def load_setup(path: str | Path) -> SimulationSetup:
    source = Path(path)
    try:
        data = json.loads(source.read_text(encoding="utf-8"))
    except OSError as error:
        raise ConfigError(f"cannot read {source}: {error}") from error
    except json.JSONDecodeError as error:
        raise ConfigError(f"invalid JSON at line {error.lineno}, column {error.colno}: {error.msg}") from error
    try:
        home = _team(data["teams"]["home"], TeamSide.HOME, "X")
        away = _team(data["teams"]["away"], TeamSide.AWAY, "O")
        play_data = data["plays"]
        plays = {name: _play(item) for name, item in play_data.items()}
        default_play = next(iter(plays))
        home_playbook = _playbook(data, TeamSide.HOME, plays, default_play)
        away_playbook = _playbook(data, TeamSide.AWAY, plays, data.get("home_play", default_play))
    except (KeyError, TypeError, IndexError, StopIteration) as error:
        raise ConfigError(f"missing or invalid field: {error}") from error
    return SimulationSetup(home, away, {TeamSide.HOME: home_playbook, TeamSide.AWAY: away_playbook})


def _playbook(
    data: dict[str, Any],
    side: TeamSide,
    plays: dict[str, Play],
    default_play: str,
) -> tuple[PlayOption, ...]:
    singular_field = f"{side.value}_play"
    plural_field = f"{side.value}_plays"
    if singular_field in data and plural_field in data:
        raise ConfigError(f"cannot specify both {singular_field} and {plural_field}")
    if plural_field not in data:
        name = data.get(singular_field, default_play)
        return (PlayOption(_named_play(plays, name, side), 1.0),)
    entries = data[plural_field]
    if not isinstance(entries, list) or not entries:
        raise ConfigError(f"{plural_field} must contain at least one play")
    options = []
    names = set()
    for entry in entries:
        if not isinstance(entry, dict) or "play" not in entry or "usage" not in entry:
            raise ConfigError(f"each {plural_field} entry must define play and usage")
        name = entry["play"]
        if not isinstance(name, str):
            raise ConfigError(f"{plural_field} play must be a string")
        if name in names:
            raise ConfigError(f"{plural_field} contains duplicate play: {name}")
        names.add(name)
        usage = entry["usage"]
        if not isinstance(usage, (int, float)) or isinstance(usage, bool) or not math.isfinite(usage) or usage <= 0:
            raise ConfigError(f"{plural_field} usage must be a positive finite number")
        options.append(PlayOption(_named_play(plays, name, side), float(usage)))
    return tuple(options)


def _named_play(plays: dict[str, Play], name: Any, side: TeamSide) -> Play:
    if not isinstance(name, str) or name not in plays:
        raise ConfigError(f"{side.value} playbook references unknown play: {name}")
    return plays[name]


def _team(data: dict[str, Any], side: TeamSide, default_symbol: str) -> Team:
    players = data["players"]
    if len(players) != 5:
        raise ConfigError(f"{side.value} team must contain exactly 5 players")
    parsed = [_player(item, index) for index, item in enumerate(players, 1)]
    player_ids = [player.player_id for player in parsed]
    if len(set(player_ids)) != len(player_ids):
        raise ConfigError(f"{side.value} team player IDs must be unique")
    positions = [player.position for player in parsed]
    if set(positions) != set(POSITIONS):
        raise ConfigError(f"{side.value} team must contain exactly one of each position: {', '.join(POSITIONS)}")
    return Team(str(data["name"]), str(data.get("symbol", default_symbol))[:1], side, parsed)


def _player(data: dict[str, Any], number: int) -> Player:
    player_id = data["id"]
    if not isinstance(player_id, str) or not player_id.strip():
        raise ConfigError("player id must be a non-empty string")
    position = data["position"]
    if position not in POSITIONS:
        raise ConfigError(f"position must be one of: {', '.join(POSITIONS)}")
    ratings_data = data["ratings"]
    tendencies_data = data["tendencies"]
    ratings = Ratings(**{name: _bounded(ratings_data[name], name, 1, 100) for name in Ratings.__dataclass_fields__})
    tendencies = Tendencies(**{name: _bounded(tendencies_data[name], name, 0.0, 1.0) for name in Tendencies.__dataclass_fields__})
    height = int(_bounded(data["height_inches"], "height_inches", 60, 96))
    weight = int(_bounded(data["weight_lb"], "weight_lb", 120, 400))
    start = Vec2(12 + number * 2, 6 + number * 8)
    return Player(number, player_id, str(data["name"]), position, height, weight, ratings, tendencies, start, start)


def _play(data: dict[str, Any]) -> Play:
    spots_data = data["spots"]
    if len(spots_data) != 5:
        raise ConfigError("every play must define exactly 5 spots")
    spots = tuple(Vec2(_bounded(spot[0], "spot x", 0, 94), _bounded(spot[1], "spot y", 0, 50)) for spot in spots_data)
    return Play(str(data["name"]), spots)


def _bounded(value: Any, field: str, minimum: float, maximum: float) -> float:
    if not isinstance(value, (int, float)) or isinstance(value, bool) or not minimum <= value <= maximum:
        raise ConfigError(f"{field} must be between {minimum} and {maximum}")
    return float(value)
