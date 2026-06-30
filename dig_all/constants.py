Prefix = '!!dig-all'
PluginName = 'DigAll'

# Objective the DiggyScoreboard datapack writes each tick; also carries the grand total.
SidebarObjective = 'dig-all'
# Fake player the datapack fills with the grand total on every dig objective each tick.
TotalName = 'Total'
# Objective owned by this plugin, holding the offline-player baseline.
HelperObjective = 'dig-helper'

# Dig category -> display objective created by `/function diggy:install`.
DigObjectives = {
	'all': 'dig-all',
	'pickaxe': 'dig-pickaxe',
	'axe': 'dig-axe',
	'shovel': 'dig-shovel',
	'hoe': 'dig-hoe',
	'shears': 'dig-shears',
}
# Dig category -> fake player (on HelperObjective) holding the offline sum for that category.
OfflineHolders = {category: '#off_{}'.format(category) for category in DigObjectives}

# Mirror of the datapack's definition of a "dig": a durability hit on a mining tool.
ToolMaterials = ('wooden', 'stone', 'iron', 'diamond', 'golden', 'netherite')
DigCategories = {
	'pickaxe': ['minecraft:{}_pickaxe'.format(material) for material in ToolMaterials],
	'axe': ['minecraft:{}_axe'.format(material) for material in ToolMaterials],
	'shovel': ['minecraft:{}_shovel'.format(material) for material in ToolMaterials],
	'hoe': ['minecraft:{}_hoe'.format(material) for material in ToolMaterials],
	'shears': ['minecraft:shears'],
}

# Real diggers never exceed this; larger scoreboard values are overflowed (32-bit) bot scores.
MaxSaneScore = 1_000_000_000
