from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import random

from .models import Event, GameState, Player, Ratings, Team, TeamSide, Tendencies, Vec2
from .plays import FIVE_OUT, Play


@dataclass(frozen=True)
class GameConfig:
    duration_seconds: float = 120.0
    tick_seconds: float = 0.1
    seed: int | None = None


class MotionPhase(Enum):
    SPACING = "spacing"
    SCREENING = "screening"
    CUTTING = "cutting"
    RESETTING = "resetting"


@dataclass
class Motion:
    phase: MotionPhase = MotionPhase.SPACING
    elapsed: float = 0.0
    phase_elapsed: float = 0.0
    screener_number: int = 5
    cutter_number: int = 2


def _roster(name: str, symbol: str, side: TeamSide) -> Team:
    profiles = (
        ("PG", 74, 185, Ratings(76, 82, 70, 86, 48), Tendencies(0.45, 0.75, 0.65)),
        ("SG", 77, 205, Ratings(82, 70, 68, 80, 55), Tendencies(0.75, 0.45, 0.55)),
        ("SF", 80, 220, Ratings(77, 68, 75, 76, 67), Tendencies(0.60, 0.48, 0.65)),
        ("PF", 82, 240, Ratings(69, 58, 79, 68, 80), Tendencies(0.48, 0.40, 0.70)),
        ("C", 84, 255, Ratings(62, 55, 83, 59, 87), Tendencies(0.40, 0.45, 0.72)),
    )
    players = []
    for index, (position, height, weight, ratings, tendencies) in enumerate(profiles, 1):
        start = Vec2(12 + index * 2, 6 + index * 8)
        players.append(Player(index, f"{name} {position}", position, height, weight, ratings, tendencies, start, start))
    return Team(name, symbol, side, players)


