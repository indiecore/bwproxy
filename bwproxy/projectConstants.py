from collections import defaultdict
from copy import deepcopy
from typing import (
    Any,
    DefaultDict,
    Generic,
    TypeVar,
    Dict,
    Tuple,
    List,
    Union,
    NamedTuple
)
from typing_extensions import Self
from enum import Enum, IntEnum

VERSION: str = "v2.2"
# 0x23F is the paintbrush symbol
CREDITS: str = chr(0x23F) + " https://a11ce.com/bwproxy"

# Helper classes and functions

class Rot(IntEnum):
    # This will probably be a mistake, but I do not want to import PIL.Image
    # just so I can use Image.ROTATE_90
    ROT_0 = 1
    ROT_90 = 2
    ROT_180 = 3
    ROT_270 = 4

class LayoutType(Enum):
    STD = "standard"
    SPL = "split"
    FUS = "fuse"
    AFT = "aftermath"
    ADV = "adventure"
    FLP = "flip"
    LND = "land"
    VTK = "vanilla_token"
    TOK = "token"
    EMB = "emblem"
    TDF = "transform"
    MDF = "modal_dfc"
    ATR = "attraction"


# This is almost useless (we could use a dictionary),
# but has the advantage of syntax higlighting and autocompletion

class BorderData():
    def __init__(
        self,
        TOP: int = -1,
        BOTTOM: int = -1,
        LEFT: int = -1,
        RIGHT: int = -1,
    ):
        self.TOP: int = TOP
        self.BOTTOM: int = BOTTOM
        self.LEFT: int = LEFT
        self.RIGHT: int = RIGHT

class SizeData():
    def __init__(
        self,
        HORIZ: int = -1,
        VERT: int = -1,
    ):
        self.HORIZ: int = HORIZ
        self.VERT: int = VERT

class Border():
    def __init__(
        self,
        CARD: BorderData,
    ):
        self.CARD: BorderData = CARD
        self.IMAGE: int = -1
        self.TYPE: int = -1
        self.RULES: BorderData = BorderData()
        self.PTL_BOX: BorderData = BorderData()
        self.CREDITS: int = -1
        self.FUSE: BorderData
        self.ATTRACTION: BorderData

class Size():
    def __init__(
        self,
        CARD: SizeData,
        TITLE: int,
        IMAGE: int,
        TYPE: int,
        RULES: SizeData,
        PTL_BOX: SizeData,
        CREDITS: int,
    ):
        self.CARD: SizeData = CARD
        self.TITLE: int = TITLE
        self.IMAGE: int = IMAGE
        self.TYPE: int = TYPE
        self.RULES: SizeData = RULES
        self.PTL_BOX: SizeData = PTL_BOX
        self.CREDITS: int = CREDITS
        self.FUSE: SizeData
        self.ATTRACTION: SizeData

class FontMiddle():
    def __init__(
        self,
    ):
        self.PTL_H: int = -1
        self.PTL_V: int = -1
        self.FUSE_V: int
        self.ATTRACTION_H: int

class LayoutData():
    def __init__(
        self,
        ROTATION: Rot,
        BORDER: Border,
        SIZE: Size,
        FONT_MIDDLE: FontMiddle,
    ):
        self.LAYOUT_TYPE: LayoutType
        self.ROTATION: Rot = ROTATION
        self.BORDER: Border = BORDER
        self.SIZE: Size = SIZE
        self.FONT_MIDDLE: FontMiddle = FONT_MIDDLE


T = TypeVar("T")

class Map(Dict[str, T], Generic[T]):
    """
    Map is a dictionary that can be manipulated using dot notation instead of bracket notation.
    Just like a dictionary, it raises a KeyError if it cannot retrieve a property.
    """

    def __init__(self, *args: Dict[str, Any], **kwargs: Any):
        self.update(*args, **kwargs)

    def __getattr__(self, attr: str):
        return self[attr]

    def __setattr__(self, key: str, value: Any):
        self.__setitem__(key, value)

    def __setitem__(self, key: str, value: Any):
        super(Map, self).__setitem__(key, value)
        self.__dict__.update({key: value})

    def __delattr__(self, item: str):
        self.__delitem__(item)

    def __delitem__(self, key: str):
        super(Map, self).__delitem__(key)
        del self.__dict__[key]


