from __future__ import annotations

from dataclasses import dataclass

from .models import Player, Vec2


@dataclass(frozen=True)
class Play:
    name: str
    spots: tuple[Vec2, ...]

    def target_for(self, player: Player, attacking_right: bool) -> Vec2:
        spot = self.spots[player.number - 1]
        return spot if attacking_right else Vec2(94.0 - spot.x, 50.0 - spot.y)


@dataclass(frozen=True)
class PlayOption:
    play: Play
    usage: float


FIVE_OUT = Play(
    "Five Out",
    (
        Vec2(65, 25),
        Vec2(72, 7),
        Vec2(72, 43),
        Vec2(86, 8),
        Vec2(86, 42),
    ),
)

HORNS = Play(
    "Horns",
    (
        Vec2(65, 25),
        Vec2(74, 7),
        Vec2(74, 43),
        Vec2(78, 18),
        Vec2(78, 32),
    ),
)

PLAYS = {play.name.lower(): play for play in (FIVE_OUT, HORNS)}
