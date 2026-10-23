# Simball

Simball is an agent-based basketball simulator built to model the game accurately while remaining fully customizable. Its command-line court provides a simple view of a more detailed simulation driven by player attributes, tendencies, movement, and decision-making.

## Run

Python 3.10 or newer is required.

```bash
cd simball
python -m simball --config configs/coach_example.json
```

Teams, players, ratings, tendencies, and plays can be changed in the JSON configuration file.

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

## Test

```bash
python -m unittest discover -s tests -v
```
