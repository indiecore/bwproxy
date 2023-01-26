from copy import deepcopy
from PIL import Image
from typing import (
    Any,
    Dict,
    Tuple,
    List,
    Union,
    NamedTuple,
    Iterable,
)
from typing_extensions import Literal, Self
from enum import Enum

VERSION: str = "v2.2"
# 0x23F is the paintbrush symbol
CREDITS: str = chr(0x23F) + " https://a11ce.com/bwproxy"

# Helper classes and functions

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

Rot = Literal[2, 3, 4]

class LayoutType(Enum):
    STD = "standard"
    SPL = "split"
    FUS = "fuse"
    AFT = "aftermath"
    ADV = "adventure"
    FLP = "flip"
    LND = "land"
    VTK = "vanilla_token"
    VCR = "vanilla_creature"
    TOK = "token"
    EMB = "emblem"
    TDF = "transform"
    MDF = "modal_dfc"
    ATR = "attraction"

    @classmethod
    def values(cls) -> Iterable[str]:
        for x in cls:
            yield x.value

# This is almost useless (we could use a dictionary),
# but has the advantage of syntax higlighting and autocompletion

class _BorderData():
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

    def __repr__(self):
        return f"T: {self.TOP}, B: {self.BOTTOM}, L: {self.LEFT}, R: {self.RIGHT}"

class _SizeData():
    def __init__(
        self,
        HORIZ: int = -1,
        VERT: int = -1,
    ):
        self.HORIZ: int = HORIZ
        self.VERT: int = VERT

    def __repr__(self) -> str:
        return f"H: {self.HORIZ}, V: {self.VERT}"

class _Border():
    def __init__(
        self,
        CARD: _BorderData,
    ):
        self.CARD: _BorderData = CARD
        self.IMAGE: int = -1
        self.TYPE: int = -1
        self.RULES: _BorderData = _BorderData()
        self.PTL_BOX: _BorderData = _BorderData()
        self.CREDITS: int = -1
        self.FUSE: _BorderData
        self.ATTRACTION: _BorderData

class _Size():
    def __init__(
        self,
        CARD: _SizeData,
        TITLE: int,
        IMAGE: int,
        TYPE: int,
        RULES: _SizeData,
        PTL_BOX: _SizeData,
        CREDITS: int,
    ):
        self.CARD: _SizeData = CARD
        self.TITLE: int = TITLE
        self.IMAGE: int = IMAGE
        self.TYPE: int = TYPE
        self.RULES: _SizeData = RULES
        self.PTL_BOX: _SizeData = PTL_BOX
        self.CREDITS: int = CREDITS
        self.FUSE: _SizeData
        self.ATTRACTION: _SizeData

class _FontMiddle():
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
        ROTATION: Union[None, Tuple[Rot, Rot]],
        BORDER: _Border,
        SIZE: _Size,
        FONT_MIDDLE: _FontMiddle,
    ):
        self.LAYOUT_TYPE: LayoutType
        self.ROTATION: Union[None, Tuple[Rot, Rot]] = ROTATION
        self.BORDER: _Border = BORDER
        self.SIZE: _Size = SIZE
        self.FONT_MIDDLE: _FontMiddle = FONT_MIDDLE
        self.ICON_CENTER: XY
        self.IMAGE_POSITION: XY

JsonDict = Dict[str, Any]
RGB = Union[Tuple[int, int, int], Tuple[int, int, int, int]]

# File locations

# Cards and Tokens/Emblems have different caches, since there are cards with the same name as tokens
# Notable example: Blood token and Flesh // Blood
CACHE_LOC = "cardcache/cardcache.p"
TOKEN_CACHE_LOC = "cardcache/tokencache.p"
BACK_CARD_SYMBOLS_LOC = "symbols"

TITLE_FONT = "fonts/title_font.ttf"
RULES_FONT = "fonts/rules_font.ttf"

