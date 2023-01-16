from __future__ import annotations
from typing import Any, List, Dict, Set
from scrython import Named
from copy import deepcopy
import re

from . import projectConstants as C

colorRe = re.compile(r"[WUBRG]")

JsonDict = C.JsonDict
MTG_COLORS = C.MTG_COLORS

def extractColor(manaCost: str) -> list[MTG_COLORS]:
    colors: Set[MTG_COLORS] = set(colorRe.findall(manaCost))
    ret: list[MTG_COLORS] = []
    for c in C.MANA_SYMBOLS:
        if c in colors:
            ret.append(c)
    return ret


class Card:
    """
    Handler class for a card, a card face, or a card half.
    Can be initialized with a Scryfall search result
    or with a name to be searched in Scryfall.
    Automatically sets aftermath and fuse layouts.
    Automatically sets layout and card face for transform and modal_dfc faces
    Has a method for color indicator reminder text
    """

    def __init__(self, card: JsonDict | Named | Card | None = None, name: str | None = None):
        if name is not None:
            card = Named(fuzzy=name)

        if isinstance(card, Named):
            self.data: JsonDict = card.scryfallJson  # type: ignore
        elif isinstance(card, Card):
            self.data: JsonDict = deepcopy(card.data)
        elif isinstance(card, dict):
            self.data: JsonDict = card
        else:
            raise ValueError("You must provide at least one between a name or a card")

        self._version = C.VERSION
        
        # Setting info for Emblem and Tokens
        if self.isEmblem():
            self.data["layout"] = C.LayoutType.EMB.value
            self.data["type_line"] = "Emblem"
            self.data["name"] = self.data["name"].replace(" Emblem", "")

        if self.isToken():
            if self.isTextlessToken():
                self.data["layout"] = C.LayoutType.VTK.value
            else:
                self.data["layout"] = C.LayoutType.TOK.value
            if not self._hasKey("card_faces") and len(self.colors) > 0:
                self.data["color_indicator"] = self.colors


        # Setting non-standard layouts (attraction, fuse, aftermath)
        
        if self.isAttraction():
            self.data["layout"] = C.LayoutType.ATR.value

        if not self._hasKey("layout"):
            print("wtf")
            return
        layout = self.layout

        if layout == C.LayoutType.SPL:
            # Set up alternative split layouts (aftermath and fuse)
            secondHalfText = self.card_faces[1].oracle_text.split("\n")
            if secondHalfText[0].split(" ")[0] == "Aftermath":
                # Second half begins with Aftermath
                self.data["layout"] = C.LayoutType.AFT.value
            if secondHalfText[-1].split(" ")[0] == "Fuse":
                # Second half ends with Fuse
                self.data["layout"] = C.LayoutType.FUS.value
                # Adding the fuse text to the main card
                self.data["fuse_text"] = secondHalfText[-1]
    

    def _hasKey(self, attr: str) -> bool:
        return attr in self.data

    def _getKey(self, attr: str) -> Any:
        if self._hasKey(attr):
            return self.data[attr]
        raise KeyError(f"Card {self.name} has no key {attr}")

    def __str__(self) -> str:
        return f"Card ({self.name})"

    def __repr__(self) -> str:
        return str(self)

    @property
    def name(self) -> str:
        return self._getKey("name")

    @property
    def colors(self) -> list[C.MTG_COLORS]:
        return self._getKey("colors")

    @property
    def color_indicator(self) -> list[C.MTG_COLORS]:
        return self._getKey("color_indicator")

    @property
    def mana_cost(self) -> str:
        return self._getKey("mana_cost")

    @property
    def oracle_text(self) -> str:
        return self._getKey("oracle_text")

    @property
    def type_line(self) -> str:
        return self._getKey("type_line")

    @property
    def power(self) -> str:
        return self._getKey("power")

    @property
    def toughness(self) -> str:
        return self._getKey("toughness")

    @property
    def loyalty(self) -> str:
        return self._getKey("loyalty")

    @property
    def layout(self) -> C.LayoutType:
        layout_str: str = self._getKey("layout")
        ret: C.LayoutType
        try:
            ret = C.LayoutType(layout_str)
        except:
            ret = C.LayoutType.STD
        return ret

    @property
    def fuse_text(self) -> str:
        return self._getKey("fuse_text")

    @property
    def card_faces(self) -> list[Card]:
        """
        card_faces are all the different units in a card
        E.G. the two halves in a split/aftermath, the two faces in a double faced card,
        adventure/other half in the adventure cards...
        """
        faces: List[JsonDict] = self._getKey("card_faces")
        layout: C.LayoutType = self.layout
        faces[0]["layout"] = layout.value
        faces[1]["layout"] = layout.value
        faces[0]["face_num"] = 0
        faces[1]["face_num"] = 1
        faces[0]["legalities"] = self._getKey("legalities")
        faces[1]["legalities"] = self._getKey("legalities")

        if layout == C.LayoutType.FLP:
            faces[0]["colors"] = self.colors
            faces[1]["colors"] = self.colors
            faces[1]["color_indicator"] = self.colors

        if layout in [
            C.LayoutType.SPL,
            C.LayoutType.FUS,
            C.LayoutType.AFT,
            C.LayoutType.ADV
        ]:
            # Subfaces don't have colors, and if you ask the main face it will respond
            # with all the card's colors, so we need to extract them from mana cost
            faces[0]["colors"] = extractColor(faces[0]["mana_cost"])
            faces[1]["colors"] = extractColor(faces[1]["mana_cost"])

        if layout == C.LayoutType.FUS:
            # Fuse text is handled separately, so we remove it from the faces' oracle text
            faces[0]["oracle_text"] = faces[0]["oracle_text"].replace(
                "\n" + self.fuse_text, ""
            )
            faces[1]["oracle_text"] = faces[1]["oracle_text"].replace(
                "\n" + self.fuse_text, ""
            )

        return [Card(face) for face in faces]

    @property
    def face_symbol(self) -> str:
        """
        The face indicator symbol appearing on dfc cards
        (front face / back face).
        It's also added to flip cards, using tap and untap symbols
        and for acorn cards.

        Only set up for faces (not whole cards)
        """
        assert self.layout in [C.LayoutType.FLP, *C.LAYOUT_TYPES_DF] or self.isAcorn()
        if self.isAcorn():
            return C.ACORN_PLAINTEXT
        else:
            return f"{{{self.layout.value}{self.face_num}}}"

    # @property
    # def face_type(self) -> C.LayoutType:
    #     """
    #     face_type is the analogous of layout for all double cards
        
    #     Value is the same of parent's layout

    #     If it's not present, returns the card's layout
    #     """
    #     if self._hasKey("face_type"):
    #         return C.LayoutType(self._getKey("face_type"))
    #     else:
    #         return self.layout

    @property
    def face_num(self) -> int:
        """
        face_num is the position of the current face in the card (0 or 1)

        0 is the left part (split cards), the vertical part (aftermath),
        the part with the title at the usual place (adventure), the unflipped part (flip)
        or the main face (DFC), while 1 is the other one.

        Only set up for faces (not whole cards)
        """
        return self._getKey("face_num")

    @property
    def color_indicator_reminder_text(self) -> str:
        """
        Since the proxies are b/w, we need to write reminder text
        for color indicators and tokens
        """
        try:
            cardColorIndicator: list[C.MTG_COLORS] = self.color_indicator
        except:
            return ""
        
        if len(cardColorIndicator) == 5:
            colorIndicatorText = "all colors"
        else:
            colorIndicatorNames = [C.COLOR_NAMES[c] for c in cardColorIndicator]
            if len(colorIndicatorNames) == 1:
                colorIndicatorText = colorIndicatorNames[0]
            else:
                colorIndicatorText = f'{", ".join(colorIndicatorNames[:-1])} and {colorIndicatorNames[-1]}'
        
        if self.isToken() and self.name in self.type_line:
            name = "This token"
        else:
            name = self.name

        return f"({name} is {colorIndicatorText}.)\n"

    def hasPT(self) -> bool:
        return self._hasKey("power")

    def hasL(self) -> bool:
        return self._hasKey("loyalty")

    def hasPTL(self) -> bool:
        return self.hasPT() or self.hasL()

    def isBasicLand(self) -> bool:
        return self.name in C.BASIC_LANDS

    def isToken(self) -> bool:
        return "Token" in self.type_line

    def isTextlessToken(self) -> bool:
        return self.isToken() and self.oracle_text == ""

    def isEmblem(self) -> bool:
        return "Emblem" in self.type_line

    def isTokenOrEmblem(self) -> bool:
        return self.isToken() or self.isEmblem()
    
    def isAttraction(self) -> bool:
        return "Attraction" in self.type_line

    def isTwoParts(self) -> bool:
        return self._hasKey("card_faces")

    @property
    def flavor_name(self) -> str:
        return self._getKey("flavor_name")

    def hasFlavorName(self) -> bool:
        return self._hasKey("flavor_name")

    def isAcorn(self) -> bool:
        """
        A crude approximation, also including things like
        Vanguard, Conspiracy and the like, but still useful
        """
        if self.isTokenOrEmblem():
            return False
        legal: dict[str, str] = self._getKey("legalities")
        return all([
            legal["vintage"] == "not_legal",
            legal["alchemy"] == "not_legal",
            legal["historic"] == "not_legal"
        ])


Deck = List[Card]
Flavor = Dict[str, str]

XY = C.XY
Box = C.Box
Layout = C.Layout
