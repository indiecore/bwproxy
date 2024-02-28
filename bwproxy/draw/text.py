from typing import Tuple, List, Dict, Match, Optional, Any, overload, cast # type: ignore
from PIL import Image, ImageDraw, ImageFont
import re
import sys
import os

from ..classes import LayoutType, ManaColors
from ..card_wrapper import LayoutCard
from ..other_constants import LAYOUT_TYPES_DF, MANA_HYBRID, ACORN_PLAINTEXT, CREDITS, VERSION
from ..dimensions import DRAW_SIZE, BORDER_CENTER_OFFSET

BLACK = (0, 0, 0)

# This or pyinstaller does not work, see https://stackoverflow.com/a/13790741
try:
    basePath = cast(str, sys._MEIPASS) # type: ignore
except:
    basePath = os.path.abspath('.')

BACK_CARD_SYMBOLS_LOC = os.path.join(basePath, "resources/symbols")
TITLE_FONT = os.path.join(basePath, "resources/fonts/title_font.ttf")
RULES_FONT = os.path.join(basePath, "resources/fonts/rules_font.ttf")

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

ATTRACTION_TEXT = "\n".join([chr(0x261 + i) for i in range(6)]) # Numbers 1 to 6, enclosed in circles


@overload
def printSymbols(text: str) -> str:
    ...
@overload
def printSymbols(text: None) -> None:
    ...

def printSymbols(text: Optional[str]) -> Optional[str]:
    """
    Substitutes all {abbreviation} in text with the corresponding code points
    These code points, when written in the program fonts, correspond to the MTG Symbols
    """
    if text is None:
        return text

    def replFunction(m: Match[str]) -> str:
        """
        Replaces a {abbreviation} with the corresponding code point, if available.
        To be used in re.sub
        """
        t = m.group().upper()
        return FONT_CODE_POINT.get(t, t)
    
    # First − is \u2212, which is not in the font but is used in Planeswalker abilities
    # The second is \u002d, the ASCII one
    return re.sub(r"\{.+?\}", replFunction, text).replace("−", "-")


def fitOneLine(fontPath: str, text: str, maxWidth: int, fontSize: int) -> ImageFont.FreeTypeFont:
    """
    Function that tries to fit one line of text in the specified width.

    It starts with the specified font size, and if the text is too long
    it reduces the font size by 3 and tries again.
    
    This is used to determine the font size for several card components,
    including title, mana cost, and type line.
    """
    font = ImageFont.truetype(fontPath, fontSize)
    while font.getbbox(text)[2] > maxWidth:
        fontSize -= 3
        font = ImageFont.truetype(fontPath, fontSize)
    return font


def fitMultiLine(
    fontPath: str, cardText: str, maxWidth: int, maxHeight: int, fontSize: int
) -> Tuple[str, ImageFont.FreeTypeFont]:
    """
    Recursive function that tries to fit multiple lines of text in the specified box.

    It starts with the specified font size, chops the text based on the max width,
    and if the text overflows vertically it reduces the font size by one and tries again.

    This is mainly used to determine font size for rules box.

    Returns the text, with newlines inserted to make it fit,
    and the specified font at the correct font size
    """
    # The terminology here gets weird so to simplify:
    # A rule is a single unit of oracle text, separated by newline characters.
    # Rules do not depend from how the card is printed.
    #
    # Ex: The following card (Smuggler's Copter) has 3 rules:
    # Flying
    # Whenever Smuggler's Copter attacks or blocks, you may draw a card. If you do, discard a card.
    # Crew 1 (Tap any number of creatures you control with total power 1 or more: This Vehicle becomes an artifact creature until end of turn.)
    #
    # A line means a line as printed on the finished proxy,
    # and as such lines depend from how the card is printed.
    #
    # A rule may be composed of multiple lines.

    font = ImageFont.truetype(fontPath, fontSize)
    formattedRules: List[str] = []

    for rule in cardText.split("\n"):
        ruleLines: List[str] = []
        curLine = ""
        for word in rule.split(" "):
            if font.getbbox(curLine + " " + word)[2] > maxWidth:
                ruleLines.append(curLine)
                curLine = word + " "
            else:
                curLine += word + " "
        ruleLines.append(curLine)
        formattedRules.append("\n".join(ruleLines))

    formattedText = "\n\n".join(formattedRules)

    if font.getbbox(formattedText)[3] * len(formattedText.split("\n")) > maxHeight:
        return fitMultiLine(fontPath, cardText, maxWidth, maxHeight, fontSize - 3)
    else:
        return (formattedText, font)


