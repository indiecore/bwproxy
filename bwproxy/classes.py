from typing import (
    Any,
    Dict,
    Tuple,
    Union,
    NamedTuple,
    Iterable,
)
from typing_extensions import Literal, Self
from enum import Enum

JsonDict = Dict[str, Any]
RGB = Union[Tuple[int, int, int], Tuple[int, int, int, int]]

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

class ValuedEnum(Enum):
    @classmethod
    def values(cls) -> Iterable[str]:
        for x in cls:
            yield x.value


class LayoutType(ValuedEnum):
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

class ManaColors(ValuedEnum):
    White = "W"
    Blue = "U"
    Black = "B"
    Red = "R"
    Green = "G"

class FrameColors(ValuedEnum):
    Multicolor = "M"
    Colorless = "C"

class PageFormat(ValuedEnum):
    A4 = "a4paper"
    LETTER = "letter"

class CardSize(ValuedEnum):
    STANDARD = "standard"
    SMALL = "small"
    PLAYTEST = "playtest"

Rot = Literal[2, 3, 4]

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

    def __repr__(self):
        return f"T: {self.TOP}, B: {self.BOTTOM}, L: {self.LEFT}, R: {self.RIGHT}"

class SizeData():
    def __init__(
        self,
        HORIZ: int = -1,
        VERT: int = -1,
    ):
        self.HORIZ: int = HORIZ
        self.VERT: int = VERT

    def __repr__(self) -> str:
        return f"H: {self.HORIZ}, V: {self.VERT}"

class Border():
    def __init__(
        self,
        CARD: BorderData,
    ):
        self.CARD: BorderData = CARD
        self.IMAGE: int = -1
        self.TYPE: int = -1
        self.RULES: BorderData = BorderData()
        self.BOTTOM_BOX: BorderData = BorderData()
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
        BOTTOM_BOX: SizeData,
        CREDITS: int,
    ):
        self.CARD: SizeData = CARD
        self.TITLE: int = TITLE
        self.IMAGE: int = IMAGE
        self.TYPE: int = TYPE
        self.RULES: SizeData = RULES
        self.BOTTOM_BOX: SizeData = BOTTOM_BOX
        self.CREDITS: int = CREDITS
        self.FUSE: SizeData
        self.ATTRACTION: SizeData

class FontMiddle():
    def __init__(
        self,
    ):
        self.BOTTOM_H: int = -1
        self.BOTTOM_V: int = -1
        self.FUSE_V: int
        self.ATTRACTION_H: int

class LayoutData():
    def __init__(
        self,
        ROTATION: Union[None, Tuple[Rot, Rot]],
        BORDER: Border,
        SIZE: Size,
        FONT_MIDDLE: FontMiddle,
    ):
        self.ROTATION: Union[None, Tuple[Rot, Rot]] = ROTATION
        self.BORDER: Border = BORDER
        self.SIZE: Size = SIZE
        self.FONT_MIDDLE: FontMiddle = FONT_MIDDLE
        self.ICON_CENTER: XY
        self.IMAGE_POSITION: XY
        self.CARD_SIZE: XY

