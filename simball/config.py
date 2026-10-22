from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any

from .models import Player, Ratings, Team, TeamSide, Tendencies, Vec2
from .plays import Play


class ConfigError(ValueError):
    pass


@dataclass(frozen=True)
class SimulationSetup:
    home: Team
    away: Team
    plays: dict[TeamSide, Play]


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
        home_play = _play(play_data[data.get("home_play", next(iter(play_data)))])
        away_play = _play(play_data[data.get("away_play", data.get("home_play", next(iter(play_data))))])
    except (KeyError, TypeError, IndexError, StopIteration) as error:
        raise ConfigError(f"missing or invalid field: {error}") from error
    return SimulationSetup(home, away, {TeamSide.HOME: home_play, TeamSide.AWAY: away_play})


def _team(data: dict[str, Any], side: TeamSide, default_symbol: str) -> Team:
    players = data["players"]
    if len(players) != 5:
        raise ConfigError(f"{side.value} team must contain exactly 5 players")
    parsed = [_player(item, index) for index, item in enumerate(players, 1)]
    return Team(str(data["name"]), str(data.get("symbol", default_symbol))[:1], side, parsed)


def _player(data: dict[str, Any], number: int) -> Player:
    ratings_data = data["ratings"]
    tendencies_data = data["tendencies"]
    ratings = Ratings(**{name: _bounded(ratings_data[name], name, 1, 100) for name in Ratings.__dataclass_fields__})
    tendencies = Tendencies(**{name: _bounded(tendencies_data[name], name, 0.0, 1.0) for name in Tendencies.__dataclass_fields__})
    height = int(_bounded(data["height_inches"], "height_inches", 60, 96))
    weight = int(_bounded(data["weight_lb"], "weight_lb", 120, 400))
    start = Vec2(12 + number * 2, 6 + number * 8)
    return Player(number, str(data["name"]), str(data["position"]), height, weight, ratings, tendencies, start, start)


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
