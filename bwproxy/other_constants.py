from .classes import LayoutType

VERSION: str = "v4.0"
# 0x23F is the paintbrush symbol
# Using Unicode thin spaces (U+2009) and en dash (U+2013)
CREDITS: str = chr(0x23F) + " {0} -  bwproxy"

# MTG constants: colors, basic lands, color names...

CARD_SUPERTYPES = [
    "Basic",
    "Legendary",
    "Snow",
    "World",
    "Ongoing",
    "Elite",
    "Host",
]

CARD_TYPES = [
    "Land",
    "Creature",
    "Artifact",
    "Enchantment",
    "Instant",
    "Sorcery",
    "Planeswalker",
    "Tribal",
]

BASIC_LANDS_NONSNOW = ["Plains", "Island", "Swamp", "Mountain", "Forest", "Wastes"]
BASIC_LANDS = BASIC_LANDS_NONSNOW + [
    f"Snow-Covered {l}" for l in BASIC_LANDS_NONSNOW if l != "Wastes"
]

# Can be obtained programmatically, but that's more concise
MANA_HYBRID = ["W/U", "U/B", "B/R", "R/G", "G/W", "W/B", "U/R", "B/G", "R/W", "G/U"]

LAYOUT_TYPES_DF = set([LayoutType.TDF, LayoutType.MDF])
LAYOUT_TYPES_TWO_PARTS = set([
    LayoutType.SPL,
    LayoutType.FUS,
    LayoutType.AFT,
    LayoutType.ADV,
    LayoutType.FLP
])

ACORN_PLAINTEXT = "{ACORN}"

TODO = """
Class, Sagas and Leveler frames?
Colored Mana symbols
Flavor Names for DFC, Adventures and possibly Flip?
Stop changing fonts
"""
