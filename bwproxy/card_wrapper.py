from __future__ import annotations
from typing import Any, List
from typing_extensions import Self
from scrython import Named
from copy import deepcopy
import re

from .classes import LayoutType, LayoutData, ManaColors, JsonDict, CardOptions
from .other_constants import VERSION, ACORN_PLAINTEXT, BASIC_LANDS, LAYOUT_TYPES_DF
from .dimensions import LAYOUT_DATA

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
        return Card(named)

    def __init__(self, card: JsonDict | Named | Card):
        
        self.data: JsonDict
        if isinstance(card, Named):
            self.data = card.scryfallJson  # type: ignore
        elif isinstance(card, Card):
            self.data = deepcopy(card.data)
        elif isinstance(card, dict): # type: ignore
            self.data = card
        else:
            raise ValueError("You must provide a card")

        self._version: str = VERSION

        # I should keep the Json untouched,
        # but this is actually a stupid thing and I have no qualms modifying it
        if self._hasKey("flavor_name") and self._getKey("flavor_name") == "":
            del(self.data["flavor_name"])
        
        # Setting info for Emblem and Tokens
        if "Emblem" in self.type_line:
            self.data["name"] = self.data["name"].replace(" Emblem", "")

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
    
    def __getattr__(self, name: str) -> str:
        return self._getKey(name)

    _colorRe = re.compile(r"[WUBRG]")

    @classmethod
    def _extractColor(cls, manaCost: str) -> List[ManaColors]:
        """
        Extracts the card colors from the mana cost, returned in WUBRG order
        """
        
        colors: List[ManaColors] = list(map(ManaColors, Card._colorRe.findall(manaCost))) # type:ignore I swear this is correct
        ret: List[ManaColors] = []
        for c in colors:
            if c in ManaColors and c not in ret:
                ret.append(c)
        return ret

    @property
    def name(self) -> str:
        return self._getKey("name")

    @property
    def colors(self) -> List[ManaColors]:
        return [ManaColors(c) for c in self._getKey("colors")]

    @property
    def color_indicator(self) -> List[ManaColors]:
        if self._hasKey("color_indicator"):
            return [ManaColors(c) for c in self._getKey("color_indicator")]
        elif (
            # I hate two-parts tokens
            self.isToken()
            and not self.isTwoParts()
            and len(self.colors) > 0
        ):
            return self.colors
        else:
            return []

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
    def defense(self) -> str:
        return self._getKey("defense")
    
    @property
    def art_crop(self) -> str:
        if self._hasKey("image_uris") and "art_crop" in self.data["image_uris"]:
            return self.data["image_uris"]["art_crop"]
        else:
            return ""
    
    @property
    def artist(self) -> str:
        return self._getKey("artist")

    @property
    def layout(self) -> LayoutType:
        """
        Returns the layout type of the card as a LayoutType instance.

        Use this to discriminate among the possible card drawing layouts.
        """
        if "Emblem" in self.type_line:
            return LayoutType.EMB
        
        elif "Token" in self.type_line:
            return LayoutType.TOK

        elif self.name in BASIC_LANDS:
            return LayoutType.LND

        elif "Attraction" in self.type_line:
            return LayoutType.ATR

        layoutString: str = self._getKey("layout")
        
        if layoutString == LayoutType.SPL.value and self._hasKey("card_faces"):
            secondHalfText = self.data["card_faces"][1]["oracle_text"].split("\n")
            if secondHalfText[0].startswith("Aftermath"):
                return LayoutType.AFT
            elif secondHalfText[-1].startswith("Fuse"):
                return LayoutType.FUS

        if layoutString in LayoutType.values():
            return LayoutType(layoutString)

        return LayoutType.STD

    @property
    def fuse_text(self) -> str:
        if self.layout != LayoutType.FUS:
            raise AttributeError("Cannot retrieve fuse text of non-fuse card")
        return "Fuse (You may cast one or both halves of this card from your hand.)"

    @property
    def card_faces(self) -> List[Self]:
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

        faces: List[JsonDict] = deepcopy(self._getKey("card_faces"))
        layout = self.layout
        faces[0]["layout"] = layout.value
        faces[1]["layout"] = layout.value
        faces[0]["face_num"] = 0
        faces[1]["face_num"] = 1
        faces[0]["legalities"] = self._getKey("legalities")
        faces[1]["legalities"] = self._getKey("legalities")

        # Since LayoutCard changes self.layout, we cannot use self.layout
        # to recognize when to overwrite the faces colors
        if self._getKey("layout") == LayoutType.FLP.value:
            faces[0]["colors"] = self.colors
            faces[1]["colors"] = self.colors
            if layout != LayoutType.FLP:
                faces[1]["color_indicator"] = self.colors

        if layout in [
            LayoutType.SPL,
            LayoutType.FUS,
            LayoutType.AFT,
            LayoutType.ADV
        ]:
            # Subfaces don't have colors, and if you ask the main face it will respond
            # with all the card's colors, so we need to extract them from mana cost
            faces[0]["colors"] = Card._extractColor(faces[0]["mana_cost"])
            faces[1]["colors"] = Card._extractColor(faces[1]["mana_cost"])

        if layout == LayoutType.FUS:
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
                self.layout in [LayoutType.FLP, *LAYOUT_TYPES_DF]
                and self._hasKey("face_num")
            ) or self.isAcorn()
        ):
            raise AttributeError(f"Card {self.name} has no face symbol")
        if self.isAcorn():
            return ACORN_PLAINTEXT
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

    def hasPT(self) -> bool:
        return self._hasKey("power")

    def hasL(self) -> bool:
        return self._hasKey("loyalty")
    
    def hasD(self) -> bool:
        return self._hasKey("defense")

    def hasBottomData(self) -> bool:
        return self.hasPT() or self.hasL() or self.hasD()

    def isToken(self) -> bool:
        """
        Check is the card is a token (both with and without text)
        """
        return self.layout in [
            LayoutType.TOK,
            LayoutType.VTK
        ]

    def isTokenOrEmblem(self) -> bool:
        """
        Check if the card is a token or an emblem (not a sanctioned card).
        """
        return self.isToken() or self.layout == LayoutType.EMB

    def isTwoParts(self) -> bool:
        """
        Check if the card has two faces.

        Please note that this is not based on the card layout,
        since a face itself does not have two faces.
        """
        return self._hasKey("card_faces")

    def isFace(self) -> bool:
        """
        Check if the card is a face, meaning we can retrieve the face_num property.

        Please note that this is not based on the card layout,
        since a card and its faces have the same layout.
        """
        return (not self.isTokenOrEmblem() and self._hasKey("face_num"))

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
        return (
            ( self._hasKey("border") and self._getKey("border") == "silver" )
            or ( self._hasKey("stamp") and self._getKey("stamp") == "acorn" )
        )

