# Simball

Simball is an agent-based basketball simulator built to model the game accurately while remaining fully customizable. Its command-line court provides a simple view of a more detailed simulation driven by player attributes, tendencies, movement, and decision-making.

## Run

Python 3.10 or newer is required.

```bash
cd simball
python -m simball --config configs/coach_example.json
```

Teams, players, ratings, tendencies, and plays can be changed in the JSON configuration file.
Configurations must include `"version": 1`. Simball rejects missing, obsolete, and newer unsupported versions with a migration-oriented error instead of trying to interpret an incompatible file.

Each team can use a weighted playbook. Usage values are relative weights and do not need to add up to one:

```json
"home_plays": [
  {"play": "motion", "usage": 0.75},
  {"play": "horns", "usage": 0.25}
]
```

Play names reference entries in the top-level `plays` object. A play is selected at the start of each possession, and `--seed` makes the sequence reproducible. The singular `home_play` and `away_play` fields remain supported for one-play teams.

Validate a configuration without running a game:

```bash
python -m simball --config configs/coach_example.json --validate
```

## Project direction

The goal is to give coaches and basketball researchers a way to test player combinations and strategies through repeatable simulations. Future plans include:

- Real NBA and college player measurements, statistics, and tendencies
- Custom inbounds, transition, and half-court plays
- More accurate screens, cuts, defensive schemes, and player decisions
- Lineup and player-configuration comparisons
- Possession-level results and analytics
- Tools for authoring and visualizing plays

The long-term priority is an accurate, data-driven simulation that can adapt to different teams, players, and coaching ideas.

## Inspiration and related projects

- [bball-coach](https://www.bball-coach.com/)
- [Coach Canvas](https://use.coachcanvas.app/)
- [BasketballGAN: Generating Basketball Play Simulation Through Sketching](https://arxiv.org/abs/1909.07088)

These projects provide references for coaching workflows, play visualization, and interactive basketball simulation. Simball's focus remains reproducible, configurable agent behavior and possession-level analysis.

## Test

```bash
python -m unittest discover -s tests -v
```
