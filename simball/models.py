from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import math


class TeamSide(Enum):
    HOME = "home"
    AWAY = "away"


@dataclass(frozen=True)
class Vec2:
    x: float
    y: float

    def distance_to(self, other: Vec2) -> float:
        return math.hypot(self.x - other.x, self.y - other.y)

    def move_toward(self, target: Vec2, distance: float) -> Vec2:
        remaining = self.distance_to(target)
        if remaining == 0 or distance >= remaining:
            return target
        ratio = distance / remaining
        return Vec2(self.x + (target.x - self.x) * ratio, self.y + (target.y - self.y) * ratio)


@dataclass(frozen=True)
class Tendencies:
    shoot: float = 0.5
    pass_ball: float = 0.5
    drive: float = 0.5


@dataclass(frozen=True)
class Ratings:
    shooting: int
    passing: int
    defense: int
    speed: int
    rebounding: int


@dataclass
class Player:
    number: int
    player_id: str
    name: str
    position: str
    height_inches: int
    weight_lb: int
    ratings: Ratings
    tendencies: Tendencies
    location: Vec2
    target: Vec2
    has_ball: bool = False
    energy: float = 1.0
    activity: str = "spacing"
    movement_modifier: float = 1.0
    reaction_time: float = 0.0
    reaction_remaining: float = 0.0
    route_offset: float = 0.0

    @property
    def size_factor(self) -> float:
        return 1.0 + (self.height_inches - 78) * 0.012

    @property
    def speed_fps(self) -> float:
        return (8.0 + self.ratings.speed * 0.055) * (0.85 + self.energy * 0.15) * self.movement_modifier

    def route_target(self) -> Vec2:
        distance = self.location.distance_to(self.target)
        if distance == 0:
            return self.target
        dx = self.target.x - self.location.x
        dy = self.target.y - self.location.y
        lateral = self.route_offset * min(1.0, distance / 12.0)
        return Vec2(self.target.x - dy / distance * lateral, self.target.y + dx / distance * lateral)


@dataclass
class Team:
    name: str
    symbol: str
    side: TeamSide
    players: list[Player]
    score: int = 0

    def player(self, player_id: str) -> Player:
        return next(player for player in self.players if player.player_id == player_id)


@dataclass(frozen=True)
class Event:
    game_time: float
    text: str


@dataclass
class GameState:
    home: Team
    away: Team
    offense: TeamSide
    game_clock: float
    shot_clock: float
    possession_number: int = 1
    events: list[Event] = field(default_factory=list)
    finished: bool = False

    def team(self, side: TeamSide) -> Team:
        return self.home if side is TeamSide.HOME else self.away

    @property
    def offense_team(self) -> Team:
        return self.team(self.offense)

    @property
    def defense_team(self) -> Team:
        return self.away if self.offense is TeamSide.HOME else self.home