class XY(NamedTuple):
    """
    XY is a two int tuple that can be added to other tuples, subtracted,
    and scaled by a constant factor.
    It represents a 2D dimension data (horizontal and vertical length)
    or a 2D position

    Being a tuple subclass, should be able to be used wherever a tuple is needed,
    but if that's not the case, call XY.tuple().
    """
    h: int
    v: int

    def __add__(self, other: Tuple[int, int]) -> Self:
        return XY(self[0] + other[0], self[1] + other[1])

    def __sub__(self, other: Tuple[int, int]) -> Self:
        return XY(self[0] - other[0], self[1] - other[1])

    def scale(self, factor: Union[int, float]) -> Self:
        return XY(int(self[0] * factor), int(self[1] * factor))

    def tuple(self) -> Tuple[int, int]:
        return tuple(self)

    def transpose(self) -> Self:
        return XY(self[1], self[0])


Box = Tuple[XY, XY]
Layout = Map[Map[int]]
JsonDict = Dict[str, Any]

# File locations

# Cards and Tokens/Emblems have different caches, since there are cards with the same name as tokens
# Notable example: Blood token and Flesh // Blood
CACHE_LOC = "cardcache/cardcache.p"
TOKEN_CACHE_LOC = "cardcache/tokencache.p"
BACK_CARD_SYMBOLS_LOC = "symbols"

TITLE_FONT = "fonts/title_font.ttf"
RULES_FONT = "fonts/rules_font.ttf"

# MTG constants: colors, basic lands, color names...

MTG_COLORS = str  # Literal["W", "U", "B", "R", "G"]

FRAME_COLORS = {
    "W": "#fcf4a3",
    "U": "#127db4",
    "B": "#692473",
    "R": "#e13c32",
    "G": "#0f7846",
    "C": "#919799",
    "M": "#d4af37",  # Multicolor / Gold
    "default": "#000000",
}

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

MANA_SYMBOLS: List[MTG_COLORS] = ["W", "U", "B", "R", "G"]
# Can be obtained programmatically, but that's more concise
HYBRID_SYMBOLS = ["W/U", "U/B", "B/R", "R/G", "G/W", "W/B", "U/R", "B/G", "R/W", "G/U"]
COLOR_NAMES = {"W": "white", "U": "blue", "B": "black", "R": "red", "G": "green"}
MTG_COLORLESS: str = "C"
MTG_MULTICOLOR: str = "M"

# Layout types
TOKEN = "token"
EMBLEM = "emblem"

LAYOUT_TYPES_DF = set([LayoutType.TDF, LayoutType.MDF])
LAYOUT_TYPES_TWO_PARTS = set([
    LayoutType.SPL,
    LayoutType.FUS,
    LayoutType.AFT,
    LayoutType.ADV,
    LayoutType.FLP
])

ACORN_PLAINTEXT = "{ACORN}"

# FONT_CODE_POINT includes the symbols used in the card text and mana cost.
# Those were added manually to the font file at the specified unicode point
FONT_CODE_POINT: Dict[str, str] = {}
for i in range(21):
    FONT_CODE_POINT[f"{{{i}}}"] = chr(0x200 + i)  # Generic mana cost (0 to 20)
for (i, c) in enumerate(MANA_SYMBOLS):
    FONT_CODE_POINT[f"{{{c}}}"] = chr(0x220 + i)  # Colored Mana
    FONT_CODE_POINT[f"{{2/{c}}}"] = chr(0x225 + i)  # Two-Hybrid Mana
    FONT_CODE_POINT[f"{{{c}/P}}"] = chr(0x22A + i)  # Phyrexian Mana
for (i, h) in enumerate(HYBRID_SYMBOLS):
    FONT_CODE_POINT[f"{{{h}}}"] = chr(0x230 + i)  # Hybrid Mana
    FONT_CODE_POINT[f"{{{h}/P}}"] = chr(0x240 + i)  # Hybrid Phyrexian Mana
