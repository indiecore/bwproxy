from typing import Tuple, List, Match, Union, Optional, Any, overload # type: ignore
from PIL import Image, ImageDraw, ImageFont, ImageColor
from tqdm import tqdm
import os
import re

from . import projectConstants as C
from .projectTypes import Card, Deck, Flavor, XY, Box, Layout  # type: ignore

RGB = Union[Tuple[int, int, int], Tuple[int, int, int, int]]

DEFAULT_BORDER_COLOR = C.FRAME_COLORS["default"]
DEFAULT_BORDER_RGB: RGB = ImageColor.getrgb(DEFAULT_BORDER_COLOR)

# Text formatting

specialTextRegex = re.compile(r"\{.+?\}")


def replFunction(m: Match[str]):
    """
    Replaces a {abbreviation} with the corresponding code point, if available.
    To be used in re.sub
    """
    t = m.group().upper()
    if t in C.FONT_CODE_POINT:
        return C.FONT_CODE_POINT[t]
    return t


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
    # First − is \u2212, which is not in the font but is used in Planeswalker abilities
    # The second is \u002d, the ASCII one
    return specialTextRegex.sub(replFunction, text).replace("−", "-")


def fitOneLine(fontPath: str, text: str, maxWidth: int, fontSize: int):
    """
    Function that tries to fit one line of text in the specified width.
    It starts with the specified font size, and if the text is too long
    it reduces the font size by one and tries again.
    This is used to determine the font size for several card components,
    including title, Mana cost, and type line
    """
    font = ImageFont.truetype(fontPath, fontSize)
    while font.getsize(text)[0] > maxWidth:
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
    """
    # the terminology here gets weird so to simplify:
    # a rule is a single line of oracle text.
    #       ex: Smuggler's Copter has 3 rules.
    # line means a printed line. a rule may have multiple lines.

    font = ImageFont.truetype(fontPath, fontSize)
    fmtRules = []

    for rule in cardText.split("\n"):
        ruleLines = []
        curLine = ""
        for word in rule.split(" "):
            if font.getsize(curLine + " " + word)[0] > maxWidth:
                ruleLines.append(curLine)
                curLine = word + " "
            else:
                curLine += word + " "
        ruleLines.append(curLine)
        fmtRules.append("\n".join(ruleLines))

    fmtText = "\n\n".join(fmtRules)

    if font.getsize(fmtText)[1] * len(fmtText.split("\n")) > maxHeight:
        return fitMultiLine(fontPath, cardText, maxWidth, maxHeight, fontSize - 3)
    else:
        return (fmtText, font)


def calcTopValue(
    font: ImageFont.FreeTypeFont, text: str, upperBorder: int, spaceSize: int
) -> int:
    """
    Calculate the vertical value for top anchor in order to center text vertically.
    See https://pillow.readthedocs.io/en/stable/handbook/text-anchors.html#text-anchors
    for explanation about font terms

    Middle of the space is at upperBorder + spaceSize // 2,
    and text is vsize // 2 over the text middle.
    So if we want space middle and text middle to align,
    we set top to space middle - vsize // 2 (remember that (0, 0) is top left)
    """
    # using getbbox because getsize does get the size :/
    (_, _, _, vsize) = font.getbbox(text, anchor="lt")
    return upperBorder + (spaceSize - vsize) // 2


# Select correct layout info


def getLayoutData(
    card: Card,
    alternativeFrames: bool = False
) -> C.LayoutData:
    """
    Given a card face, return the correct layout for the face,
    and whether or not it should be rotated or flipped
    """
    layoutType: C.LayoutType
    faceNum: int
    layoutType = card.layout
    if card.isTwoParts():
        faceNum = card.face_num
    else:
        faceNum = 0

    if alternativeFrames:
        if layoutType == C.LayoutType.FLP:
            layoutType = C.LayoutType.STD
        elif layoutType == C.LayoutType.AFT:
            layoutType = C.LayoutType.SPL

    return C.LAYOUT_DATA[layoutType][faceNum]


def getRotation(layoutData: C.LayoutData):
    # This cannot be correctly annotated in Python 3.7, we let type inference do its job
    if layoutData.ROTATION == C.Rot.ROT_0:
        return None
    elif layoutData.ROTATION == C.Rot.ROT_180:
        return (Image.ROTATE_180, Image.ROTATE_180)
    elif layoutData.ROTATION == C.Rot.ROT_90:
        return (Image.ROTATE_90, Image.ROTATE_270)
    else:
        return (Image.ROTATE_270, Image.ROTATE_90)

# Black frame

def drawStandardRectangle(pen: ImageDraw.ImageDraw, layout: C.LayoutData, bottom: int):
    pen.rectangle(
        (
            (layout.BORDER.CARD.LEFT, layout.BORDER.CARD.TOP),
            (layout.BORDER.CARD.RIGHT, bottom),
        ),
        outline=DEFAULT_BORDER_COLOR,
        width=C.BORDER_THICKNESS,
    )

def makeFrame(
    card: Card, image: Image.Image, alternativeFrames: bool = False
) -> Image.Image:
    """
    Creates a frame on which we can draw the card,
    and draws the basic card parts on it (black only)

    Color, if needed, will be added later
    """

    try:
        faces = card.card_faces
    except:
        faces = [card]

    for face in faces:
        layoutData = getLayoutData(
            card=face, alternativeFrames=alternativeFrames
        )

        rotation = getRotation(layoutData)
        if rotation is not None:
            image = image.transpose(rotation[0])

        pen = ImageDraw.Draw(image)

        drawStandardRectangle(pen, layoutData, layoutData.BORDER.IMAGE)
        drawStandardRectangle(pen, layoutData, layoutData.BORDER.TYPE)
        drawStandardRectangle(pen, layoutData, layoutData.BORDER.RULES.TOP)
        drawStandardRectangle(pen, layoutData, layoutData.BORDER.CREDITS)
        drawStandardRectangle(pen, layoutData, layoutData.BORDER.CARD.BOTTOM)

        if face.hasPTL():
            pen.rectangle(
                (
                    (layoutData.BORDER.PTL_BOX.LEFT, layoutData.BORDER.PTL_BOX.TOP),
                    (layoutData.BORDER.PTL_BOX.RIGHT, layoutData.BORDER.PTL_BOX.BOTTOM)
                ),
                outline=DEFAULT_BORDER_COLOR,
                fill=C.WHITE,
                width=C.BORDER_THICKNESS,
            )

        if layoutData.LAYOUT_TYPE == C.LayoutType.FUS:
            pen.rectangle(
                (
                    (layoutData.BORDER.FUSE.LEFT, layoutData.BORDER.FUSE.TOP),
                    (layoutData.BORDER.FUSE.RIGHT, layoutData.BORDER.FUSE.BOTTOM)
                ),
                outline=DEFAULT_BORDER_COLOR,
                fill=C.WHITE,
                width=C.BORDER_THICKNESS,
            )

        if layoutData.LAYOUT_TYPE == C.LayoutType.ATR:
            pen.rectangle(
                (
                    (layoutData.BORDER.ATTRACTION.LEFT, layoutData.BORDER.ATTRACTION.TOP),
                    (layoutData.BORDER.ATTRACTION.RIGHT, layoutData.BORDER.ATTRACTION.BOTTOM)
                ),
                outline=DEFAULT_BORDER_COLOR,
                fill=C.WHITE,
                width=C.BORDER_THICKNESS
            )
        if face.isTokenOrEmblem():
            pen.arc(
                (
                    # We need to offset this vertically because BORDER.IMAGE is the bottom pixel
                    # based on how it was drawn, while here we need the top pixel
                    layoutData.BORDER.CARD.LEFT,
                    layoutData.BORDER.IMAGE - C.BORDER_START_OFFSET,
                    layoutData.BORDER.CARD.RIGHT,
                    layoutData.BORDER.IMAGE + C.TOKEN_ARC_WIDTH - C.BORDER_START_OFFSET
                ),
                start=180,
                end=360,
                fill=DEFAULT_BORDER_COLOR,
                width=C.BORDER_THICKNESS,
            )

        if rotation is not None:
            image = image.transpose(rotation[1])

    return image


# Colored frame utility function


def interpolateColor(color1: RGB, color2: RGB, weight: float) -> RGB:
    return tuple(int(a + (weight * (b - a))) for a, b in zip(color1, color2))


def coloredTemplateSimple(card: Card, size: XY) -> Image.Image:
    """
    Create a new image of specified size that is completely colored.
    If monocolor, colorless or pentacolor the color is uniform,
    otherwise there's a gradient effect for all the card colors
    """
    coloredTemplate = Image.new("RGB", size=size, color=C.WHITE)
    colors = card.colors

    pen = ImageDraw.Draw(coloredTemplate)

    imgColors = []
    if len(colors) == 0:
        multicolor = False
        imgColor = ImageColor.getrgb(C.FRAME_COLORS[C.MTG_COLORLESS])
    elif len(colors) == 1:
        multicolor = False
        imgColor = ImageColor.getrgb(C.FRAME_COLORS[colors[0]])
    elif len(colors) == 5:
        multicolor = False
        imgColor = ImageColor.getrgb(C.FRAME_COLORS[C.MTG_MULTICOLOR])
    else:
        multicolor = True
        imgColor = ImageColor.getrgb(C.FRAME_COLORS[C.MTG_MULTICOLOR])
        imgColors = [ImageColor.getrgb(C.FRAME_COLORS[c]) for c in colors]

    if not multicolor:
        for idx in range(size[0]):
            pen.line(
                [(idx, 0), (idx, size[1])],
                imgColor,
                width=1,
            )
        return coloredTemplate

    n = len(imgColors) - 1
    segmentLength = size[0] // n
    # imgColors.append(imgColors[-1]) # Necessary line in order not to crash

    for idx in range(size[0]):
        i = idx // segmentLength
        pen.line(
            [(idx, 0), (idx, size[1])],
            interpolateColor(
                imgColors[i], imgColors[i + 1], (idx % segmentLength) / segmentLength
            ),
            width=1,
        )

    return coloredTemplate


def colorHalf(
    card: Card, image: Image.Image, layoutData: C.LayoutData
) -> Image.Image:

    rotation = getRotation(layoutData=layoutData)
    if rotation is not None:
        image = image.transpose(rotation[0])

    size = XY(layoutData.SIZE.CARD.HORIZ, layoutData.SIZE.CARD.VERT)
    halfImage = coloredTemplateSimple(card=card, size=size)
    image.paste(halfImage, box=(layoutData.BORDER.CARD.LEFT, layoutData.BORDER.CARD.TOP))
    
    if rotation is not None:
        image = image.transpose(rotation[1])
    return image


def coloredBlank(card: Card) -> Image.Image:
    """
    Creates a template for two-colored card frames,
    with a color shift from the first color to the second
    This template is then used to set the colors in the real frame
    """
    coloredTemplate = Image.new("RGB", size=C.CARD_SIZE, color=C.WHITE)

    if card.layout in [C.LayoutType.SPL, C.LayoutType.FUS, C.LayoutType.AFT]:
        # breakpoint()
        faces = card.card_faces
        for face in faces:
            layoutData = getLayoutData(card=face)
            coloredTemplate = colorHalf(
                card = face,
                image= coloredTemplate,
                layoutData= layoutData
            )
        return coloredTemplate
    # Flip does not have multicolored cards, so I'm ignoring it
    # Adventure for now is monocolored or both parts are the same color
    else:
        return coloredTemplateSimple(card=card, size=C.CARD_SIZE)


def colorBorders(card: Card, image: Image.Image) -> Image.Image:
    coloredTemplate = coloredBlank(card=card)
    for idx in range(C.CARD_H):
        for idy in range(C.CARD_V):
            if image.getpixel((idx, idy)) == DEFAULT_BORDER_RGB:
                image.putpixel((idx, idy), coloredTemplate.getpixel((idx, idy)))  # type: ignore
    return image


# Symbol


def resizeSetIcon(setIcon: Image.Image) -> Image.Image:
    iconSize = setIcon.size
    scaleFactor = max(iconSize[0] / C.SET_ICON_SIZE, iconSize[1] / C.SET_ICON_SIZE)
    setIcon = setIcon.resize(
        size=(int(iconSize[0] / scaleFactor), int(iconSize[1] / scaleFactor))
    )
    return setIcon


def correctSetIconPosition(setIcon: Image.Image, position: XY) -> XY:
    iconSize: XY = XY(*setIcon.size)
    setIconSizeXY: XY = XY(C.SET_ICON_SIZE, C.SET_ICON_SIZE)
    return position + (setIconSizeXY - iconSize).scale(0.5)


def pasteSetIcon(
    card: Card,
    image: Image.Image,
    setIcon: Image.Image,
    alternativeFrames: bool = False,
) -> Image.Image:

    if card.isTwoParts():
        faces = card.card_faces
    else:
        faces = [card]

    for face in faces:
        
        layoutData = getLayoutData(
            card=face, alternativeFrames=alternativeFrames
        )

        rotation = getRotation(layoutData)
        if rotation is not None:
            image = image.transpose(rotation[0])

        layoutName = layoutData.LAYOUT_TYPE

        if layoutName in C.LAYOUT_TYPES_TWO_PARTS:
            position = C.ICON_POSITIONS[layoutName][face.face_num]
        else:
            position = C.ICON_POSITIONS[layoutName][0]

        image.paste(
            im=setIcon,
            box=correctSetIconPosition(setIcon=setIcon, position=position).tuple(),
        )

        if rotation is not None:
            image = image.transpose(rotation[1])

    return image


def drawIllustrationSymbol(card: Card, image: Image.Image) -> Image.Image:
    """
    Emblems and basic lands have a backdrop on the card:
    For land is the corresponding mana symbol, for emblems is the planeswalker symbol.
    """

    if card.layout == C.LayoutType.LND:
        illustrationSymbolName = card.name.split()[-1]
        position = C.LAND_MANA_SYMBOL_POSITION.tuple()
    elif card.layout == C.LayoutType.EMB:
        illustrationSymbolName = "Emblem"
        position = C.EMBLEM_SYMBOL_POSITION.tuple()
    else:
        return image

    illustrationSymbol = Image.open(
        f"{C.BACK_CARD_SYMBOLS_LOC}/{illustrationSymbolName}.png"
    )
    image.paste(
        illustrationSymbol,
        box=position,
        mask=illustrationSymbol,
    )
    return image


# Text


def drawText(
    card: Card,
    image: Image.Image,
    flavorNames: Flavor = {},
    useTextSymbols: bool = True,
    fullArtLands: bool = False,
    hasSetIcon: bool = True,
    alternativeFrames: bool = False,
    useAcornSymbol: bool = True,
) -> Image.Image:
    """
    This function collects all functions writing text to a card
    """

    if card.isTwoParts():
        faces = card.card_faces
    else:
        faces = [card]

    for face in faces:
        if face.layout == C.LayoutType.ADV and face.face_num == 1:
            # This is the adventure side for a card
            hasSetIcon = False
        image = drawTitleLine(
            card=face,
            image=image,
            flavorNames=flavorNames,
            alternativeFrames=alternativeFrames,
            useAcornSymbol=useAcornSymbol,
        )
        if (
            face.layout == C.LayoutType.LND or face.layout == C.LayoutType.EMB
        ) and not fullArtLands:
            image = drawIllustrationSymbol(card=card, image=image)
        image = drawTypeLine(
            card=face,
            image=image,
            hasSetIcon=hasSetIcon,
            alternativeFrames=alternativeFrames,
        )
        if face.layout == C.LayoutType.ATR:
            image = drawAttractionLine(
                card=face,
                image=image
            )
        image = drawTextBox(
            card=face,
            image=image,
            useTextSymbols=useTextSymbols,
            alternativeFrames=alternativeFrames,
        )
        if face.hasPTL():
            image = drawPTL(card=face, image=image, alternativeFrames=alternativeFrames)
        image = drawCredits(card=face, image=image, alternativeFrames=alternativeFrames)

    if card.layout == C.LayoutType.FUS:
        image = drawFuseText(card=card, image=image)

    return image


def drawTitleLine(
    card: Card,
    image: Image.Image,
    flavorNames: Flavor = {},
    alternativeFrames: bool = False,
    useAcornSymbol: bool = True,
) -> Image.Image:
    """
    Draw mana cost. name and flavor name (if present) for a card
    """
    
    layoutData = getLayoutData(
        card=card, alternativeFrames=alternativeFrames
    )

    rotation = getRotation(layoutData)
    if rotation is not None:
        image = image.transpose(rotation[0])

    manaCornerRight = layoutData.BORDER.CARD.RIGHT - C.BORDER
    alignNameLeft = layoutData.BORDER.CARD.LEFT + C.BORDER
    alignNameAnchor = "lt"

    pen = ImageDraw.Draw(image)

    if card.isTokenOrEmblem():
        # Token and Emblems have no mana cost, and have a centered title
        alignNameLeft = layoutData.BORDER.CARD.LEFT + layoutData.SIZE.CARD.HORIZ // 2
        alignNameAnchor = "mt"
        maxNameWidth = layoutData.SIZE.CARD.HORIZ - 2 * C.BORDER
    else:
        manaCost = printSymbols(card.mana_cost)
        # Mana should never be so small that you can fit more than 16 on a line
        maxManaWidth = max(layoutData.SIZE.CARD.HORIZ // 2, C.CARD_H // 16 * len(manaCost))

        # This fitOneLine was born for Oakhame Ranger // Bring Back, which has
        # 4 hybrid mana symbols on the adventure part, making the title unreadable
        # So we force the mana cost to a dimension such that 8 mana symbols
        # occupy at the minimum 1/2 of the horizontal dimension
        # (we don't want the mana symbols to be too small)
        # and the dimension can grow up to half the card length,
        # if it has not already overflown.
        #
        # It also helps with cards like Progenitus or Emergent Ultimatum
        manaFont = fitOneLine(
            fontPath=C.TITLE_FONT,
            text=manaCost,
            maxWidth=maxManaWidth,
            fontSize=C.TITLE_FONT_SIZE,
        )
        # Test for easier mana writing
        pen.text(
            (
                manaCornerRight,
                calcTopValue(
                    font=manaFont,
                    text=manaCost,
                    upperBorder=layoutData.BORDER.CARD.TOP,
                    spaceSize=layoutData.SIZE.TITLE,
                ),
            ),
            text=manaCost,
            font=manaFont,
            fill=C.BLACK,
            anchor="rt",
        )
        xPos = manaCornerRight - manaFont.getsize(manaCost)[0]
        maxNameWidth = xPos - alignNameLeft - C.BORDER

    displayName = flavorNames[card.name] if card.name in flavorNames else card.name

    # Section for card indicator at left of the name: dfc, flip
    # and acorn indicator (for "silver-border" cards)
    # It is separated from title because we want it always at max size
    if (
        (card.isAcorn() and useAcornSymbol)
        or card.layout in C.LAYOUT_TYPES_DF
        or card.layout == C.LayoutType.FLP
    ):
        # Boy I sure hope there will never be acorn AND (dfc / flip) cards
        if card.isAcorn():
            faceSymbol = f"{C.FONT_CODE_POINT[C.ACORN_PLAINTEXT]} "
        else:
            faceSymbol = f"{C.FONT_CODE_POINT[card.face_symbol]} "

        faceSymbolFont = ImageFont.truetype(C.TITLE_FONT, size=C.TITLE_FONT_SIZE)
        pen.text(
            (
                alignNameLeft,
                calcTopValue(
                    font=faceSymbolFont,
                    text=faceSymbol,
                    upperBorder=layoutData.BORDER.CARD.TOP,
                    spaceSize=layoutData.SIZE.TITLE,
                ),
            ),
            text=faceSymbol,
            font=faceSymbolFont,
            fill=C.BLACK,
            anchor="lt",
        )
        faceSymbolSpace = faceSymbolFont.getsize(faceSymbol)[0]
        alignNameLeft += faceSymbolSpace
        maxNameWidth -= faceSymbolSpace

    # Here the indicator section is finished, we now write the card name

    nameFont = fitOneLine(
        fontPath=C.TITLE_FONT,
        text=displayName,
        maxWidth=maxNameWidth,
        fontSize=C.TITLE_FONT_SIZE,
    )
    pen.text(
        (
            alignNameLeft,
            calcTopValue(
                font=nameFont,
                text=displayName,
                upperBorder=layoutData.BORDER.CARD.TOP,
                spaceSize=layoutData.SIZE.TITLE,
            ),
        ),
        text=displayName,
        font=nameFont,
        fill=C.BLACK,
        anchor=alignNameAnchor,
    )

    # Writing oracle name, if card has also a flavor name.
    # Card name goes at the top of the illustration, centered.
    # We exclude composite layouts because I could not care less
    if card.name in flavorNames and card.layout not in [
        C.LayoutType.SPL,
        C.LayoutType.FUS,
        C.LayoutType.AFT,
        C.LayoutType.FLP,
    ]:
        trueNameFont = ImageFont.truetype(font=C.TITLE_FONT, size=C.TEXT_FONT_SIZE)
        pen.text(
            (
                (layoutData.BORDER.CARD.LEFT + layoutData.BORDER.CARD.RIGHT) // 2,
                layoutData.BORDER.IMAGE + C.BORDER,
            ),
            card.name,
            font=trueNameFont,
            fill=C.BLACK,
            anchor="mt",
        )

        if rotation is not None:
            image = image.transpose(rotation[1])

    return image


def drawTypeLine(
    card: Card,
    image: Image.Image,
    hasSetIcon: bool = True,
    alternativeFrames: bool = False,
) -> Image.Image:
    """
    Draws the type line, leaving space for set icon (if present)
    """

    layoutData = getLayoutData(
        card=card, alternativeFrames=alternativeFrames
    )

    rotation = getRotation(layoutData)
    if rotation is not None:
        image = image.transpose(rotation[0])

    alignTypeLeft = layoutData.BORDER.CARD.LEFT + C.BORDER
    setIconMargin = (C.BORDER + C.SET_ICON_SIZE) if hasSetIcon else 0
    maxWidth = layoutData.SIZE.CARD.HORIZ - 2 * C.BORDER - setIconMargin

    pen = ImageDraw.Draw(image)

    typeFont = fitOneLine(
        fontPath=C.TITLE_FONT,
        text=card.type_line,
        maxWidth=maxWidth,
        fontSize=C.TYPE_FONT_SIZE,
    )
    pen.text(
        (
            alignTypeLeft,
            calcTopValue(
                font=typeFont,
                text=card.type_line,
                upperBorder=layoutData.BORDER.TYPE,
                spaceSize=layoutData.SIZE.TYPE,
            ),
        ),
        text=card.type_line,
        font=typeFont,
        fill=C.BLACK,
        anchor="lt",
    )

    if rotation is not None:
        image = image.transpose(rotation[1])

    return image


def drawAttractionLine(
    card: Card,
    image: Image.Image
) -> Image.Image:
    """
    Draw Attraction line to Attractions (numbers from 1 to 6)
    We don't colour the numbers based on the card, because
    1) the colouring does dot translate well to a black/white proxy
    2) We should randomize the selected numbers and that does not translate well
    into a deterministic proxy generator
    """
    if card.layout != C.LayoutType.ATR:
        return image

    layout = getLayoutData(card=card)

    alignRulesTextAscendant = layout.BORDER.RULES.TOP + C.BORDER

    pen = ImageDraw.Draw(image)

    textFont = ImageFont.truetype(C.RULES_FONT, C.ATTRACTION_FONT_SIZE)
    pen.text(
        (layout.FONT_MIDDLE.ATTRACTION_H, alignRulesTextAscendant),
        text=C.ATTRACTION_LINE,
        font=textFont,
        spacing=C.ATTRACTION_PIXELS_BETWEEN_LINES,
        fill=C.BLACK,
        anchor="ca",
    )

    return image


def drawTextBox(
    card: Card,
    image: Image.Image,
    useTextSymbols: bool = True,
    alternativeFrames: bool = False,
) -> Image.Image:
    """
    Draw rules text box, replacing any curly braces plaintext
    with the corresponding symbol (unless specified).
    If there is a colour indicator, we also spell it out
    (it does not translate well into a black/white proxy)
    """

    if card.layout == C.LayoutType.LND:
        return image

    layoutData = getLayoutData(
        card=card, alternativeFrames=alternativeFrames
    )

    rotation = getRotation(layoutData)
    if rotation is not None:
        image = image.transpose(rotation[0])

    cardText = f"{card.color_indicator_reminder_text}{card.oracle_text}".strip()
    if useTextSymbols:
        cardText = printSymbols(cardText)

    alignRulesTextLeft = layoutData.BORDER.RULES.LEFT + C.BORDER
    alignRulesTextAscendant = layoutData.BORDER.RULES.TOP + C.BORDER

    maxWidth = layoutData.SIZE.RULES.HORIZ - 2 * C.BORDER
    maxHeight = layoutData.SIZE.RULES.VERT - 2 * C.BORDER

    pen = ImageDraw.Draw(image)

    (fmtText, textFont) = fitMultiLine(
        fontPath=C.RULES_FONT,
        cardText=cardText,
        maxWidth=maxWidth,
        maxHeight=maxHeight,
        fontSize=C.TEXT_FONT_SIZE,
    )
    pen.text(
        (alignRulesTextLeft, alignRulesTextAscendant),
        text=fmtText,
        font=textFont,
        fill=C.BLACK,
        anchor="la",
    )

    if rotation is not None:
        image = image.transpose(rotation[1])

    return image


def drawFuseText(card: Card, image: Image.Image) -> Image.Image:
    """
    Fuse card have an horizontal line spanning both halves of the card
    """
    if not card.layout == C.LayoutType.FUS:
        return image

    # Both card faces are ok, we just want the fuse info
    layoutData = getLayoutData(card=card.card_faces[0])

    image = image.transpose(Image.ROTATE_90)
    pen = ImageDraw.Draw(image)

    fuseTextFont = fitOneLine(
        fontPath=C.RULES_FONT,
        text=card.fuse_text,
        maxWidth=C.CARD_V - 2 * C.BORDER,
        fontSize=C.TEXT_FONT_SIZE,
    )
    # Using SPLIT_LAYOUT_LEFT because it's indistinguishable from SPLIT_LAYOUT_RIGHT
    pen.text(
        (
            C.BORDER,
            calcTopValue(
                font=fuseTextFont,
                text=card.fuse_text,
                upperBorder=layoutData.BORDER.FUSE.TOP,
                spaceSize=layoutData.SIZE.FUSE.VERT,
            ),
        ),
        text=card.fuse_text,
        font=fuseTextFont,
        fill=C.BLACK,
        anchor="lt",
    )

    image = image.transpose(Image.ROTATE_270)

    return image


def drawPTL(
    card: Card, image: Image.Image, alternativeFrames: bool = False
) -> Image.Image:
    """
    Draws Power / Toughness or Loyalty (if present) on the PTL box
    """

    layoutData = getLayoutData(
        card, alternativeFrames=alternativeFrames
    )
    
    rotation = getRotation(layoutData)
    if rotation is not None:
        image = image.transpose(rotation[0])

    if card.hasPT():
        ptl = f"{card.power}/{card.toughness}"
    elif card.hasL():
        ptl = card.loyalty
    else:
        return image

    pen = ImageDraw.Draw(image)

    ptlFont = fitOneLine(
        fontPath=C.RULES_FONT,
        text=ptl,
        maxWidth=layoutData.SIZE.PTL_BOX.HORIZ - 2 * C.BORDER,
        fontSize=C.TITLE_FONT_SIZE,
    )

    pen.text(
        (layoutData.FONT_MIDDLE.PTL_H, layoutData.FONT_MIDDLE.PTL_V),
        text=ptl,
        font=ptlFont,
        fill=C.BLACK,
        anchor="mm",
    )

    if rotation is not None:
        image = image.transpose(rotation[1])

    return image


def drawCredits(
    card: Card, image: Image.Image, alternativeFrames: bool = False
) -> Image.Image:
    """
    Draws the credits text line in the bottom section (site and version)
    """


    if card.layout == C.LayoutType.ADV and card.face_num == 1:
        return image

    layout = getLayoutData(
        card, alternativeFrames=alternativeFrames
    )
    
    rotation = getRotation(layout)
    if rotation is not None:
        image = image.transpose(rotation[0])

    alignCreditsLeft = layout.BORDER.CARD.LEFT + C.BORDER

    pen = ImageDraw.Draw(image)

    credFont = ImageFont.truetype(C.RULES_FONT, size=C.OTHER_FONT_SIZE)
    pen.text(
        (
            alignCreditsLeft,
            calcTopValue(
                font=credFont,
                text=C.CREDITS,
                upperBorder=layout.BORDER.CREDITS,
                spaceSize=layout.SIZE.CREDITS,
            ),
        ),
        text=C.CREDITS,
        font=credFont,
        fill=C.BLACK,
        anchor="lt",
    )
    credLength = pen.textlength(text=C.CREDITS + "   ", font=credFont)

    proxyFont = ImageFont.truetype(C.TITLE_FONT, size=C.OTHER_FONT_SIZE * 4 // 3)
    pen.text(
        (
            alignCreditsLeft + credLength,
            calcTopValue(
                font=proxyFont,
                text=C.VERSION,
                upperBorder=layout.BORDER.CREDITS,
                spaceSize=layout.SIZE.CREDITS,
            ),
        ),
        text=C.VERSION,
        font=proxyFont,
        fill=C.BLACK,
        anchor="lt",
    )

    if rotation is not None:
        image = image.transpose(rotation[1])

    return image


# Draw card from beginning to end


def drawCard(
    card: Card,
    isColored: bool = False,
    setIcon: Optional[Image.Image] = None,
    flavorNames: Flavor = {},
    useTextSymbols: bool = True,
    fullArtLands: bool = False,
    alternativeFrames: bool = False,
    useAcornSymbol: bool = True,
) -> Image.Image:
    """
    Takes card info and external parameters, producing a complete image.
    """

    image = Image.new("RGB", size=C.CARD_SIZE, color=C.WHITE)
    pen = ImageDraw.Draw(image)
    # Card border
    pen.rectangle(((0, 0), C.CARD_SIZE), outline=DEFAULT_BORDER_COLOR, width=5)

    image = makeFrame(card=card, image=image, alternativeFrames=alternativeFrames)
    if isColored:
        image = colorBorders(card=card, image=image)
    if setIcon is not None:
        image = pasteSetIcon(card=card, image=image, setIcon=setIcon, alternativeFrames=alternativeFrames)
    image = drawText(
        card=card,
        image=image,
        flavorNames=flavorNames,
        useTextSymbols=useTextSymbols,
        fullArtLands=fullArtLands,
        hasSetIcon=setIcon is not None,
        alternativeFrames=alternativeFrames,
        useAcornSymbol=useAcornSymbol,
    )

    return image


# Paging


def batchSpacing(
    n: int,
    batchSize: Tuple[int, int],
    pageSize: XY,
    cardSize: XY,
    noCardSpace: bool = False,
):
    CARD_H = cardSize.h
    CARD_V = cardSize.v
    CARD_DISTANCE = 1 if noCardSpace else C.CARD_DISTANCE
    maxH = pageSize[0] - (CARD_DISTANCE + (CARD_H + CARD_DISTANCE) * batchSize[0])
    maxV = pageSize[1] - (CARD_DISTANCE + (CARD_V + CARD_DISTANCE) * batchSize[1])
    return (
        maxH // 2 + CARD_DISTANCE + (CARD_H + CARD_DISTANCE) * (n % batchSize[0]),
        maxV // 2 + CARD_DISTANCE + (CARD_V + CARD_DISTANCE) * (n // batchSize[0]),
    )


def savePages(
    images: List[Image.Image],
    deckName: str,
    small: bool = False,
    pageFormat: C.PageFormat = C.PageFormat.A4,
    noCardSpace: bool = False,
):
    os.makedirs(os.path.dirname(f"pages/{deckName}/"), exist_ok=True)
    pageHoriz = False
    cardSize = C.CARD_SIZE
    if not small:
        batchSize = (3, 3)
    else:
        batchSize = (4, 4)

    batchNum = batchSize[0] * batchSize[1]

    pageSize: XY = C.PAGE_SIZE[pageFormat]

    if small:
        cardSize = C.SMALL_CARD_SIZE
        images = [image.resize(cardSize) for image in images]

    if pageHoriz:
        pageSize = pageSize.transpose()

    for i in tqdm(
        range(0, len(images), batchNum),
        desc="Pagination progress: ",
        unit="page",
    ):
        batch = images[i : i + batchNum]
        page = Image.new("RGB", size=pageSize, color="white")
        for n in range(len(batch)):
            page.paste(
                batch[n],
                batchSpacing(
                    n,
                    batchSize=batchSize,
                    pageSize=pageSize,
                    cardSize=cardSize,
                    noCardSpace=noCardSpace,
                ),
            )

        page.save(f"pages/{deckName}/{i // batchNum + 1:02}.png", "PNG")