def calcAscendantValue(
    font: ImageFont.FreeTypeFont, text: str, upperBorder: int, spaceSize: int
) -> int:
    """
    Calculate the vertical value for the ascendant anchor in order to center text vertically.

    See https://pillow.readthedocs.io/en/stable/handbook/text-anchors.html#text-anchors
    for explanation about font terms.
    """
    # Middle of the space is at upperBorder + spaceSize // 2,
    # and text is vsize // 2 over the text middle.

    # using getbbox because getsize is deprecated.
    # I'm adding "{G}" to the text in order to force the bounding box
    # to consider reasonable top and bottom anchors
    gMana = printSymbols("{G}")
    (_, vtop, _, vbottom) = font.getbbox(gMana, anchor="ls")
    vsize = vbottom - vtop
    return upperBorder + (spaceSize - vsize) // 2 - vtop


def drawTitleLine(
    card: LayoutCard,
    image: Image.Image,
    useAcornSymbol: bool = True,
) -> Image.Image:
    """
    Draw mana cost. name and flavor name (if present) for a card
    """

    layoutData = card.layoutData

    rotation = layoutData.ROTATION
    if rotation is not None:
        image = image.transpose(rotation[0])

    pen = ImageDraw.Draw(image)

    if card.isTokenOrEmblem():
        # Token and Emblems have no mana cost, and have a centered title
        # They also don't have card indicators or flavor names
        # and are not rotated, so we can return early
        maxNameWidth = layoutData.SIZE.CARD.HORIZ - 2 * DRAW_SIZE.SEPARATOR
        alignNameMiddle = layoutData.BORDER.CARD.LEFT + layoutData.SIZE.CARD.HORIZ // 2

        nameFont = fitOneLine(
            fontPath=TITLE_FONT,
            text=card.name,
            maxWidth=maxNameWidth,
            fontSize=DRAW_SIZE.TITLE,
        )
        pen.text(
            (
                alignNameMiddle,
                calcAscendantValue(
                    font=nameFont,
                    text=card.name,
                    upperBorder=layoutData.BORDER.CARD.TOP,
                    spaceSize=layoutData.SIZE.TITLE,
                ),
            ),
            text=card.name,
            font=nameFont,
            fill=BLACK,
            anchor="ms",
        )

        return image
        
    # Card is not a token or an emblem

    manaCost = printSymbols(card.mana_cost)
    # We may need to shrink the mana cost in order to make the title readable.
    # That's the case for Oakhame Ranger // Bring Back, on the Bring Back side.
    # It also helps with cards like Progenitus or the Ultimatums, having many mana symbols in the cost
    # However mana should never be too small:
    # A good rule of thumb is that we don't want it to be possible to have more than 16 mana on a line
    maxManaWidth = max(layoutData.SIZE.CARD.HORIZ // 2, layoutData.SIZE.CARD.HORIZ // 16 * len(manaCost))
    manaFont = fitOneLine(
        fontPath=TITLE_FONT,
        text=manaCost,
        maxWidth=maxManaWidth,
        fontSize=DRAW_SIZE.TITLE,
    )

    manaCornerRight = layoutData.BORDER.CARD.RIGHT - DRAW_SIZE.SEPARATOR

    pen.text(
        (
            manaCornerRight,
            calcAscendantValue(
                font=manaFont,
                text=manaCost,
                upperBorder=layoutData.BORDER.CARD.TOP,
                spaceSize=layoutData.SIZE.TITLE,
            ),
        ),
        text=manaCost,
        font=manaFont,
        fill=BLACK,
        anchor="rs",
    )
    xPos = manaCornerRight - manaFont.getbbox(manaCost)[2]
    alignNameLeft = layoutData.BORDER.CARD.LEFT + DRAW_SIZE.SEPARATOR
    maxNameWidth = xPos - alignNameLeft - DRAW_SIZE.SEPARATOR

    displayName = card.flavor_name if card.hasFlavorName() else card.name

    # Section for card indicator at left of the name: dfc, flip
    # and acorn indicator (for "silver-border" cards)
    # It is separated from title because we want it always at max size
    if (
        (card.isAcorn() and useAcornSymbol)
        or card.layout in LAYOUT_TYPES_DF
        or card.layout == LayoutType.FLP
    ):
        # Boy I sure hope there will never be acorn AND (dfc / flip) cards
        faceSymbol = f"{FONT_CODE_POINT[card.face_symbol]} "

        faceSymbolFont = ImageFont.truetype(TITLE_FONT, size=DRAW_SIZE.TITLE)
        pen.text(
            (
                alignNameLeft,
                calcAscendantValue(
                    font=faceSymbolFont,
                    text=faceSymbol,
                    upperBorder=layoutData.BORDER.CARD.TOP,
                    spaceSize=layoutData.SIZE.TITLE,
                ),
            ),
            text=faceSymbol,
            font=faceSymbolFont,
            fill=BLACK,
            anchor="ls",
        )
        faceSymbolSpace = faceSymbolFont.getbbox(faceSymbol)[2]
        alignNameLeft += faceSymbolSpace
        maxNameWidth -= faceSymbolSpace

    # Here the indicator section is finished, we now write the card name

    nameFont = fitOneLine(
        fontPath=TITLE_FONT,
        text=displayName,
        maxWidth=maxNameWidth,
        fontSize=DRAW_SIZE.TITLE,
    )
    pen.text(
        (
            alignNameLeft,
            calcAscendantValue(
                font=nameFont,
                text=displayName,
                upperBorder=layoutData.BORDER.CARD.TOP,
                spaceSize=layoutData.SIZE.TITLE,
            ),
        ),
        text=displayName,
        font=nameFont,
        fill=BLACK,
        anchor="ls",
    )

    # If card has also a flavor name we also write the oracle name
    # Card name goes at the top of the illustration, centered.
    # We exclude composite layouts because I could not care less
    if card.hasFlavorName() and card.layout not in [
        LayoutType.SPL,
        LayoutType.FUS,
        LayoutType.AFT,
        LayoutType.FLP,
    ]:
        trueNameFont = ImageFont.truetype(font=TITLE_FONT, size=DRAW_SIZE.TEXT)
        pen.text(
            (
                (layoutData.BORDER.CARD.LEFT + layoutData.BORDER.CARD.RIGHT) // 2,
                layoutData.BORDER.IMAGE + DRAW_SIZE.SEPARATOR,
            ),
            card.name,
            font=trueNameFont,
            fill=BLACK,
            anchor="mt",
        )

    if rotation is not None:
        image = image.transpose(rotation[1])

    return image


def drawIllustrationSymbol(card: LayoutCard, image: Image.Image) -> Image.Image:
    """
    Emblems and basic lands have a backdrop on the card:
    For land is the corresponding mana symbol, for emblems is the planeswalker symbol.
    """

    if card.layout == LayoutType.LND:
        illustrationSymbolName = card.name.split()[-1]
    elif card.layout == LayoutType.EMB:
        illustrationSymbolName = "Emblem"
    else:
        return image

    layoutData = card.layoutData

    position = layoutData.IMAGE_POSITION
    illustrationSymbol = Image.open(
        f"{BACK_CARD_SYMBOLS_LOC}/{illustrationSymbolName}.png"
    )
    # Here illustrationSymbol is RGBA, so mask uses the alpha channel and everything works
    image.paste(
        illustrationSymbol,
        box=position.tuple(),
        mask=illustrationSymbol,
    )
    return image


def drawTypeLine(
    card: LayoutCard,
    image: Image.Image,
    hasSetIcon: bool = True,
) -> Image.Image:
    """
    Draws the type line, leaving space for set icon (if present)
    """

    layoutData = card.layoutData

    rotation = layoutData.ROTATION
    if rotation is not None:
        image = image.transpose(rotation[0])

    alignTypeLeft = layoutData.BORDER.CARD.LEFT + DRAW_SIZE.SEPARATOR
    setIconMargin = (DRAW_SIZE.SEPARATOR + DRAW_SIZE.ICON) if hasSetIcon else 0
    maxWidth = layoutData.SIZE.CARD.HORIZ - 2 * DRAW_SIZE.SEPARATOR - setIconMargin
    text = card.type_line
    if len(card.color_indicator) > 0:
        colorIndicatorStr = printSymbols(
            "".join("{" + color.value.upper() + "}" for color in card.color_indicator)
        )
        text = f"{text} ({colorIndicatorStr})"

    pen = ImageDraw.Draw(image)

    typeFont = fitOneLine(
        fontPath=TITLE_FONT,
        text=text,
        maxWidth=maxWidth,
        fontSize=DRAW_SIZE.TYPE,
    )
    pen.text(
        (
            alignTypeLeft,
            calcAscendantValue(
                font=typeFont,
                text=text,
                upperBorder=layoutData.BORDER.TYPE,
                spaceSize=layoutData.SIZE.TYPE,
            ) - BORDER_CENTER_OFFSET,
        ),
        text=text,
        font=typeFont,
        fill=BLACK,
        anchor="ls",
    )

    if rotation is not None:
        image = image.transpose(rotation[1])

    return image


def drawAttractionColumn(
    card: LayoutCard,
    image: Image.Image
) -> Image.Image:
    """
    Draw Attraction column to Attractions (numbers from 1 to 6)
    We don't colour the numbers based on the card, because
    1) the colouring does dot translate well to a black/white proxy
    2) We should randomize the selected numbers and that does not translate well
    into a deterministic proxy generator
    """
    if card.layout != LayoutType.ATR:
        return image

    layoutData = card.layoutData

    alignRulesTextAscendant = layoutData.BORDER.RULES.TOP + DRAW_SIZE.SEPARATOR

    pen = ImageDraw.Draw(image)

    textFont = ImageFont.truetype(RULES_FONT, DRAW_SIZE.ATTRACTION)
    pen.text(
        (
            layoutData.FONT_MIDDLE.ATTRACTION_H,
            alignRulesTextAscendant
        ),
        text=ATTRACTION_TEXT,
        font=textFont,
        spacing=DRAW_SIZE.ATTRACTION_INTERLINE,
        fill=BLACK,
        anchor="ma",
    )

    return image


def drawTextBox(
    card: LayoutCard,
    image: Image.Image,
    useTextSymbols: bool = True,
) -> Image.Image:
    """
    Draw rules text box, replacing any curly braces plaintext
    with the corresponding symbol (unless specified).
    If there is a colour indicator, we also spell it out
    (it does not translate well into a black/white proxy)
    """

    if card.layout in [LayoutType.LND, LayoutType.VCR, LayoutType.VTK]:
        return image

    layoutData = card.layoutData

    rotation = layoutData.ROTATION
    if rotation is not None:
        image = image.transpose(rotation[0])

    cardText = card.oracle_text.strip()
    if useTextSymbols:
        cardText = printSymbols(cardText)

    alignRulesTextLeft = layoutData.BORDER.RULES.LEFT + DRAW_SIZE.SEPARATOR
    alignRulesTextAscendant = layoutData.BORDER.RULES.TOP + DRAW_SIZE.SEPARATOR

    maxWidth = layoutData.SIZE.RULES.HORIZ - 2 * DRAW_SIZE.SEPARATOR
    maxHeight = layoutData.SIZE.RULES.VERT - 1 * DRAW_SIZE.SEPARATOR # Was 2 but it prints too high

    pen = ImageDraw.Draw(image)

    (formattedText, textFont) = fitMultiLine(
        fontPath=RULES_FONT,
        cardText=cardText,
        maxWidth=maxWidth,
        maxHeight=maxHeight,
        fontSize=DRAW_SIZE.TEXT,
    )
    pen.text(
        (alignRulesTextLeft, alignRulesTextAscendant),
        text=formattedText,
        font=textFont,
        fill=BLACK,
        anchor="la",
    )

    if rotation is not None:
        image = image.transpose(rotation[1])

    return image


def drawFuseText(card: LayoutCard, image: Image.Image) -> Image.Image:
    """
    Fuse card have an horizontal line spanning both halves of the card
    """
    if not card.layout == LayoutType.FUS:
        return image

    # Both card faces are ok, we just want the fuse info
    layoutData = card.layoutData

    rotation = layoutData.ROTATION
    if rotation is not None:
        image = image.transpose(rotation[0])

    pen = ImageDraw.Draw(image)

    fuseTextFont = fitOneLine(
        fontPath=RULES_FONT,
        text=card.fuse_text,
        maxWidth=layoutData.CARD_SIZE.v - 2 * DRAW_SIZE.SEPARATOR,
        fontSize=DRAW_SIZE.TEXT,
    )
    pen.text(
        (
            DRAW_SIZE.SEPARATOR,
            calcAscendantValue(
                font=fuseTextFont,
                text=card.fuse_text,
                upperBorder=layoutData.BORDER.FUSE.TOP,
                spaceSize=layoutData.SIZE.FUSE.VERT,
            ),
        ),
        text=card.fuse_text,
        font=fuseTextFont,
        fill=BLACK,
        anchor="ls",
    )

    if rotation is not None:
        image = image.transpose(rotation[1])

    return image


def drawBottomData(
    card: LayoutCard, image: Image.Image
) -> Image.Image:
    """
    Draws bottom data (Power / Toughness, Loyalty or defense) (if present) on the bottom box
    """

    layoutData = card.layoutData

    rotation = layoutData.ROTATION
    if rotation is not None:
        image = image.transpose(rotation[0])

    if card.hasPT():
        bottomData = f"{card.power}/{card.toughness}"
    elif card.hasL():
        bottomData = card.loyalty
    elif card.hasD():
        bottomData = card.defense
    else:
        return image

    pen = ImageDraw.Draw(image)

    bottomDataFont = fitOneLine(
        fontPath=RULES_FONT,
        text=bottomData,
        maxWidth=layoutData.SIZE.BOTTOM_BOX.HORIZ - 2 * DRAW_SIZE.SEPARATOR,
        fontSize=DRAW_SIZE.TITLE,
    )

    pen.text(
        (layoutData.FONT_MIDDLE.BOTTOM_H, layoutData.FONT_MIDDLE.BOTTOM_V),
        text=bottomData,
        font=bottomDataFont,
        fill=BLACK,
        anchor="mm",
    )

    if rotation is not None:
        image = image.transpose(rotation[1])

    return image


def drawCredits(
    card: LayoutCard, image: Image.Image
) -> Image.Image:
    """
    Draws the credits text line in the bottom section (site and version)
    """

    if card.layout == LayoutType.ADV and card.face_num == 1:
        return image

    layoutData = card.layoutData  
    rotation = layoutData.ROTATION
    if rotation is not None:
        image = image.transpose(rotation[0])

    alignCreditsLeft = layoutData.BORDER.CARD.LEFT + DRAW_SIZE.SEPARATOR

    pen = ImageDraw.Draw(image)
    fontSize = DRAW_SIZE.CREDITS_PLAYTEST if card.isPlaytestSize() else DRAW_SIZE.CREDITS

    creditsText = CREDITS.format(card.artist) + " " + VERSION;
    credFont = fitOneLine(
        fontPath=RULES_FONT,
        text=creditsText,
        maxWidth=layoutData.SIZE.CARD.HORIZ - 2 * DRAW_SIZE.SEPARATOR,
        fontSize=fontSize,
    )

    alignCreditsAscendant = calcAscendantValue(
        font=credFont,
        text=creditsText + VERSION,
        upperBorder=layoutData.BORDER.CREDITS,
        spaceSize=layoutData.SIZE.CREDITS,
    )

    pen.text(
        (
            alignCreditsLeft,
            alignCreditsAscendant
        ),
        text=creditsText,
        font=credFont,
        fill=BLACK,
        anchor="ls",
    )
   
    if rotation is not None:
        image = image.transpose(rotation[1])

    return image


def drawText(
    card: LayoutCard,
    image: Image.Image,
    useTextSymbols: bool = True,
    fullArtLands: bool = False,
    hasSetIcon: bool = True,
    useAcornSymbol: bool = True,
) -> Image.Image:
    """
    This function collects all functions writing text to a card
    """

    for face in card.card_faces:
        if face.layout == LayoutType.ADV and face.face_num == 1:
            # This is the adventure side for a card
            hasSetIcon = False
        
        image = drawTitleLine(
            card=face,
            image=image,
            useAcornSymbol=useAcornSymbol,
        )

        if (
            face.layout in [LayoutType.LND, LayoutType.EMB]
        ) and not fullArtLands:
            image = drawIllustrationSymbol(
                card=card,
                image=image
            )
        
        image = drawTypeLine(
            card=face,
            image=image,
            hasSetIcon=hasSetIcon,
        )

        if face.layout == LayoutType.ATR:
            image = drawAttractionColumn(
                card=face,
                image=image
            )
        
        image = drawTextBox(
            card=face,
            image=image,
            useTextSymbols=useTextSymbols,
        )
        if face.hasBottomData():
            image = drawBottomData(card=face, image=image)
        image = drawCredits(card=face, image=image)

    if card.layout == LayoutType.FUS:
        image = drawFuseText(card=card, image=image)

    return image
