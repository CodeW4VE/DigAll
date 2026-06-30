import os
from typing import Dict, List

from mcdreforged.api.utils.serializer import Serializable


class Config(Serializable):
	# Carpet bot team; its members are excluded from the total.
	bot_team: str = 'zBots'
	# Leftover old names from renames, dropped to avoid double counting.
	# Example: ['TVTvirus_old']
	exclude_names: List[str] = []
	# Periodic self-heal reseed in minutes; 0 = only on server start and manual reseed.
	reseed_interval_minutes: int = 0
	# Where vanilla statistics live; stats_dir empty -> '<server_path>/<world_folder>/stats'.
	server_path: str = './server'
	world_folder: str = 'world'
	stats_dir: str = ''
	# StatsHelper's UUID -> name mapping, reused so both plugins agree on player names.
	statshelper_uuid_file: str = os.path.join('config', 'StatsHelper', 'uuid.json')
	# Manual UUID -> historic display name for renamed players that uuid.json never
	# mapped (they wiped their name history). Highest priority. The example below is
	# the author's own account; replace it with your renamed players (or empty it).
	aliases: Dict[str, str] = {
		'466a0fbd-7b87-431c-ab58-c1887f577deb': 'TVTvirus',
	}

	__instance: 'Config' = None

	@classmethod
	def set_instance(cls, instance: 'Config'):
		cls.__instance = instance

	@classmethod
	def get_instance(cls) -> 'Config':
		return cls.__instance
