import threading
from typing import Callable, NamedTuple, Optional, Set

from mcdreforged.api.all import *

from dig_all import constants, stats
from dig_all.config import Config
from dig_all.utils import is_bot, parse_score, query_names_after_colon

config: Config
PLUGIN_ID: Optional[str] = None

_excluded: Set[str] = set()   # lowercase excluded names, refreshed on config load
_zbots: Set[str] = set()      # lowercase bot-team members, refreshed on each reseed
_timer_lock = threading.Lock()
_timer: Optional[threading.Timer] = None


class ReseedResult(NamedTuple):
	offline_total: int
	offline_diggers: int
	online: int
	scanned: int
	bots: int
	source: str


def tr(translation_key: str, *args, **kwargs) -> RTextMCDRTranslation:
	return ServerInterface.get_instance().rtr('{}.{}'.format(PLUGIN_ID, translation_key), *args, **kwargs)


# --------------------------------------------------------------------------- #
#  Player filtering                                                           #
# --------------------------------------------------------------------------- #

def eligible(name: str) -> bool:
	"""A real, countable digger: not a fake player, not a bot, not a rename duplicate."""
	if name == constants.TotalName or name.startswith('#') or name.startswith('const'):
		return False
	if is_bot(name):
		return False
	low = name.lower()
	return low not in _excluded and low not in _zbots


# --------------------------------------------------------------------------- #
#  RCON helpers                                                               #
# --------------------------------------------------------------------------- #

def get_tracked_names(server: ServerInterface):
	return query_names_after_colon(server.rcon_query('scoreboard players list'))


def get_online_players(server: ServerInterface):
	return query_names_after_colon(server.rcon_query('list'))


def get_team_members(server: ServerInterface, team: str):
	return query_names_after_colon(server.rcon_query('team list {}'.format(team)))


def get_score(server: ServerInterface, name: str, objective: str) -> int:
	return parse_score(server.rcon_query('scoreboard players get {} {}'.format(name, objective)))


def set_score(server: ServerInterface, name: str, objective: str, value: int):
	"""Set a score via RCON. Its feedback returns over the RCON channel (captured, discarded)
	instead of being broadcast to online ops, so bookkeeping writes stay silent without
	touching the sendCommandFeedback gamerule (admins keep seeing their own command output)."""
	server.rcon_query('scoreboard players set {} {} {}'.format(name, objective, value))


# --------------------------------------------------------------------------- #
#  Offline baseline                                                           #
# --------------------------------------------------------------------------- #

def do_reseed(server: ServerInterface) -> Optional[ReseedResult]:
	"""Rebuild the offline baseline (and offline players' per-player scores) from the stats files.

	The stats files are the source of truth: they never drift and they include every historical
	player. Reading from them also means a 32-bit-overflowed bot score can never poison the total.
	Falls back to scanning the scoreboard when the stats directory is unavailable. Returns ``None``
	if RCON is down.
	"""
	global _zbots
	if not server.is_rcon_running():
		return None

	_zbots = {name.lower() for name in get_team_members(server, config.bot_team)}
	online = {name.lower() for name in get_online_players(server)}
	players = stats.player_digs(_excluded)

	baseline = {category: 0 for category in constants.DigObjectives}
	offline_diggers = 0

	# All the scoreboard writes below go through RCON (set_score): the command feedback
	# returns over the RCON channel instead of being broadcast to online ops, so this
	# ~1k-write periodic reseed stays completely silent WITHOUT touching the
	# sendCommandFeedback gamerule (no stray "Set [dig-*]" or "sendCommandFeedback is
	# now set to: true" lines, and admins keep normal command output for everything else).
	if players is not None:
		for name, digs in players.items():
			if not eligible(name) or name.lower() in online:
				continue  # online players are summed live by the datapack
			for category, objective in constants.DigObjectives.items():
				set_score(server, name, objective, digs[category])
			for category in baseline:
				baseline[category] += digs[category]
			offline_diggers += 1
		source, scanned = 'stats', len(players)
	else:
		names = get_tracked_names(server)
		for name in names:
			if not eligible(name) or name.lower() in online:
				continue
			value = get_score(server, name, constants.DigObjectives['all'])
			if value == 0 or abs(value) > constants.MaxSaneScore:
				continue  # 0 = untracked, huge = overflowed bot score
			baseline['all'] += value
			for category in ('pickaxe', 'axe', 'shovel', 'hoe', 'shears'):
				baseline[category] += get_score(server, name, constants.DigObjectives[category])
			offline_diggers += 1
		source, scanned = 'scoreboard', len(names)

	for category, value in baseline.items():
		set_score(server, constants.OfflineHolders[category], constants.HelperObjective, value)

	server.logger.info(
		'Reseeded offline baseline #off_all={:,} from {} offline digger(s) '
		'(source={}, online={}, scanned={}, bots={})'.format(
			baseline['all'], offline_diggers, source, len(online), scanned, len(_zbots)))
	return ReseedResult(baseline['all'], offline_diggers, len(online), scanned, len(_zbots), source)


