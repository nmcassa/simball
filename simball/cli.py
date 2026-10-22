from __future__ import annotations

import argparse
import os
import sys
import time

from .config import ConfigError, load_setup
from .engine import Game, GameConfig
from .plays import PLAYS
from .render import render


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(prog="simball", description="Agent-based command-line basketball simulation")
    result.add_argument("--duration", type=float, default=120, help="game length in simulated seconds")
    result.add_argument("--speed", type=float, default=4, help="simulation speed multiplier; 0 runs instantly")
    result.add_argument("--seed", type=int, default=None, help="random seed for reproducible games")
    result.add_argument("--play", choices=sorted(PLAYS), default="five out", help="offensive alignment")
    result.add_argument("--config", help="JSON file containing teams, players, tendencies, and plays")
    result.add_argument("--no-clear", action="store_true", help="print frames instead of refreshing the screen")
    return result


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    if args.duration <= 0 or args.speed < 0:
        parser().error("duration must be positive and speed cannot be negative")
    game_config = GameConfig(duration_seconds=args.duration, seed=args.seed)
    if args.config:
        try:
            setup = load_setup(args.config)
        except ConfigError as error:
            parser().error(str(error))
        game = Game(game_config, home=setup.home, away=setup.away, team_plays=setup.plays)
    else:
        game = Game(game_config, PLAYS[args.play])
    render_interval = 0.2
    next_frame = 0.0
    while not game.state.finished:
        game.tick()
        if game.elapsed >= next_frame or game.state.finished:
            if not args.no_clear and sys.stdout.isatty():
                os.system("cls" if os.name == "nt" else "clear")
            print(render(game.state), flush=True)
            next_frame += render_interval
            if args.speed:
                time.sleep(render_interval / args.speed)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