FONT_CODE_POINT["{X}"] = chr(0x215)
FONT_CODE_POINT["{Y}"] = chr(0x216)
FONT_CODE_POINT["{Z}"] = chr(0x217)
FONT_CODE_POINT["{T}"] = chr(0x218)  # Tap
FONT_CODE_POINT["{Q}"] = chr(0x219)  # Untap
FONT_CODE_POINT["{S}"] = chr(0x21E)  # Snow Mana
FONT_CODE_POINT["{C}"] = chr(0x21F)  # Colorless Mana
FONT_CODE_POINT["{P}"] = chr(0x22F)  # Standard Phyrexian Mana
FONT_CODE_POINT["{E}"] = chr(0x23A)  # Energy Counter
FONT_CODE_POINT["{TK}"] = chr(0x23B) # Ticket Counter (from Unfinity)
FONT_CODE_POINT[f"{{{LayoutType.MDF.value}0}}"] = chr(0x21A)  # Sun
FONT_CODE_POINT[f"{{{LayoutType.MDF.value}1}}"] = chr(0x21B)  # Moon
FONT_CODE_POINT[f"{{{LayoutType.TDF.value}0}}"] = chr(0x21C)  # One triangle
FONT_CODE_POINT[f"{{{LayoutType.TDF.value}1}}"] = chr(0x21D)  # Two triangles
FONT_CODE_POINT[f"{{{LayoutType.FLP.value}0}}"] = chr(0x218)  # Tap
FONT_CODE_POINT[f"{{{LayoutType.FLP.value}1}}"] = chr(0x219)  # Untap
FONT_CODE_POINT[ACORN_PLAINTEXT] = chr(0x23C) # Acorn Symbol
FONT_CODE_POINT["{PAINTBRUSH}"] = chr(0x23F)  # Paintbrush Symbol

ATTRACTION_LINE = "\n".join([chr(0x261 + i) for i in range(6)]) # Numbers 1 to 6, enclosed in circles

TODO = """
Class, Sagas and Leveler frames?
Colored Mana symbols
Flavor Names for DFC, Adventures and possibly Flip?
Stop changing fonts
COMMENTS
"""

# Info relative to card pagination, mainly card and element sizes

# A MtG card is 2.5 in x 3.5 in
# Standard resolution is 300 dpi
# A4 paper is 8.25 in x 11.75 in
# Letter paper is 8.5 in x 11 in
# We can have a 3x3 of cards in both A4 and letter
# If we resize a MtG card to 1.875 in x 2.625 in (x0.75)
# We can have a 4x4 of cards in both A4 and letter

# PageFormat = str  # Literal["a4paper", "letter"]

# A4_FORMAT: PageFormat = "a4paper"
# LETTER_FORMAT: PageFormat = "letter"
# PAGE_FORMAT: List[PageFormat] = ["a4paper", "letter"]

WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
DPI = 300
A4_PAPER = XY(int(8.25 * DPI), int(11.75 * DPI))
LETTER_PAPER = XY(int(8.5 * DPI), int(11 * DPI))
CARD_H = int(2.5 * DPI)
CARD_V = int(3.5 * DPI)
CARD_SIZE = XY(CARD_H, CARD_V)
CARD_BOX: Box = (XY(0, 0), CARD_SIZE)
SMALL_CARD_SIZE = CARD_SIZE.scale(factor=0.75)
# Distance between cards when paginated, in pixels
CARD_DISTANCE = 20
# Desired distance in pixels between elements inside the card, e.g. between card border and title
BORDER = 15

TITLE_FONT_SIZE = 60
TYPE_FONT_SIZE = 50
TEXT_FONT_SIZE = 40
ATTRACTION_FONT_SIZE = 80
ATTRACTION_PIXELS_BETWEEN_LINES = 15
OTHER_FONT_SIZE = 25
SET_ICON_SIZE = 40
ILLUSTRATION_SIZE = 600
BORDER_THICKNESS = 5
BORDER_START_OFFSET = BORDER_THICKNESS - 1

# PTL box (stands for Power/Toughness/Loyalty) is always the same dimension
# And its lower right vertex is always the same distance from the card lower right vertex
PTL_BOX_DIM = XY(175, 70)
PTL_BOX_MARGIN = XY(25, 5)


class PageFormat(Enum):
    A4 = "a4paper"
    LETTER = "letter"

PAGE_SIZE: Dict[PageFormat, XY] = {
    PageFormat.A4: XY(h = int(8.25 * DPI), v = int(11.75 * DPI)),
    PageFormat.LETTER: XY(int(8.5 * DPI), int(11 * DPI)),
}

# Info about the card layout (how the lines are positioned to make the frame and various card sections)
# Every layout has a NAME_LAYOUT Map[Map[int]] with info about
# - the upper borders (BORDER) for different card sections (title, illustration, type line, rules box, other)
# - the size for different card sections
# - the vertical middle anchor for one-line text (title, type line)
# There also is the position of the set icon, and the position of the PTL box