# MTG constants: colors, basic lands, color names...

class ManaColors(Enum):
    White = "W"
    Blue = "U"
    Black = "B"
    Red = "R"
    Green = "G"
    
    @classmethod
    def values(cls) -> Iterable[str]:
        for x in cls:
            yield x.value

class FrameColors(Enum):
    Multicolor = "M"
    Colorless = "C"

    @classmethod
    def values(cls) -> Iterable[str]:
        for x in cls:
            yield x.value

FRAME_COLORS = {
    ManaColors.White: "#fcf4a3",
    ManaColors.Blue: "#127db4",
    ManaColors.Black: "#692473",
    ManaColors.Red: "#e13c32",
    ManaColors.Green: "#0f7846",
    FrameColors.Colorless: "#919799",
    FrameColors.Multicolor: "#d4af37",  # Multicolor / Gold
}

DEFAULT_FRAME_COLOR = "#000000"

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

# FONT_CODE_POINT includes the symbols used in the card text and mana cost.
# Those were added manually to the font file at the specified unicode point
FONT_CODE_POINT: Dict[str, str] = {}
# This is just to be able to collapse everything
if True:
    for _i in range(21):
        FONT_CODE_POINT[f"{{{_i}}}"] = chr(0x200 + _i)  # Generic mana cost (0 to 20)
    for (_i, _c) in enumerate(ManaColors):
        _cVal = _c.value
        FONT_CODE_POINT[f"{{{_cVal}}}"] = chr(0x220 + _i)  # Colored Mana
        FONT_CODE_POINT[f"{{2/{_cVal}}}"] = chr(0x225 + _i)  # Two-Hybrid Mana
        FONT_CODE_POINT[f"{{{_cVal}/P}}"] = chr(0x22A + _i)  # Phyrexian Mana
    for (_i, _h) in enumerate(MANA_HYBRID):
        FONT_CODE_POINT[f"{{{_h}}}"] = chr(0x230 + _i)  # Hybrid Mana
        FONT_CODE_POINT[f"{{{_h}/P}}"] = chr(0x240 + _i)  # Hybrid Phyrexian Mana
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

ATTRACTION_COLUMN = "\n".join([chr(0x261 + i) for i in range(6)]) # Numbers 1 to 6, enclosed in circles

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

class PageFormat(Enum):
    A4 = "a4paper"
    LETTER = "letter"

    @classmethod
    def values(cls) -> Iterable[str]:
        for x in cls:
            yield x.value

WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
DPI = 300
CARD_H = int(2.5 * DPI)
CARD_V = int(3.5 * DPI)
CARD_SIZE = XY(CARD_H, CARD_V)
SMALL_CARD_SIZE = CARD_SIZE.scale(factor=0.75)
# Distance between cards when paginated, in pixels
CARD_DISTANCE = 20

PAGE_SIZE: Dict[PageFormat, XY] = {
    PageFormat.A4: XY(h = int(8.25 * DPI), v = int(11.75 * DPI)),
    PageFormat.LETTER: XY(int(8.5 * DPI), int(11 * DPI)),
}

class DrawSize():
    def __init__(
        self
    ):
        self.TITLE: int = 60
        self.TYPE = 50
        self.TEXT = 40
        self.ATTRACTION = 80
        self.ATTRACTION_INTERLINE = 15
        self.CREDITS = 30
        self.ICON = 40
        # Image size for emblem and land 
        self.IMAGE = 600
        # Border thickness
        self.BORDER = 5
        # Distance between elements of a card
        self.SEPARATOR = 15

DRAW_SIZE = DrawSize()

# Since the borders in the layout are offset when asking for the bottom line,
# We need these values in order to properly center text and align borders
BORDER_START_OFFSET = DRAW_SIZE.BORDER - 1
BORDER_CENTER_OFFSET = DRAW_SIZE.BORDER // 2

