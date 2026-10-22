from __future__ import annotations

from .models import GameState


def render(state: GameState, width: int = 71, height: int = 21) -> str:
    grid = [[" " for _ in range(width)] for _ in range(height)]
    for x in range(width):
        grid[0][x] = "-"
        grid[-1][x] = "-"
    for y in range(height):
        grid[y][0] = "|"
        grid[y][-1] = "|"
        grid[y][width // 2] = ":"
    grid[0][0] = grid[0][-1] = grid[-1][0] = grid[-1][-1] = "+"
    center_y = height // 2
    for hoop_x in (4, width - 5):
        grid[center_y][hoop_x] = "#"
    occupants: dict[tuple[int, int], list[str]] = {}
    for team in (state.home, state.away):
        for player in team.players:
            x = max(1, min(width - 2, round(player.location.x / 94 * (width - 1))))
            y = max(1, min(height - 2, round(player.location.y / 50 * (height - 1))))
            marker = team.symbol.lower() if player.has_ball else team.symbol
            occupants.setdefault((x, y), []).append(marker)
    for (x, y), markers in occupants.items():
        grid[y][x] = markers[0] if len(markers) == 1 else "*"
    minutes, seconds = divmod(max(0, round(state.game_clock)), 60)
    header = (
        f" {state.home.name} {state.home.score} - {state.away.score} {state.away.name}"
        f"   {minutes:02d}:{seconds:02d}   Shot {max(0, state.shot_clock):04.1f}"
        f"   {state.offense_team.name} ball "
    )
    legend = "X Home  O Away  lowercase = ball  # basket"
    movement = "  ".join(
        f"{team.symbol}{player.number}:{player.activity}"
        for team in (state.home, state.away)
        for player in team.players
        if player.activity not in ("spacing", "defending")
    )
    event_lines = [f"{event.game_time:5.1f}  {event.text}" for event in reversed(state.events[-4:])]
    return "\n".join(
        [header, legend, *("".join(row) for row in grid), f"Movement: {movement or 'forming alignment'}", "Play-by-play", *event_lines]
    )
