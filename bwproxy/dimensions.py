from copy import deepcopy
from PIL import Image
from typing import (
    Dict,
    List,
    Tuple
)

from .classes import XY, LayoutType, LayoutData, PageFormat
from .classes import (
    Size,
    SizeData,
    Border,
    BorderData,
    FontMiddle
)
from .other_constants import LAYOUT_TYPES_DF, LAYOUT_TYPES_TWO_PARTS

DPI = 300
CARD_SIZE = XY(int(2.5 * DPI), int(3.5 * DPI))
CARD_SIZE_PLAYTEST = XY(int(2 * DPI), int(3.5 * DPI))
SMALL_CARD_RESIZE_FACTOR = 0.75
# SMALL_CARD_SIZE = CARD_SIZE.scale(factor=0.75)
# Distance between cards when paginated, in pixels
CARD_DISTANCE = 40
CARD_DISTANCE_SMALL = 3

PAGE_SIZE: Dict[PageFormat, XY] = {
    PageFormat.A4: XY(
        h = int(8.25 * DPI),
        v = int(11.75 * DPI)
    ),
    PageFormat.LETTER: XY(
        h = int(8.5 * DPI),
        v = int(11 * DPI)
    ),
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
        self.CREDITS_PLAYTEST = 23
        self.ICON = 40
        # Image size for emblem and land 
        self.IMAGE = 600
        # Border thickness
        self.BORDER = 5
        # Distance between elements of a card
        self.SEPARATOR = 15

DRAW_SIZE = DrawSize()
TOKEN_ARC_WIDTH: int = 600

# Since the borders in the layout are offset when asking for the bottom line,
# We need these values in order to properly center text and align borders
BORDER_START_OFFSET = DRAW_SIZE.BORDER - 1
BORDER_CENTER_OFFSET = DRAW_SIZE.BORDER // 2

def calcLayoutData(
    template: LayoutData,
    cardSize: XY,
    layoutType: LayoutType,
    part: int = 0
) -> LayoutData:
    """Calculates the card layout (how the lines are positioned
    to make the frame and various card sections)

    Every calculated layout has info about

    - The layout type;

    - The necessary rotation to view the card (or card part) correctly;
    
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

    # Setting BORDER.CARD because it depends on card size
    layoutData.BORDER.CARD.BOTTOM = cardSize.v
    layoutData.BORDER.CARD.RIGHT  = cardSize.h
    layoutData.CARD_SIZE = cardSize
    
    # Aftermath second part is just a split card second part
    if (layoutType == LayoutType.AFT and part == 1):
        layoutType = LayoutType.SPL
    
    if layoutType == LayoutType.SPL or layoutType == LayoutType.FUS:
        layoutData.ROTATION = (Image.ROTATE_90, Image.ROTATE_270)
        layoutData.BORDER.CARD.BOTTOM = cardSize.h
        layoutData.SIZE.RULES.VERT = 280

        if (part == 0):
            layoutData.BORDER.CARD.LEFT = 0
            layoutData.BORDER.CARD.RIGHT = cardSize.v // 2
        else:
            layoutData.BORDER.CARD.LEFT = cardSize.v // 2
            layoutData.BORDER.CARD.RIGHT = cardSize.v

    elif layoutType == LayoutType.AFT:
        layoutData.BORDER.CARD.BOTTOM = cardSize.v // 2
        layoutData.SIZE.RULES.VERT = 175

    elif layoutType == LayoutType.ADV:
        if (part == 1):
            layoutData.BORDER.CARD.RIGHT = cardSize.h // 2
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
        layoutData.SIZE.RULES.VERT = 303

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

    
    # Calculating bottom box borders
    layoutData.BORDER.BOTTOM_BOX.BOTTOM = (
        # We are not using BORDER.CARD.BOTTOM because it does not work
        # for flip cards (for that it would be BORDER.IMAGE)
        layoutData.BORDER.CREDITS + layoutData.SIZE.CREDITS
    )
    layoutData.BORDER.BOTTOM_BOX.TOP = layoutData.BORDER.BOTTOM_BOX.BOTTOM - layoutData.SIZE.BOTTOM_BOX.VERT
    layoutData.BORDER.BOTTOM_BOX.RIGHT = layoutData.BORDER.RULES.RIGHT - 15 # Box is 15 pixels left
    layoutData.BORDER.BOTTOM_BOX.LEFT = layoutData.BORDER.BOTTOM_BOX.RIGHT - layoutData.SIZE.BOTTOM_BOX.HORIZ
    # Calculating bottom font position
    layoutData.FONT_MIDDLE.BOTTOM_H = layoutData.BORDER.BOTTOM_BOX.LEFT + layoutData.SIZE.BOTTOM_BOX.HORIZ // 2
    layoutData.FONT_MIDDLE.BOTTOM_V = layoutData.BORDER.BOTTOM_BOX.TOP + layoutData.SIZE.BOTTOM_BOX.VERT // 2 + BORDER_CENTER_OFFSET

    # Layouts needing adjustments to rules box or non-standard sections
    # Main adventure part has the other part on the left
    if (layoutType == LayoutType.ADV and part == 0):
        layoutData.SIZE.RULES.HORIZ //= 2
        layoutData.BORDER.RULES.LEFT = layoutData.BORDER.RULES.RIGHT - layoutData.SIZE.RULES.HORIZ
    # Fuse layouts have the Fuse section under the rules box
    elif (layoutType == LayoutType.FUS):
        layoutData.SIZE.FUSE = SizeData(
            HORIZ = cardSize.v,
            VERT = 50,
        )
        layoutData.BORDER.RULES.BOTTOM -= layoutData.SIZE.FUSE.VERT
        layoutData.SIZE.RULES.VERT -= layoutData.SIZE.FUSE.VERT
        layoutData.BORDER.FUSE = BorderData(
            TOP = layoutData.BORDER.RULES.BOTTOM,
            BOTTOM = layoutData.BORDER.RULES.BOTTOM + layoutData.SIZE.FUSE.VERT,
            LEFT = 0,
            RIGHT = cardSize.v
        )
        layoutData.FONT_MIDDLE.FUSE_V = layoutData.BORDER.FUSE.TOP +  layoutData.SIZE.FUSE.VERT // 2
    # Attractions have the number box on the right
    elif (layoutType == LayoutType.ATR):
        layoutData.SIZE.ATTRACTION = SizeData(
            HORIZ = 100,
            VERT = layoutData.SIZE.RULES.HORIZ
        )
        layoutData.BORDER.RULES.RIGHT -= layoutData.SIZE.ATTRACTION.HORIZ
        layoutData.SIZE.RULES.HORIZ -= layoutData.SIZE.ATTRACTION.HORIZ
        layoutData.BORDER.ATTRACTION = BorderData(
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
        BORDER = Border(
            # Most borders, except for card borders,
            # are calculated based on sizes
            CARD = BorderData(
                LEFT = 0,
                TOP = 0,
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
            TYPE = 55,
            RULES = SizeData(),
            BOTTOM_BOX = SizeData(
                HORIZ = 160,
                VERT = 60,
            ),
            CREDITS = 55,
        ),
        FONT_MIDDLE = FontMiddle()
    ),
    cardSize=CARD_SIZE,
    layoutType=LayoutType.STD
)

LAYOUT_DATA_CACHE: Dict[Tuple[LayoutType, bool], List[LayoutData]] = {}

def LAYOUT_DATA(layoutType: LayoutType, isPlaytest: bool = False):
    cacheKey = (layoutType, isPlaytest)
    cardSize = CARD_SIZE_PLAYTEST if isPlaytest else CARD_SIZE
    if cacheKey not in LAYOUT_DATA_CACHE:
        if layoutType in [*LAYOUT_TYPES_TWO_PARTS, *LAYOUT_TYPES_DF]:
            LAYOUT_DATA_CACHE[cacheKey] = [calcLayoutData(
                template=TEMPLATE_LAYOUT_DATA,
                cardSize=cardSize,
                layoutType=layoutType,
                part=i
            ) for i in range(2)]
        else:
            LAYOUT_DATA_CACHE[cacheKey] = [calcLayoutData(
                template=TEMPLATE_LAYOUT_DATA,
                cardSize=cardSize,
                layoutType=layoutType
            )]
            
    return LAYOUT_DATA_CACHE[cacheKey]