def calcLayoutData(
    template: LayoutData,
    layoutType: LayoutType,
    part: int = 0
) -> LayoutData:
    """Calculates the card layout (how the lines are positioned
    to make the frame and various card sections)

    Every calculated layout has info about

    - The layout type;

    - The necessary rotation to view the card (or card part) correcly;
    
    - The borders for the different card sections
    (whole card, image, type line, rules box, credits line).
    Some sections only have the top border, while others have all the four sides;

    - The corresponding section sizes;

    - The vertical middle anchor for one-line text (type line);

    - The card icon center position;

    - The image top left position (for emblems and lands).
    
    While some of these values are hardcoded, others are calculated
    such that the values are internally consistent."""
    layoutData = deepcopy(template)

    layoutData.LAYOUT_TYPE = layoutType
    
    # Aftermath second part is just a split card second part
    if (layoutType == LayoutType.AFT and part == 1):
        layoutType = LayoutType.SPL
    
    if layoutType == LayoutType.SPL or layoutType == LayoutType.FUS:
        layoutData.ROTATION = (Image.ROTATE_90, Image.ROTATE_270)
        layoutData.BORDER.CARD.BOTTOM = CARD_H
        layoutData.SIZE.RULES.VERT = 280

        if (part == 0):
            layoutData.BORDER.CARD.LEFT = 0
            layoutData.BORDER.CARD.RIGHT = CARD_V // 2
        else:
            layoutData.BORDER.CARD.LEFT = CARD_V // 2
            layoutData.BORDER.CARD.RIGHT = CARD_V

    elif layoutType == LayoutType.AFT:
        layoutData.BORDER.CARD.BOTTOM = CARD_V // 2
        layoutData.SIZE.RULES.VERT = 175

    elif layoutType == LayoutType.ADV:
        if (part == 1):
            layoutData.BORDER.CARD.RIGHT = CARD_H // 2
            layoutData.BORDER.CARD.TOP = TEMPLATE_LAYOUT_DATA.BORDER.RULES.TOP - BORDER_START_OFFSET
            layoutData.BORDER.CARD.BOTTOM = TEMPLATE_LAYOUT_DATA.BORDER.RULES.BOTTOM
            layoutData.SIZE.TITLE += BORDER_START_OFFSET
            layoutData.SIZE.RULES.VERT = (
                TEMPLATE_LAYOUT_DATA.SIZE.RULES.VERT
                - template.SIZE.TITLE
                - template.SIZE.TYPE
            )
            layoutData.SIZE.CREDITS = 0

    elif layoutType == LayoutType.FLP:
        layoutData.SIZE.RULES.VERT = 200
        if (part == 1):
            layoutData.ROTATION = (Image.ROTATE_180, Image.ROTATE_180)

    elif layoutType in [LayoutType.LND, LayoutType.VCR, LayoutType.VTK]:
        layoutData.SIZE.RULES.VERT = 0

    elif layoutType == LayoutType.TOK or layoutType == LayoutType.EMB:
        layoutData.SIZE.RULES.VERT = 250

    else:
        layoutData.SIZE.RULES.VERT = 500

    # Default borders for rules box
    layoutData.BORDER.RULES.LEFT = layoutData.BORDER.CARD.LEFT
    layoutData.BORDER.RULES.RIGHT = layoutData.BORDER.CARD.RIGHT

    # Calculating sizes
    layoutData.SIZE.CARD.HORIZ = layoutData.BORDER.CARD.RIGHT - layoutData.BORDER.CARD.LEFT
    layoutData.SIZE.CARD.VERT = layoutData.BORDER.CARD.BOTTOM - layoutData.BORDER.CARD.TOP
    layoutData.SIZE.RULES.HORIZ = layoutData.BORDER.RULES.RIGHT - layoutData.BORDER.RULES.LEFT

    other_sizes: int = (
        layoutData.SIZE.TITLE
        + layoutData.SIZE.TYPE
        + layoutData.SIZE.RULES.VERT
        + layoutData.SIZE.CREDITS
    )

    if (layoutType == LayoutType.FLP):
        # Image size (which is calculated in a different way, since we have two of everything else)
        layoutData.SIZE.IMAGE = layoutData.SIZE.CARD.VERT - 2 * other_sizes
        # All borders
        layoutData.BORDER.TYPE = layoutData.BORDER.CARD.TOP + layoutData.SIZE.TITLE
        layoutData.BORDER.RULES.TOP = layoutData.BORDER.TYPE + layoutData.SIZE.TYPE
        layoutData.BORDER.RULES.BOTTOM = layoutData.BORDER.RULES.TOP + layoutData.SIZE.RULES.VERT
        layoutData.BORDER.CREDITS = layoutData.BORDER.RULES.BOTTOM
        layoutData.BORDER.IMAGE = layoutData.BORDER.CREDITS + layoutData.SIZE.CREDITS
    else:
        # Image size
        layoutData.SIZE.IMAGE = layoutData.SIZE.CARD.VERT - other_sizes
        # All borders
        layoutData.BORDER.IMAGE = layoutData.BORDER.CARD.TOP + layoutData.SIZE.TITLE
        layoutData.BORDER.TYPE = layoutData.BORDER.IMAGE + layoutData.SIZE.IMAGE
        layoutData.BORDER.RULES.TOP = layoutData.BORDER.TYPE + layoutData.SIZE.TYPE
        layoutData.BORDER.RULES.BOTTOM = layoutData.BORDER.RULES.TOP + layoutData.SIZE.RULES.VERT
        layoutData.BORDER.CREDITS = layoutData.BORDER.RULES.BOTTOM

    
    # Calculating PTL box borders
    layoutData.BORDER.PTL_BOX.BOTTOM = (
        # We are not using BORDER.CARD.BOTTOM because it does not work
        # for flip cards (for that it would be BORDER.IMAGE)
        layoutData.BORDER.CREDITS + layoutData.SIZE.CREDITS
    )
    layoutData.BORDER.PTL_BOX.TOP = layoutData.BORDER.PTL_BOX.BOTTOM - layoutData.SIZE.PTL_BOX.VERT
    layoutData.BORDER.PTL_BOX.RIGHT = layoutData.BORDER.RULES.RIGHT - 25 # Box is 25 pixels left
    layoutData.BORDER.PTL_BOX.LEFT = layoutData.BORDER.PTL_BOX.RIGHT - layoutData.SIZE.PTL_BOX.HORIZ
    # Calculating PTL font position
    layoutData.FONT_MIDDLE.PTL_H = layoutData.BORDER.PTL_BOX.LEFT + layoutData.SIZE.PTL_BOX.HORIZ // 2
    layoutData.FONT_MIDDLE.PTL_V = layoutData.BORDER.PTL_BOX.TOP + layoutData.SIZE.PTL_BOX.VERT // 2 + BORDER_CENTER_OFFSET

    # Layouts needing adjustments to rules box or non-standard sections
    # Main adventure part has the other part on the left
    if (layoutType == LayoutType.ADV and part == 0):
        layoutData.SIZE.RULES.HORIZ //= 2
        layoutData.BORDER.RULES.LEFT = layoutData.BORDER.RULES.RIGHT - layoutData.SIZE.RULES.HORIZ
    # Fuse layouts have the Fuse section under the rules box
    elif (layoutType == LayoutType.FUS):
        layoutData.SIZE.FUSE = _SizeData(
            HORIZ = CARD_V,
            VERT = 50,
        )
        layoutData.BORDER.RULES.BOTTOM -= layoutData.SIZE.FUSE.VERT
        layoutData.SIZE.RULES.VERT -= layoutData.SIZE.FUSE.VERT
        layoutData.BORDER.FUSE = _BorderData(
            TOP = layoutData.BORDER.RULES.BOTTOM,
            BOTTOM = layoutData.BORDER.RULES.BOTTOM + layoutData.SIZE.FUSE.VERT,
            LEFT = 0,
            RIGHT = CARD_V
        )
        layoutData.FONT_MIDDLE.FUSE_V = layoutData.BORDER.FUSE.TOP +  layoutData.SIZE.FUSE.VERT // 2
    # Attractions have the number box on the right
    elif (layoutType == LayoutType.ATR):
        layoutData.SIZE.ATTRACTION = _SizeData(
            HORIZ = 100,
            VERT = layoutData.SIZE.RULES.HORIZ
        )
        layoutData.BORDER.RULES.RIGHT -= layoutData.SIZE.ATTRACTION.HORIZ
        layoutData.SIZE.RULES.HORIZ -= layoutData.SIZE.ATTRACTION.HORIZ
        layoutData.BORDER.ATTRACTION = _BorderData(
            TOP = layoutData.BORDER.RULES.TOP - BORDER_START_OFFSET,
            BOTTOM = layoutData.BORDER.RULES.BOTTOM,
            LEFT = layoutData.BORDER.RULES.RIGHT,
            RIGHT = layoutData.BORDER.CARD.RIGHT,
        )
        layoutData.FONT_MIDDLE.ATTRACTION_H = layoutData.BORDER.ATTRACTION.LEFT +  layoutData.SIZE.ATTRACTION.HORIZ // 2

    layoutData.ICON_CENTER = XY(
        h = layoutData.BORDER.CARD.RIGHT - DRAW_SIZE.SEPARATOR - DRAW_SIZE.ICON // 2,
        v = layoutData.BORDER.TYPE + layoutData.SIZE.TYPE // 2,
    )

    if layoutType in [LayoutType.LND, LayoutType.EMB]:
        layoutData.IMAGE_POSITION = XY(
            (layoutData.BORDER.CARD.RIGHT - DRAW_SIZE.IMAGE) // 2,
            layoutData.BORDER.IMAGE + (layoutData.SIZE.IMAGE - DRAW_SIZE.IMAGE) // 2,
        )
    
    return layoutData