# Helper functions for layout


def calcLayoutData(
    layoutType: str,
    bottom: int = CARD_V,
    left: int = 0,
    right: int = CARD_H,
    rulesBoxSize: int = 0,
):
    """
    Defines the layouts for all card types.
    Layouts start with TITLE at 0, then it has
    TITLE, ILLUSTRATION, TYPE_LINE, RULES_BOX and OTHER.
    The illustration size is deduced from the card vertical size
    (which depends on the layout type, for split it's the horizontal dim)
    All the borders are calculated using the sizes
    Almost all the sizes stay the same across layouts,
    except for rules box size and illustration.
    The text aligment is calculated using box size, only for PTL
    - Adventure frames are weird because they don't start at 0
    and don't have the OTHER line (also illustration is 0)
    - Flip frames have the illustration at the bottom,
    between the two halves of the card
    - Fuse cards have another section (the fuse box),
    which is specified at the end.
    - Attractions have a box for numbers on the right
    """
    layout = Map[Map[int]](
        BORDER=Map[int](
            TITLE=0,
            BOTTOM=bottom,
            LEFT=left,
            RIGHT=right
        ),
        SIZE=Map[int](
            TITLE=90,
            TYPE_LINE=50,
            RULES_BOX=rulesBoxSize,
            OTHER=40,
            PTL_BOX_H=PTL_BOX_DIM[0],
            PTL_BOX_V=PTL_BOX_DIM[1],
        ),
        FONT_MIDDLE=Map[int](),
    )

    if layoutType == LayoutType.ADV:
        layout.BORDER.TITLE = STD_LAYOUT.BORDER.RULES_BOX
        layout.SIZE.RULES_BOX = (
            STD_LAYOUT.SIZE.RULES_BOX - layout.SIZE.TITLE - layout.SIZE.TYPE_LINE
        )
        layout.BORDER.BOTTOM = layout.BORDER.BOTTOM - layout.SIZE.OTHER
        layout.SIZE.OTHER = 0

    if layoutType == LayoutType.FLP:
        layout.BORDER.TYPE_LINE = layout.BORDER.TITLE + layout.SIZE.TITLE
        layout.BORDER.RULES_BOX = layout.BORDER.TYPE_LINE + layout.SIZE.TYPE_LINE
        layout.BORDER.OTHER = layout.BORDER.RULES_BOX + layout.SIZE.RULES_BOX
        layout.BORDER.ILLUSTRATION = layout.BORDER.OTHER + layout.SIZE.OTHER

        layout.SIZE.ILLUSTRATION = layout.BORDER.BOTTOM - 2 * layout.BORDER.ILLUSTRATION

        layout.BORDER.PTL_BOX_BOTTOM = layout.BORDER.ILLUSTRATION - PTL_BOX_MARGIN[1]

    else:
        layout.BORDER.ILLUSTRATION = layout.BORDER.TITLE + layout.SIZE.TITLE
        layout.BORDER.OTHER = layout.BORDER.BOTTOM - layout.SIZE.OTHER
        layout.BORDER.RULES_BOX = layout.BORDER.OTHER - layout.SIZE.RULES_BOX
        layout.BORDER.TYPE_LINE = layout.BORDER.RULES_BOX - layout.SIZE.TYPE_LINE

        layout.SIZE.ILLUSTRATION = layout.BORDER.TYPE_LINE - layout.BORDER.ILLUSTRATION

        layout.BORDER.PTL_BOX_BOTTOM = layout.BORDER.BOTTOM - PTL_BOX_MARGIN[1]

    layout.BORDER.PTL_BOX_RIGHT = layout.BORDER.RIGHT - PTL_BOX_MARGIN[0]
    layout.BORDER.PTL_BOX_LEFT = layout.BORDER.PTL_BOX_RIGHT - layout.SIZE.PTL_BOX_H
    layout.BORDER.PTL_BOX_TOP = layout.BORDER.PTL_BOX_BOTTOM - layout.SIZE.PTL_BOX_V

    layout.SIZE.H = layout.BORDER.RIGHT - layout.BORDER.LEFT
    layout.SIZE.V = layout.BORDER.BOTTOM - layout.BORDER.TITLE

    layout.FONT_MIDDLE.PTL_H = layout.BORDER.PTL_BOX_LEFT + layout.SIZE.PTL_BOX_H // 2
    layout.FONT_MIDDLE.PTL_V = layout.BORDER.PTL_BOX_TOP + layout.SIZE.PTL_BOX_V // 2

    if layoutType == LayoutType.ATR:
        layout.SIZE.ATTRACTION_SECTION_H = 100
        layout.BORDER.ATTRACTION_SECTION_H = layout.BORDER.RIGHT - layout.SIZE.ATTRACTION_SECTION_H

    if layoutType == LayoutType.SPL:
        layout.SIZE.FUSE = 50
        layout.BORDER.FUSE = layout.BORDER.OTHER - layout.SIZE.FUSE
        layout.SIZE.RULES_BOX_FUSE = layout.SIZE.RULES_BOX - layout.SIZE.FUSE
        layout.FONT_MIDDLE.FUSE = layout.BORDER.FUSE + layout.SIZE.FUSE // 2

    return layout