class Game:
    def __init__(
        self,
        config: GameConfig = GameConfig(),
        play: Play = FIVE_OUT,
        home: Team | None = None,
        away: Team | None = None,
        team_plays: dict[TeamSide, Play] | None = None,
    ) -> None:
        self.config = config
        self.play = play
        self.rng = random.Random(config.seed)
        self.team_plays = team_plays or {TeamSide.HOME: play, TeamSide.AWAY: play}
        home_team = home or _roster("Home", "X", TeamSide.HOME)
        away_team = away or _roster("Away", "O", TeamSide.AWAY)
        self.state = GameState(home_team, away_team, TeamSide.HOME, config.duration_seconds, 24.0)
        self.elapsed = 0.0
        self.action_cooldown = 1.5
        self.motion = Motion()
        self._start_possession(initial=True)

    def tick(self) -> GameState:
        if self.state.finished:
            return self.state
        dt = min(self.config.tick_seconds, self.state.game_clock)
        self.elapsed += dt
        self.state.game_clock -= dt
        self.state.shot_clock -= dt
        self.action_cooldown -= dt
        self._update_motion(dt)
        self._assign_targets()
        self._move_players(dt)
        if self.state.shot_clock <= 0:
            self._event("Shot-clock violation")
            self._change_possession()
        elif self.action_cooldown <= 0:
            self._choose_action()
        if self.state.game_clock <= 0:
            self.state.game_clock = 0
            self.state.finished = True
            self._event("Final buzzer")
        return self.state

    def _assign_targets(self) -> None:
        attacking_right = self.state.offense is TeamSide.HOME
        offense = self.state.offense_team
        defense = self.state.defense_team
        active_play = self.team_plays[self.state.offense]
        for player in offense.players:
            player.target = active_play.target_for(player, attacking_right)
            player.activity = "handling" if player.has_ball else "spacing"
            player.movement_modifier = 1.0
        handler = next(player for player in offense.players if player.has_ball)
        screener = offense.players[self.motion.screener_number - 1]
        cutter = offense.players[self.motion.cutter_number - 1]
        direction = 1 if attacking_right else -1
        screen_spot = Vec2(
            max(8, min(86, handler.location.x + direction * 4)),
            max(7, min(43, handler.location.y + (4 if handler.location.y < 25 else -4))),
        )
        hoop = Vec2(89, 25) if attacking_right else Vec2(5, 25)
        if self.motion.phase is MotionPhase.SCREENING:
            screener.target = screen_spot
            screener.activity = "setting screen"
            cutter.target = Vec2(screen_spot.x - direction * 2, screen_spot.y)
            cutter.activity = "using screen"
        elif self.motion.phase is MotionPhase.CUTTING:
            cutter.target = Vec2(hoop.x - direction * 3, hoop.y + (3 if cutter.number % 2 else -3))
            cutter.activity = "cutting"
            screener.target = Vec2(hoop.x - direction * 7, hoop.y)
            screener.activity = "rolling"
        elif self.motion.phase is MotionPhase.RESETTING:
            cutter.activity = "clearing"
            screener.activity = "popping"
        for defender, matchup in zip(defense.players, offense.players):
            basket_x = 89.0 if attacking_right else 5.0
            defender.target = Vec2(
                matchup.location.x + (basket_x - matchup.location.x) * 0.12,
                matchup.location.y,
            )
            defender.activity = "defending"
            defender.movement_modifier = 1.0
        if self.motion.phase in (MotionPhase.SCREENING, MotionPhase.CUTTING):
            cutter_defender = defense.players[cutter.number - 1]
            if cutter_defender.location.distance_to(screener.location) < 5.0:
                cutter_defender.movement_modifier = 0.48
                cutter_defender.activity = "fighting screen"

    def _update_motion(self, dt: float) -> None:
        self.motion.elapsed += dt
        self.motion.phase_elapsed += dt
        if self.motion.phase is MotionPhase.SPACING and self.motion.phase_elapsed >= 2.5:
            handler = next(player for player in self.state.offense_team.players if player.has_ball)
            candidates = [player for player in self.state.offense_team.players if not player.has_ball]
            bigs = [player for player in candidates if player.position in ("PF", "C")]
            wings = [player for player in candidates if player.position in ("SG", "SF")]
            self.motion.screener_number = max(bigs, key=lambda player: player.height_inches + player.weight_lb / 20).number
            self.motion.cutter_number = max(wings or candidates, key=lambda player: player.ratings.speed).number
            self.motion.phase = MotionPhase.SCREENING
            self.motion.phase_elapsed = 0.0
            self._event(f"{self.state.offense_team.players[self.motion.screener_number - 1].name} comes to screen for {handler.name}")
        elif self.motion.phase is MotionPhase.SCREENING and self.motion.phase_elapsed >= 1.8:
            self.motion.phase = MotionPhase.CUTTING
            self.motion.phase_elapsed = 0.0
            cutter = self.state.offense_team.players[self.motion.cutter_number - 1]
            screener = self.state.offense_team.players[self.motion.screener_number - 1]
            self._event(f"{cutter.name} cuts as {screener.name} rolls")
        elif self.motion.phase is MotionPhase.CUTTING and self.motion.phase_elapsed >= 2.4:
            self.motion.phase = MotionPhase.RESETTING
            self.motion.phase_elapsed = 0.0
        elif self.motion.phase is MotionPhase.RESETTING and self.motion.phase_elapsed >= 2.0:
            self.motion.phase = MotionPhase.SPACING
            self.motion.phase_elapsed = 0.0

    def _move_players(self, dt: float) -> None:
        for team in (self.state.home, self.state.away):
            for player in team.players:
                player.location = player.location.move_toward(player.target, player.speed_fps * dt)
                player.energy = max(0.55, player.energy - dt * 0.0008)

    def _choose_action(self) -> None:
        handler = next(player for player in self.state.offense_team.players if player.has_ball)
        closest = min(self.state.defense_team.players, key=lambda player: player.location.distance_to(handler.location))
        pressure = max(0.0, 1.0 - closest.location.distance_to(handler.location) / 8.0)
        attacking_right = self.state.offense is TeamSide.HOME
        hoop = Vec2(89, 25) if attacking_right else Vec2(5, 25)
        distance = handler.location.distance_to(hoop)
        urgency = max(0.0, (7.0 - self.state.shot_clock) / 7.0)
        shoot_score = handler.tendencies.shoot + urgency + max(0.0, (24.0 - distance) / 30.0) - pressure * 0.35
        if distance <= 28 and self.rng.random() < min(0.9, shoot_score * 0.45):
            self._shoot(handler, closest, distance)
        elif self.rng.random() < handler.tendencies.pass_ball * 0.5:
            self._pass(handler)
        else:
            drive_x = hoop.x - (5 if attacking_right else -5)
            handler.target = Vec2(drive_x, 25 + self.rng.uniform(-7, 7))
            self._event(f"{handler.name} drives")
            self.action_cooldown = self.rng.uniform(0.7, 1.4)

    def _pass(self, passer: Player) -> None:
        teammates = [player for player in self.state.offense_team.players if player is not passer]
        receiver = max(teammates, key=lambda player: self._receiver_score(player))
        passer.has_ball = False
        receiver.has_ball = True
        steal_risk = max(0.015, 0.11 - passer.ratings.passing / 1200)
        if self.rng.random() < steal_risk:
            self._event(f"Turnover by {passer.name}")
            self._change_possession()
            return
        self._event(f"{passer.name} passes to {receiver.name}")
        self.action_cooldown = self.rng.uniform(0.8, 1.6)

    def _receiver_score(self, player: Player) -> float:
        score = player.ratings.shooting + self.rng.uniform(-20, 20)
        if player.activity == "cutting":
            score += 45
        elif player.activity == "rolling":
            score += 28
        return score

    def _shoot(self, shooter: Player, defender: Player, distance: float) -> None:
        points = 3 if distance >= 23.75 else 2
        range_penalty = abs(distance - (21 if points == 3 else 8)) * 0.009
        contest = max(0.0, 1.0 - defender.location.distance_to(shooter.location) / 6.0)
        height_effect = (shooter.height_inches - defender.height_inches) * 0.006
        probability = 0.24 + shooter.ratings.shooting * 0.004 - range_penalty - contest * 0.17 + height_effect
        probability = max(0.08, min(0.78, probability))
        if self.rng.random() < probability:
            self.state.offense_team.score += points
            self._event(f"{shooter.name} makes a {points}-pointer")
            self._change_possession()
            return
        self._event(f"{shooter.name} misses a {points}-pointer")
        offense_rebounding = sum(player.ratings.rebounding * player.size_factor for player in self.state.offense_team.players)
        defense_rebounding = sum(player.ratings.rebounding * player.size_factor for player in self.state.defense_team.players)
        if self.rng.random() < offense_rebounding / (offense_rebounding + defense_rebounding) * 0.55:
            rebounder = max(self.state.offense_team.players, key=lambda player: player.ratings.rebounding * self.rng.random())
            for player in self.state.offense_team.players:
                player.has_ball = player is rebounder
            self.state.shot_clock = 14.0
            self._event(f"Offensive rebound: {rebounder.name}")
            self.action_cooldown = 1.0
        else:
            self._change_possession()

    def _change_possession(self) -> None:
        self.state.offense = TeamSide.AWAY if self.state.offense is TeamSide.HOME else TeamSide.HOME
        self.state.possession_number += 1
        self._start_possession()

    def _start_possession(self, initial: bool = False) -> None:
        for team in (self.state.home, self.state.away):
            for player in team.players:
                player.has_ball = False
                player.activity = "spacing"
                player.movement_modifier = 1.0
        self.state.offense_team.players[0].has_ball = True
        self.state.shot_clock = 24.0
        self.action_cooldown = 1.8
        self.motion = Motion()
        if not initial:
            self._event(f"{self.state.offense_team.name} possession")

    def _event(self, text: str) -> None:
        self.state.events.append(Event(self.state.game_clock, text))
        self.state.events = self.state.events[-8:]