TEMPLATE_LAYOUT_DATA: LayoutData = calcLayoutData(
    template=LayoutData(
        # -1 (or not present) means that the value is calculated
        ROTATION = None,
        BORDER = _Border(
            # Most borders, except for card borders,
            # are calculated based on sizes
            CARD = _BorderData(
                LEFT = 0,
                RIGHT = CARD_H,
                TOP = 0,
                BOTTOM = CARD_V
            ),
        ),
        SIZE = _Size(
            # The only sizes that are calculated are
            # Card sizes (based on borders)
            # Rules horizontal size (usually based on card size)
            # and image size (based on all the other sizes)
            CARD = _SizeData(),
            TITLE = 90,
            IMAGE = -1,
            TYPE = 55,
            RULES = _SizeData(),
            PTL_BOX = _SizeData(
                HORIZ = 160,
                VERT = 60,
            ),
            CREDITS = 55,
        ),
        FONT_MIDDLE = _FontMiddle()
    ),
    layoutType=LayoutType.STD
)

LAYOUT_DATA: Dict[LayoutType, List[LayoutData]] = {}

for _layoutType in LayoutType:
    if _layoutType in [*LAYOUT_TYPES_TWO_PARTS, *LAYOUT_TYPES_DF]:
        LAYOUT_DATA[_layoutType] = [calcLayoutData(
            template=TEMPLATE_LAYOUT_DATA,
            layoutType=_layoutType,
            part=i
        ) for i in range(2)]
    else:
        LAYOUT_DATA[_layoutType] = [calcLayoutData(
            template=TEMPLATE_LAYOUT_DATA,
            layoutType=_layoutType
        )]

TOKEN_ARC_WIDTH: int = 600