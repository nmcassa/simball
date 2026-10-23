# Simball TODO

## 1. Stabilize the simulation model

- [ ] Separate possession logic into movement, decision, and outcome systems
- [ ] Give every player velocity, acceleration, facing direction, and reaction time
- [ ] Add seeded variation to player reaction timing, movement routes, and path selection so repeated plays do not produce identical agent behavior
- [ ] Prevent players from occupying the same physical space
- [ ] Model ball travel for passes and shots instead of transferring possession instantly
- [ ] Add deterministic tests for movement, possessions, scoring, and clock behavior

## 2. Expand configuration

- [ ] Publish a documented JSON schema for teams, players, and plays
- [x] Add stable player IDs instead of relying on roster order
- [x] Allow teams to select multiple plays with usage frequencies
- [ ] Support substitutions, rotations, and lineup-specific assignments
- [x] Add a command that validates a configuration without running a game
- [x] Add configuration versioning and migration errors

## 3. Build a play system

- [ ] Represent plays as timed phases with player assignments and destinations
- [ ] Support actions for cuts, screens, rolls, pops, handoffs, and spacing
- [ ] Define triggers such as pass completion, screen contact, or elapsed time
- [ ] Allow branches when a read is open or defended
- [ ] Add baseline and sideline inbounds starting positions
- [ ] Create example half-court, baseline-out-of-bounds, and sideline-out-of-bounds plays

## 4. Improve basketball behavior

- [ ] Add on-ball, help, deny, switch, hedge, drop, and zone defensive assignments
- [ ] Detect passing lanes, shot contests, screen contact, and defensive rotations
- [ ] Use player tendencies to choose shots, passes, drives, and cuts
- [ ] Make height, wingspan, strength, speed, and fatigue affect outcomes
- [ ] Model turnovers, fouls, free throws, blocks, and loose balls
- [ ] Calibrate shot and possession outcomes against realistic basketball ranges

## 5. Add data and analytics

- [ ] Define a source-neutral format for NBA and college player data
- [ ] Write an importer for one legally usable public dataset
- [ ] Record the source, season, and transformation of every imported rating
- [ ] Derive initial ratings and tendencies from documented statistical formulas
- [ ] Export box scores, play-by-play, shot locations, and possession summaries
- [ ] Add batch simulation for comparing lineups and plays across many seeded games
- [ ] Report uncertainty and sample size with comparison results

## 6. Improve coaching tools

- [ ] Add CLI commands to list teams, players, and plays
- [ ] Support pause, step, replay, and adjustable simulation speed
- [ ] Show player numbers, ball movement, screen locations, and play phases clearly
- [ ] Add a play-debug mode that explains each agent decision
- [ ] Create a simple play-authoring interface after the play schema stabilizes

## Near-term milestone

A useful first milestone is a reproducible half-court possession in which a configured lineup executes a multi-phase play against a configured defense. The simulator should export the resulting events and explain why each player chose an action. Complete sections 1–3 before importing real player data or building a graphical interface.
