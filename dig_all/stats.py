import glob
import json
import os
from typing import Dict, List, Optional, Set

from dig_all import constants
from dig_all.config import Config
from dig_all.utils import is_bot


def stats_dir() -> str:
	config = Config.get_instance()
	if config.stats_dir:
		return config.stats_dir
	return os.path.join(config.server_path, config.world_folder, 'stats')


def uuid_file() -> str:
	return Config.get_instance().statshelper_uuid_file


def uuid_to_name(excluded: Set[str]) -> Dict[str, str]:
	"""Map uuid (lowercase) -> a single display name.

	Collapses renames by keying on UUID, prefers a non-excluded, non-bot name, then applies the
	manual aliases from the config (which also add UUIDs that StatsHelper's uuid.json never mapped).
	"""
	try:
		with open(uuid_file(), encoding='utf-8') as file:
			raw = json.load(file)
	except (OSError, ValueError):
		return {}
	names_by_uuid: Dict[str, List[str]] = {}
	for name, uuid in raw.items():
		names_by_uuid.setdefault(str(uuid).lower(), []).append(name)
	result: Dict[str, str] = {}
	for uuid, names in names_by_uuid.items():
		preferred = [name for name in names if name.lower() not in excluded and not is_bot(name)]
		result[uuid] = (preferred or names)[0]
	for uuid, name in Config.get_instance().aliases.items():
		result[str(uuid).lower()] = name
	return result


def player_digs(excluded: Set[str]) -> Optional[Dict[str, Dict[str, int]]]:
	"""Return ``name -> {category: value, 'all': value}`` read from every ``world/stats/*.json``.

	Returns ``None`` when the stats directory is missing, so the caller can fall back to scanning
	the scoreboard. Players with no recorded digs are skipped.
	"""
	directory = stats_dir()
	if not os.path.isdir(directory):
		return None
	mapping = uuid_to_name(excluded)
	result: Dict[str, Dict[str, int]] = {}
	for path in glob.glob(os.path.join(directory, '*.json')):
		uuid = os.path.basename(path)[:-len('.json')].lower()
		name = mapping.get(uuid)
		if name is None:
			continue
		try:
			with open(path, encoding='utf-8') as file:
				used = json.load(file).get('stats', {}).get('minecraft:used', {})
		except (OSError, ValueError):
			continue
		digs = {
			category: sum(used.get(item, 0) for item in items)
			for category, items in constants.DigCategories.items()
		}
		digs['all'] = sum(digs.values())
		if digs['all'] > 0:
			result[name] = digs
	return result
