from __future__ import annotations
from typing import Any, List, Dict, Set
from typing_extensions import Self
from scrython import Named
from copy import deepcopy
import re

from . import projectConstants as C

colorRe = re.compile(r"[WUBRG]")

def _extractColor(manaCost: str) -> List[C.ManaColors]:
    """
    Extracts the card colors from the mana cost, returned in WUBRG order
    """
    colors: Set[C.ManaColors] = set(map(C.ManaColors, colorRe.findall(manaCost)))
    ret: List[C.ManaColors] = []
    for c in C.ManaColors:
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
    @classmethod
    def from_name(cls, name: str) -> Self:
        named: Named = Named(fuzzy=name)
        return cls(named)

    def __init__(self, card: C.JsonDict | Named | Card):
        
        self.data: C.JsonDict
        if isinstance(card, Named):
            self.data = card.scryfallJson  # type: ignore
        elif isinstance(card, Card):
            self.data = deepcopy(card.data)
        elif isinstance(card, dict): # type: ignore
            self.data = card
        else:
            raise ValueError("You must provide a card")

        self._version: str = C.VERSION
        
        # Setting info for Emblem and Tokens
        if "Emblem" in self.type_line:
            self.data["layout"] = C.LayoutType.EMB.value
            self.data["type_line"] = "Emblem"
            self.data["name"] = self.data["name"].replace(" Emblem", "")

        if "Token" in self.type_line:
            if self.isTwoParts():
                self.data["layout"] = C.LayoutType.TOK.value
            else:
                if self.oracle_text == "":
                    self.data["layout"] = C.LayoutType.VTK.value
                else:
                    self.data["layout"] = C.LayoutType.TOK.value
                
                if len(self.colors) > 0:
                    self.data["color_indicator"] = self.colors

        if self.name in C.BASIC_LANDS:
            self.data["layout"] = C.LayoutType.LND.value

        if not self.isTwoParts() and not self.isTokenOrEmblem() and self.oracle_text == "":
            self.data["layout"] = C.LayoutType.VCR.value


        # Setting non-standard layouts (attraction, fuse, aftermath)
        
        if "Attraction" in self.type_line:
            self.data["layout"] = C.LayoutType.ATR.value

        if not self._hasKey("layout"):
            # Something went horribly, horribly wrong
            raise Exception(f"Card {self.name} has no layout")

        layout = self.layout

        if layout == C.LayoutType.SPL and self.isTwoParts():
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
        """
        Check if the requested key is present in the underlying json
        """
        return attr in self.data

    def _getKey(self, attr: str) -> Any:
        """
        Returns the value of json[attr].

        Raises KeyError if the attribute is not present in the JSON
        """
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
    def colors(self) -> List[C.ManaColors]:
        return [C.ManaColors(c) for c in self._getKey("colors")]

    @property
    def color_indicator(self) -> List[C.ManaColors]:
        return [C.ManaColors(c) for c in self._getKey("color_indicator")]

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
        """
        Returns the layout type of the card as a LayoutType instance.

        Use this to discriminate among the possible card drawing layouts.
        """
        layoutString: str = self._getKey("layout")
        if layoutString in C.LayoutType.values():
            return C.LayoutType(layoutString)
        return C.LayoutType.STD

    @property
    def fuse_text(self) -> str:
        return self._getKey("fuse_text")

    @property
    def card_faces(self) -> List[Card]:
        """
        Returns all the different units in a card.
        
        Any time a single card can be two different named objects,
        the two possibilities are called card faces and can be retrieved via this property.
        
        Examples include the two halves in a split/aftermath, the two faces in a double faced card,
        Adventure/Main card in adventure cards, and both orientations of a flip card.

        Please note that meld cards aren't included in this list.

        If called on faces or on cards having no faces raises AttributeError.
        """
        if self._hasKey("face_num"):
            raise AttributeError(f"Cannot ask for faces of the face {self.name}")

        if not self._hasKey("card_faces"):
            raise AttributeError(f"Cannot ask for faces of the single card {self.name}")

        faces: List[C.JsonDict] = self._getKey("card_faces")
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
            faces[0]["colors"] = _extractColor(faces[0]["mana_cost"])
            faces[1]["colors"] = _extractColor(faces[1]["mana_cost"])

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
        It's also added to flip cards, using tap and untap symbols,
        and for acorn cards.

        Only set up for faces (not whole cards)
        """
        if not (
            (
                self.layout in [C.LayoutType.FLP, *C.LAYOUT_TYPES_DF]
                and self._hasKey("face_num")
            ) or not self.isAcorn()
        ):
            raise AttributeError(f"Card {self.name} has no face symbol")
        if self.isAcorn():
            return C.ACORN_PLAINTEXT
        else:
            return f"{{{self.layout.value}{self.face_num}}}"

    @property
    def face_num(self) -> int:
        """
        The progressive number of the current face in the card (0 or 1)

        0 is the main part, or the left part in cards that don't have a main card, while 1 is the other one.
        
        If a card has a "//" in its Oracle name,
        0 is the object on the left of the //, while 1 is the object on the right.

        If called on cards having faces or on single cards raises AttributeError.
        """
        if self._hasKey("card_faces"):
            raise AttributeError(f"Cannot ask for face number of multifaced card {self.name}")
        if not self._hasKey("face_num"):
            raise AttributeError(f"Cannot ask for face number of single card {self.name}")
        return self._getKey("face_num")

    @property
    def color_indicator_reminder_text(self) -> str:
        """
        How the color indicator would appear if written out.

        This is used instead of a colored dot, since the proxies are in black and white.
        """
        try:
            cardColorIndicator: List[C.ManaColors] = self.color_indicator
        except:
            return ""
        
        if len(cardColorIndicator) == 5:
            colorIndicatorText = "all colors"
        else:
            colorIndicatorNames = [c.name.lower() for c in cardColorIndicator]
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

    def isToken(self) -> bool:
        """
        Check is the card is a token (both with and without text)
        """
        return self.layout in [
            C.LayoutType.TOK,
            C.LayoutType.VTK
        ]

    def isTokenOrEmblem(self) -> bool:
        """
        Check if the card is a token or an emblem (not a sanctioned card)
        """
        return self.isToken() or self.layout == C.LayoutType.EMB

    def isTwoParts(self) -> bool:
        """
        Check if the card has two faces.

        Please note that this is not based on the card layout,
        since a face itsef does not have two faces
        """
        return self._hasKey("card_faces")

    @property
    def flavor_name(self) -> str:
        return self._getKey("flavor_name")

    def hasFlavorName(self) -> bool:
        return self._hasKey("flavor_name")

    def isAcorn(self) -> bool:
        """
        Check if the card is acorn, meaning not-tournament legal
        (the old silver-border).

        This is only an approximation, since it also includes oversized card
        like Vanguard, Conspiracy, and Planes.
        """
        if self.isTokenOrEmblem():
            return False
        legal: Dict[str, str] = self._getKey("legalities")
        return all([
            legal["vintage"] == "not_legal",
            legal["alchemy"] == "not_legal",
            legal["historic"] == "not_legal"
        ])


Deck = List[Card]
Flavor = Dict[str, str]

XY = C.XY