def calcIconPosition(layout: Layout) -> XY:
    """
    Returns the set icon position, given the layout and the right border of the card
    """
    return XY(
        layout.BORDER.RIGHT - BORDER - SET_ICON_SIZE,
        layout.BORDER.TYPE_LINE + (layout.SIZE.TYPE_LINE - SET_ICON_SIZE) // 2,
    )


def calcIllustrationPosition(layout: Layout) -> XY:
    """
    Returns the illustration position for basic lands and emblems
    """
    return XY(
        (layout.BORDER.RIGHT - ILLUSTRATION_SIZE) // 2,
        layout.BORDER.ILLUSTRATION
        + (layout.SIZE.ILLUSTRATION - ILLUSTRATION_SIZE) // 2,
    )


def ptlTextPosition(box: Box) -> XY:
    return (box[0] + box[1]).scale(0.5)


# Standard layout (normal cards)
STD_LAYOUT = calcLayoutData(layoutType=LayoutType.STD, rulesBoxSize=500)
STD_SET_ICON_POSITION = calcIconPosition(layout=STD_LAYOUT)


# Split layout (for split, fuse, and right half of aftermath)
SPLIT_LAYOUT_LEFT = calcLayoutData(
    layoutType=LayoutType.SPL, bottom=CARD_H, left=0, right=CARD_V // 2, rulesBoxSize=360
)
SPLIT_LAYOUT_RIGHT = calcLayoutData(
    layoutType=LayoutType.SPL, bottom=CARD_H, left=CARD_V // 2, right=CARD_V, rulesBoxSize=360
)
SPLIT_SET_ICON_POSITION: List[XY] = [
    calcIconPosition(layout=SPLIT_LAYOUT_LEFT),
    calcIconPosition(layout=SPLIT_LAYOUT_RIGHT),
]


# Adventure layout (for the Adventure part of the card, the other one uses the standard layout)
ADVENTURE_LAYOUT = calcLayoutData(
    layoutType=LayoutType.ADV,
    bottom=CARD_V,
    left=0,
    right=CARD_H // 2,
)


# Aftermath layout (for the upper half of aftermath)
AFTERMATH_LAYOUT = calcLayoutData(
    layoutType=LayoutType.AFT,
    bottom=CARD_V // 2,
    rulesBoxSize=175,
)
AFTERMATH_SET_ICON_POSITION = calcIconPosition(layout=AFTERMATH_LAYOUT)


# Flip layout (Only one half is specified here, for the other just flip the card and redraw)
FLIP_LAYOUT = calcLayoutData(
    layoutType=LayoutType.FLP,
    rulesBoxSize=200,
)
FLIP_SET_ICON_POSITION = calcIconPosition(layout=FLIP_LAYOUT)


# Attraction cards layout (normal cards, but with attraction line)
ATTRACTION_LAYOUT = calcLayoutData(layoutType=LayoutType.ATR, rulesBoxSize=500)


# Textless land layout
LAND_LAYOUT = calcLayoutData(layoutType=LayoutType.LND, rulesBoxSize=0)
LAND_SET_ICON_POSITION = calcIconPosition(layout=LAND_LAYOUT)


# Vanilla token layout (has one line for color indicator)
TOKEN_LAYOUT = calcLayoutData(layoutType=TOKEN, rulesBoxSize=100)
TOKEN_SET_ICON_POSITION = calcIconPosition(layout=TOKEN_LAYOUT)


