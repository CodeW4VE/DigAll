import re
from typing import List, Optional

_SCORE_PATTERN = re.compile(r'has (-?\d+)')


def is_bot(name: str) -> bool:
	low = name.lower()
	return low.startswith('bot_') or low.endswith('_bot')


def query_names_after_colon(response: Optional[str]) -> List[str]:
	"""Parse the comma-separated tail of vanilla ``list``-style command output."""
	if not response or ':' not in response:
		return []
	tail = response.split(':', 1)[1]
	return [name.strip() for name in tail.split(',') if name.strip()]


def parse_score(response: Optional[str]) -> int:
	"""Pull the integer out of a ``scoreboard players get`` reply (0 when unset)."""
	if response:
		match = _SCORE_PATTERN.search(response)
		if match:
			return int(match.group(1))
	return 0