def adjust_baseline(server: ServerInterface, player: str, joined: bool):
	"""Keep the baseline complementary to the live sum: on join the datapack starts counting the
	player, so subtract them from the baseline; on leave, fold their current scores back in."""
	# Go through RCON so the 6 bookkeeping writes never broadcast to online ops (no
	# "Set [dig-helper] ..." spam) without touching the sendCommandFeedback gamerule.
	# If RCON is momentarily down we skip it; the periodic reseed heals any drift.
	if not server.is_rcon_running():
		return
	operation = '-=' if joined else '+='
	for category, objective in constants.DigObjectives.items():
		server.rcon_query('scoreboard players operation {} {} {} {} {}'.format(
			constants.OfflineHolders[category], constants.HelperObjective, operation, player, objective))


# --------------------------------------------------------------------------- #
#  Commands                                                                   #
# --------------------------------------------------------------------------- #

def cmd_show(source: CommandSource):
	source.get_server().execute(
		'scoreboard objectives setdisplay sidebar {}'.format(constants.SidebarObjective))
	source.reply(tr('command.sidebar_set'))


@new_thread('{} reseed'.format(constants.PluginName))
def cmd_reseed(source: CommandSource):
	result = do_reseed(source.get_server())
	if result is None:
		source.reply(tr('reseed.no_rcon'))
		return
	source.reply(tr('reseed.done', result.offline_total))
	source.reply(tr('reseed.detail', result.offline_diggers, result.online,
		config.bot_team, result.bots, result.scanned))


@new_thread('{} status'.format(constants.PluginName))
def cmd_status(source: CommandSource):
	server = source.get_server()
	if not server.is_rcon_running():
		source.reply(tr('reseed.no_rcon'))
		return
	baseline = get_score(server, constants.OfflineHolders['all'], constants.HelperObjective)
	total = get_score(server, constants.TotalName, constants.DigObjectives['all'])
	source.reply(tr('status.line', total, baseline, total - baseline))


def register_command(server: PluginServerInterface):
	server.register_command(
		Literal(constants.Prefix).
		runs(cmd_show).
		then(Literal('reseed').runs(cmd_reseed)).
		then(Literal('status').runs(cmd_status))
	)
	server.register_help_message('{} reseed'.format(constants.Prefix), tr('help.reseed'))
	server.register_help_message('{} status'.format(constants.Prefix), tr('help.status'))


# --------------------------------------------------------------------------- #
#  Periodic self-heal                                                         #
# --------------------------------------------------------------------------- #

def _start_timer(minutes: int, callback: Callable[[], None]):
	global _timer
	_timer = threading.Timer(minutes * 60, callback)
	_timer.daemon = True
	_timer.start()


def schedule_safety_reseed(server: ServerInterface):
	minutes = config.reseed_interval_minutes
	if minutes <= 0:
		return

	def tick():
		do_reseed(server)
		with _timer_lock:
			_start_timer(minutes, tick)

	with _timer_lock:
		_start_timer(minutes, tick)


# --------------------------------------------------------------------------- #
#  MCDR event handlers                                                        #
# --------------------------------------------------------------------------- #

def on_player_joined(server: PluginServerInterface, player: str, info: Info):
	if eligible(player):
		adjust_baseline(server, player, joined=True)


def on_player_left(server: PluginServerInterface, player: str):
	if eligible(player):
		adjust_baseline(server, player, joined=False)


@new_thread('{} startup reseed'.format(constants.PluginName))
def on_server_startup(server: PluginServerInterface):
	do_reseed(server)


@new_thread('{} load reseed'.format(constants.PluginName))
def _reseed_async(server: ServerInterface):
	do_reseed(server)


def on_load(server: PluginServerInterface, prev_module):
	global config, PLUGIN_ID, _excluded
	PLUGIN_ID = server.get_self_metadata().id
	config = server.load_config_simple(target_class=Config)
	Config.set_instance(config)
	_excluded = {name.lower() for name in config.exclude_names}

	server.register_help_message(constants.Prefix, tr('summary_help'))
	register_command(server)

	if server.is_rcon_running():  # hot-reloaded while the server is already up
		_reseed_async(server)
	schedule_safety_reseed(server)


def on_unload(server: PluginServerInterface):
	global _timer
	with _timer_lock:
		if _timer is not None:
			_timer.cancel()
			_timer = None