# Emblem and normal token layout (has more rules space)
EMBLEM_LAYOUT = calcLayoutData(layoutType=EMBLEM, rulesBoxSize=250)
EMBLEM_SET_ICON_POSITION = calcIconPosition(layout=EMBLEM_LAYOUT)

TOKEN_ARC_WIDTH = 600
LAND_MANA_SYMBOL_POSITION = calcIllustrationPosition(layout=LAND_LAYOUT)
EMBLEM_SYMBOL_POSITION = calcIllustrationPosition(layout=EMBLEM_LAYOUT)

LAYOUTS: DefaultDict[str, List[Layout]] = defaultdict(
    lambda: [STD_LAYOUT],
    {
        LayoutType.SPL: [SPLIT_LAYOUT_LEFT, SPLIT_LAYOUT_RIGHT],
        LayoutType.FUS: [SPLIT_LAYOUT_LEFT, SPLIT_LAYOUT_RIGHT],
        LayoutType.AFT: [AFTERMATH_LAYOUT, SPLIT_LAYOUT_RIGHT],
        LayoutType.FLP: [FLIP_LAYOUT, FLIP_LAYOUT],
        LayoutType.ADV: [STD_LAYOUT, ADVENTURE_LAYOUT],
        LayoutType.ATR: [ATTRACTION_LAYOUT],
        LayoutType.LND: [LAND_LAYOUT],
        TOKEN: [TOKEN_LAYOUT],
        EMBLEM: [EMBLEM_LAYOUT],
    },
)

SET_ICON_POSITIONS: DefaultDict[str, List[XY]] = defaultdict(
    lambda: [STD_SET_ICON_POSITION],
    {
        LayoutType.SPL: SPLIT_SET_ICON_POSITION,
        LayoutType.FUS: SPLIT_SET_ICON_POSITION,
        LayoutType.AFT: [AFTERMATH_SET_ICON_POSITION, SPLIT_SET_ICON_POSITION[1]],
        LayoutType.FLP: [FLIP_SET_ICON_POSITION, FLIP_SET_ICON_POSITION],
        LayoutType.ADV: [STD_SET_ICON_POSITION, STD_SET_ICON_POSITION],
        LayoutType.LND: [LAND_SET_ICON_POSITION],
        TOKEN: [TOKEN_SET_ICON_POSITION],
        EMBLEM: [EMBLEM_SET_ICON_POSITION],
    },
)

