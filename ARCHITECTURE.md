# Architecture

## Guiding Principle
Keep simulation logic separate from the PyQt UI and keep the active game focused on property ownership.

## Major Packages
- `core/`: clock, engine, events, saves, state
- `world/`: countries, regions, cities, property demand data
- `industries/real_estate/`: building config and property models
- `companies/`: lightweight company and holding-company data
- `finance/`: statements, loans, credit ratings
- `npcs/`: property competitor simulation
- `news/`: headline feed
- `gameplay/`: player-facing property actions
- `ui/`: PyQt windows, navigation, tables, dialogs
- `config/`: themes
- `tests/`: active property-game tests

## Active Simulation Flow
`GameEngine` advances the clock, processes player property operations, processes NPC property competitors, and publishes news.

## Disabled Systems
Banking, stocks, research, generic industry plugins, and acquisition/subsidiary services were removed from the active structure during simplification.
