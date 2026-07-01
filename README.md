# DigAll

An [MCDReforged](https://github.com/MCDReforged/MCDReforged) plugin that gives
[DiggyScoreboard](https://github.com/Fallen-Breath/DiggyScoreboard) a **real grand total**
of blocks mined, including **offline and historical** players, with bots excluded.

DiggyScoreboard counts tool uses (≈ blocks mined) for whoever is **online**. DigAll keeps an
offline baseline so the `Total` also covers everyone who isn't online right now, i.e. every
block ever mined on the server.

```
Total = #off_all  +  Σ( online players, team != <bot_team> )
```

## How it works

On boot (and on demand) DigAll reseeds the offline baseline straight from the vanilla stats
files (`world/stats/*.json`, keyed by UUID): it sums the tool families
(pickaxe / axe / shovel / hoe + shears), maps each UUID to a current name, drops bots, and
writes the per-player `dig-*` scores plus the `#off_*` constants over RCON. It self-heals on
every restart, so newly tracked players fold in automatically.

Two gotchas it handles:

- **32-bit overflow.** A bot count big enough to wrap a signed 32-bit scoreboard int could
  drag `#off_all` negative. DigAll excludes the bot team **and** rejects any per-player value
  with `|v| > 1e9` before summing.
- **Renames.** Stats are keyed by UUID, so renamed players can appear twice. DigAll reuses
  StatsHelper's UUID->name map (which carries the rename de-duplication fix, see Credits) and
  a manual `aliases` table for players whose name history was wiped.

## Requirements

- MCDReforged `>=2.1.0`
- A Minecraft server with **RCON** enabled
- [DiggyScoreboard](https://github.com/Fallen-Breath/DiggyScoreboard) installed (the base datapack)
- [StatsHelper](https://github.com/CodeW4VE/StatsHelper) (for the shared UUID->name map)

## Commands

```
!!dig-all status                  # show the totals
!!dig-all reseed                  # rebuild the offline baseline from the stats files
!!MCDR plugin reload dig_all
```

## Config

`config/dig_all/config.json` (generated on first run). Key fields:

- `bot_team`: Carpet bot team to exclude (e.g. `zBots`).
- `aliases`: manual UUID -> name for players whose name history was wiped. The shipped
  example is the author's own account (`TVTvirus`); replace it with your own.
- `reseed_interval_minutes`: periodic self-heal (`0` = only on start + manual reseed).

> Hammering RCON from outside can drop MCDR's internal RCON connection (`!!dig-all` then says
> "RCON not available"). A server restart fixes it: MCDR reconnects and reseeds on boot.

## Credits

- **[DiggyScoreboard](https://github.com/Fallen-Breath/DiggyScoreboard)**: Fallen_Breath (the base datapack this builds on).
- **[StatsHelper](https://github.com/TISUnion/StatsHelper)**: TISUnion (UUID -> name mapping).
- **UUID / rename de-duplication fix** in StatsHelper, by [KarlaPrz02](https://github.com/KarlaPrz02) (Katherina).
- **Total layer, offline baseline & integration**: TVTvirus ([MineWave](https://w4ve.xyz/)).

## License

[MIT](LICENSE). Part of [CodeW4VE](https://github.com/CodeW4VE).