def calc_layout_data(
    template: LayoutData,
    layout_type: LayoutType,
    part: int = 0
):
    layout_data = deepcopy(template)

    layout_data.LAYOUT_TYPE = layout_type
    
    # Aftermath second part is just a split card second part
    if (layout_type == LayoutType.AFT and part == 1):
        layout_type = LayoutType.SPL
    
    if layout_type == LayoutType.SPL or layout_type == LayoutType.FUS:
        layout_data.ROTATION = Rot.ROT_90
        layout_data.BORDER.CARD.BOTTOM = CARD_H
        layout_data.SIZE.RULES.VERT = 280

        if (part == 0):
            layout_data.BORDER.CARD.LEFT = 0
            layout_data.BORDER.CARD.RIGHT = CARD_V // 2
        else:
            layout_data.BORDER.CARD.LEFT = CARD_V // 2
            layout_data.BORDER.CARD.RIGHT = CARD_V

    elif layout_type == LayoutType.AFT:
        layout_data.BORDER.CARD.BOTTOM = CARD_V // 2
        layout_data.SIZE.RULES.VERT = 175

    elif layout_type == LayoutType.ADV:
        if (part == 1):
            layout_data.BORDER.CARD.RIGHT = CARD_H // 2
            layout_data.BORDER.CARD.TOP = TEMPLATE_LAYOUT_DATA.BORDER.RULES.TOP
            layout_data.BORDER.CARD.BOTTOM = TEMPLATE_LAYOUT_DATA.BORDER.RULES.BOTTOM
            layout_data.SIZE.RULES.VERT = (
                TEMPLATE_LAYOUT_DATA.SIZE.RULES.VERT
                - template.SIZE.TITLE
                - template.SIZE.TYPE
            )
            layout_data.SIZE.CREDITS = 0

    elif layout_type == LayoutType.FLP:
        layout_data.SIZE.RULES.VERT = 200
        if (part == 1):
            layout_data.ROTATION = Rot.ROT_180

    elif layout_type == LayoutType.LND:
        layout_data.SIZE.RULES.VERT = 0

    elif layout_type == LayoutType.VTK:
        layout_data.SIZE.RULES.VERT = 90

    elif layout_type == LayoutType.TOK or layout_type == LayoutType.EMB:
        layout_data.SIZE.RULES.VERT = 250

    else:
        layout_data.SIZE.RULES.VERT = 500

    # Default borders for rules box
    layout_data.BORDER.RULES.LEFT = layout_data.BORDER.CARD.LEFT
    layout_data.BORDER.RULES.RIGHT = layout_data.BORDER.CARD.RIGHT

    # Calculating sizes
    layout_data.SIZE.CARD.HORIZ = layout_data.BORDER.CARD.RIGHT - layout_data.BORDER.CARD.LEFT
    layout_data.SIZE.CARD.VERT = layout_data.BORDER.CARD.BOTTOM - layout_data.BORDER.CARD.TOP
    layout_data.SIZE.RULES.HORIZ = layout_data.BORDER.RULES.RIGHT - layout_data.BORDER.RULES.LEFT

    # Calculating PTL box borders
    layout_data.BORDER.PTL_BOX.BOTTOM = (
        layout_data.BORDER.CREDITS + layout_data.SIZE.CREDITS
        - PTL_BOX_MARGIN[1]
    )
    layout_data.BORDER.PTL_BOX.TOP = layout_data.BORDER.PTL_BOX.BOTTOM - layout_data.SIZE.PTL_BOX.VERT
    layout_data.BORDER.PTL_BOX.RIGHT = layout_data.BORDER.RULES.RIGHT - PTL_BOX_MARGIN[0]
    layout_data.BORDER.PTL_BOX.LEFT = layout_data.BORDER.PTL_BOX.RIGHT - layout_data.SIZE.PTL_BOX.HORIZ
    # Calculating PTL font position
    layout_data.FONT_MIDDLE.PTL_H = layout_data.BORDER.PTL_BOX.LEFT + layout_data.SIZE.PTL_BOX.HORIZ // 2
    layout_data.FONT_MIDDLE.PTL_V = layout_data.BORDER.PTL_BOX.TOP + layout_data.SIZE.PTL_BOX.VERT // 2

    other_sizes: int = (
        layout_data.SIZE.TITLE
        + layout_data.SIZE.TYPE
        + layout_data.SIZE.RULES.VERT
        + layout_data.SIZE.CREDITS
    )

    if (layout_type == LayoutType.FLP):
        # Image size (which is calculated in a different way, since we have two of everything else)
        layout_data.SIZE.IMAGE = layout_data.BORDER.CARD.BOTTOM - 2 * other_sizes
        # All borders
        layout_data.BORDER.TYPE = layout_data.BORDER.CARD.TOP + layout_data.SIZE.TITLE
        layout_data.BORDER.RULES.TOP = layout_data.BORDER.TYPE + layout_data.SIZE.TYPE
        layout_data.BORDER.RULES.BOTTOM = layout_data.BORDER.RULES.TOP + layout_data.SIZE.RULES.VERT
        layout_data.BORDER.CREDITS = layout_data.BORDER.RULES.BOTTOM
        layout_data.BORDER.IMAGE = layout_data.BORDER.CREDITS + layout_data.SIZE.CREDITS
    else:
        # Image size
        layout_data.SIZE.IMAGE = layout_data.BORDER.CARD.BOTTOM - other_sizes
        # All borders
        layout_data.BORDER.IMAGE = layout_data.BORDER.CARD.TOP + layout_data.SIZE.TITLE
        layout_data.BORDER.TYPE = layout_data.BORDER.IMAGE + layout_data.SIZE.IMAGE
        layout_data.BORDER.RULES.TOP = layout_data.BORDER.TYPE + layout_data.SIZE.TYPE
        layout_data.BORDER.RULES.BOTTOM = layout_data.BORDER.RULES.TOP + layout_data.SIZE.RULES.VERT
        layout_data.BORDER.CREDITS = layout_data.BORDER.RULES.BOTTOM

    # Layouts needing adjustments to rules box or non-standard sections
    # Main adventure part has the other part on the left
    if (layout_type == LayoutType.ADV and part == 0):
        layout_data.SIZE.RULES.HORIZ //= 2
        layout_data.BORDER.RULES.LEFT = layout_data.BORDER.RULES.RIGHT - layout_data.SIZE.RULES.HORIZ
    # Fuse layouts have the Fuse section under the rules box
    elif (layout_type == LayoutType.FUS):
        layout_data.SIZE.FUSE = SizeData(
            HORIZ = CARD_V,
            VERT = 50,
        )
        layout_data.BORDER.RULES.BOTTOM -= layout_data.SIZE.FUSE.VERT
        layout_data.SIZE.RULES.VERT -= layout_data.SIZE.FUSE.VERT
        layout_data.BORDER.FUSE = BorderData(
            TOP = layout_data.BORDER.RULES.BOTTOM,
            BOTTOM = layout_data.BORDER.RULES.BOTTOM + layout_data.SIZE.FUSE.VERT,
            LEFT = 0,
            RIGHT = CARD_V
        )
        layout_data.FONT_MIDDLE.FUSE_V = layout_data.BORDER.FUSE.TOP +  layout_data.SIZE.FUSE.VERT // 2
    # Attractions have the number box on the right
    elif (layout_type == LayoutType.ATR):
        layout_data.SIZE.ATTRACTION = SizeData(
            HORIZ = 100,
            VERT = layout_data.SIZE.RULES.HORIZ
        )
        layout_data.BORDER.RULES.RIGHT -= layout_data.SIZE.ATTRACTION.HORIZ
        layout_data.SIZE.RULES.HORIZ -= layout_data.SIZE.ATTRACTION.HORIZ
        layout_data.BORDER.ATTRACTION = BorderData(
            TOP = layout_data.BORDER.RULES.TOP,
            BOTTOM = layout_data.BORDER.RULES.BOTTOM,
            LEFT = layout_data.BORDER.RULES.RIGHT,
            RIGHT = layout_data.BORDER.CARD.RIGHT,
        )
        layout_data.FONT_MIDDLE.ATTRACTION_H = layout_data.BORDER.ATTRACTION.LEFT +  layout_data.SIZE.ATTRACTION.HORIZ // 2
    
    return layout_data