class LayoutCard(Card):
    @classmethod
    def from_name(
        cls,
        name: str,
        alternativeFrames: bool = False,
        flavorName: str | None = None,
        isPlaytest: bool = False,
        options:CardOptions = None,
    ) -> Self:
        set = ""

        if (options):
            set = options.SET

        named: Named = Named(fuzzy=name, set=set)
        return LayoutCard(
            named,
            alternativeFrames,
            flavorName,
            isPlaytest,
            options,
        )

    def __init__(
        self,
        card: JsonDict | Named | Card,
        alternativeFrames: bool = False,
        flavorName: str | None = None,
        isPlaytest: bool = False,
        options:CardOptions=None
    ):
        super().__init__(card)
        self.__flavorName = flavorName
        self.__alternativeFrames = alternativeFrames
        self.__isPlaytest = isPlaytest
        self.options = options
    
    @property
    def layout(self) -> LayoutType:
        layoutType = super().layout

        if self.__alternativeFrames:
            if layoutType == LayoutType.FLP:
                layoutType = LayoutType.TDF
            elif layoutType == LayoutType.AFT:
                layoutType = LayoutType.SPL
            elif layoutType == LayoutType.TOK and self.oracle_text == "":
                layoutType = LayoutType.VTK
            elif layoutType == LayoutType.STD and self.oracle_text == "":
                layoutType = LayoutType.VCR

        return layoutType

    @property
    def layoutData(self) -> LayoutData:
        """
        Given a card or a card face, return the correct layout
        (taking into consideration if the alternate card frames were requested or not)
        """
        return LAYOUT_DATA(self.layout, self.__isPlaytest)[self.face_num]

    @property
    def card_faces(self) -> List[Self]:
        if self.isTwoParts():
            return [
                LayoutCard(
                    face,
                    self.__alternativeFrames,
                    flavorName = None,
                    isPlaytest = self.__isPlaytest,
                    options=self.options 
                )
                for face in super().card_faces
            ]
        else:
            return [self]

    @property
    def face_num(self) -> int:
        if self.isFace():
            return super().face_num
        else:
            return 0

    def hasFlavorName(self) -> bool:
        return self.__flavorName is not None or super().hasFlavorName()
    
    def isPlaytestSize(self) -> bool:
        return self.__isPlaytest

    @property
    def flavor_name(self) -> str:
        if self.__flavorName is not None:
            return self.__flavorName
        return super().flavor_name