TEMPLATE_LAYOUT_DATA: LayoutData = calc_layout_data(
    template=LayoutData(
        # -1 (or not present) means that the value is calculated
        ROTATION = Rot.ROT_0,
        BORDER = Border(
            # Most borders, except for card borders,
            # are calculated based on sizes
            CARD = BorderData(
                LEFT = 0,
                RIGHT = CARD_H,
                TOP = 0,
                BOTTOM = CARD_V
            ),
        ),
        SIZE = Size(
            # The only sizes that are calculated are
            # Card sizes (based on borders)
            # Rules horizontal size (usually based on card size)
            # and image size (based on all the other sizes)
            CARD = SizeData(),
            TITLE = 90,
            IMAGE = -1,
            TYPE = 50,
            RULES = SizeData(),
            PTL_BOX = SizeData(
                HORIZ = 175,
                VERT = 70,
            ),
            CREDITS = 40,
        ),
        FONT_MIDDLE = FontMiddle()
    ),
    layout_type=LayoutType.STD
)

LAYOUT_DATA: Dict[LayoutType, List[LayoutData]] = {}

for layout_type in LayoutType:
    if layout_type in LAYOUT_TYPES_TWO_PARTS:
        LAYOUT_DATA[layout_type] = [calc_layout_data(
            template=TEMPLATE_LAYOUT_DATA,
            layout_type=layout_type,
            part=i
        ) for i in range(2)]
    else:
        LAYOUT_DATA[layout_type] = [calc_layout_data(
            template=TEMPLATE_LAYOUT_DATA,
            layout_type=layout_type
        )]


def calc_icon_position(layout_type: LayoutType, part: int = 0) -> XY:
    """
    Returns the set icon top left position,
    given the layout type and the layout part
    """
    layout_data = LAYOUT_DATA[layout_type][part]
    return XY(
        h = layout_data.BORDER.CARD.RIGHT - BORDER - SET_ICON_SIZE,
        v = layout_data.BORDER.TYPE + (layout_data.SIZE.TYPE - SET_ICON_SIZE) // 2,
    )

ICON_POSITIONS: Dict[LayoutType, List[XY]] = {}

for layout_type in LayoutType:
    if layout_type in LAYOUT_TYPES_TWO_PARTS:
        ICON_POSITIONS[layout_type] = [calc_icon_position(
            layout_type=layout_type,
            part=i
        ) for i in range(2)]
    else:
        ICON_POSITIONS[layout_type] = [calc_icon_position(
            layout_type=layout_type
        )]
