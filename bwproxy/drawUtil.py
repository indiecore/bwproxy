from typing import Tuple, List, Match, Union, Optional, Any, overload # type: ignore
from PIL import Image, ImageDraw, ImageFont, ImageColor
import re

from . import projectConstants as C
from .projectTypes import Card, Flavor, XY # type: ignore

RGB = Union[Tuple[int, int, int], Tuple[int, int, int, int]]

DEFAULT_BORDER_RGB = ImageColor.getrgb(C.DEFAULT_FRAME_COLOR)

# Text formatting

specialTextRegex = re.compile(r"\{.+?\}")


def replFunction(m: Match[str]) -> str:
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


def fitOneLine(fontPath: str, text: str, maxWidth: int, fontSize: int) -> ImageFont.FreeTypeFont:
    """
    Function that tries to fit one line of text in the specified width.

    It starts with the specified font size, and if the text is too long
    it reduces the font size by 3 and tries again.
    
    This is used to determine the font size for several card components,
    including title, mana cost, and type line.
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
            if font.getsize(curLine + " " + word)[0] > maxWidth:
                ruleLines.append(curLine)
                curLine = word + " "
            else:
                curLine += word + " "
        ruleLines.append(curLine)
        formattedRules.append("\n".join(ruleLines))

    formattedText = "\n\n".join(formattedRules)

    if font.getsize(formattedText)[1] * len(formattedText.split("\n")) > maxHeight:
        return fitMultiLine(fontPath, cardText, maxWidth, maxHeight, fontSize - 3)
    else:
        return (formattedText, font)


def calcTopValue(
    font: ImageFont.FreeTypeFont, text: str, upperBorder: int, spaceSize: int
) -> int:
    """
    Calculate the vertical value for top anchor in order to center text vertically.

    See https://pillow.readthedocs.io/en/stable/handbook/text-anchors.html#text-anchors
    for explanation about font terms.
    """
    # Middle of the space is at upperBorder + spaceSize // 2,
    # and text is vsize // 2 over the text middle.

    # using getbbox because getsize does get the size :/
    (_, _, _, vsize) = font.getbbox(text, anchor="lt")
    return upperBorder + (spaceSize - vsize) // 2


# Select correct layout info


def getLayoutData(
    card: Card,
    alternativeFrames: bool = False
) -> C.LayoutData:
    """
    Given a card or a card face, return the correct layout
    (taking into consideration if the alternate card frames were requested or not)
    """
    layoutType = card.layout
    if card.isTwoParts():
        faceNum = card.face_num
    else:
        faceNum = 0

    if alternativeFrames:
        if layoutType == C.LayoutType.FLP:
            layoutType = C.LayoutType.TDF
        elif layoutType == C.LayoutType.AFT:
            layoutType = C.LayoutType.SPL

    return C.LAYOUT_DATA[layoutType][faceNum]


# Black frame

def drawStandardRectangle(pen: ImageDraw.ImageDraw, layout: C.LayoutData, bottom: int) -> None:
    """
    Draws a rectangle from the card's top left to the card's right and the bottom parameter.
    """
    pen.rectangle(
        (
            (layout.BORDER.CARD.LEFT, layout.BORDER.CARD.TOP),
            (layout.BORDER.CARD.RIGHT, bottom),
        ),
        outline=C.DEFAULT_FRAME_COLOR,
        width=C.DRAW_SIZE.BORDER,
    )

def makeFrame(
    card: Card, image: Image.Image, alternativeFrames: bool = False
) -> Image.Image:
    """
    Creates a frame on which we can draw the card,
    and draws the basic card parts on it.

    The frame is drawn in black. Color, if requested, will be added later.
    """

    if card.isTwoParts():
        faces = card.card_faces
    else:
        faces = [card]

    for face in faces:
        layoutData = getLayoutData(
            card=face, alternativeFrames=alternativeFrames
        )

        rotation = layoutData.ROTATION
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
                outline=C.DEFAULT_FRAME_COLOR,
                fill=C.WHITE,
                width=C.DRAW_SIZE.BORDER,
            )

        if layoutData.LAYOUT_TYPE == C.LayoutType.FUS:
            pen.rectangle(
                (
                    (layoutData.BORDER.FUSE.LEFT, layoutData.BORDER.FUSE.TOP),
                    (layoutData.BORDER.FUSE.RIGHT, layoutData.BORDER.FUSE.BOTTOM)
                ),
                outline=C.DEFAULT_FRAME_COLOR,
                fill=C.WHITE,
                width=C.DRAW_SIZE.BORDER,
            )

        if layoutData.LAYOUT_TYPE == C.LayoutType.ATR:
            pen.rectangle(
                (
                    (layoutData.BORDER.ATTRACTION.LEFT, layoutData.BORDER.ATTRACTION.TOP),
                    (layoutData.BORDER.ATTRACTION.RIGHT, layoutData.BORDER.ATTRACTION.BOTTOM)
                ),
                outline=C.DEFAULT_FRAME_COLOR,
                fill=C.WHITE,
                width=C.DRAW_SIZE.BORDER
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
                fill=C.DEFAULT_FRAME_COLOR,
                width=C.DRAW_SIZE.BORDER,
            )

        if rotation is not None:
            image = image.transpose(rotation[1])

    return image


# Colored frame utility function


def interpolateColor(color1: RGB, color2: RGB, weight: float) -> RGB:
    """
    Given two colors and a number between 0 and 1, returns the
    combination of those colors with that factor.

    Used to vary with continuity between the two colors:
    if the weight is 0, returns the first one;
    if the weigth is 1, returns the second.
    """
    assert 0 <= weight <= 1
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
        imgColor = ImageColor.getrgb(C.FRAME_COLORS[C.FrameColors.Colorless])
    elif len(colors) == 1:
        multicolor = False
        imgColor = ImageColor.getrgb(C.FRAME_COLORS[colors[0]])
    elif len(colors) == 5:
        multicolor = False
        imgColor = ImageColor.getrgb(C.FRAME_COLORS[C.FrameColors.Multicolor])
    else:
        multicolor = True
        imgColor = ImageColor.getrgb(C.FRAME_COLORS[C.FrameColors.Multicolor])
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

    rotation = layoutData.ROTATION
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
    with a color shift from the first color to the second.
    If the card is a split card variation, the template is separated in two parts,
    each one colored only with the single face colors.

    This template is used to set the colors in the real frame.
    """
    coloredTemplate = Image.new("RGB", size=C.CARD_SIZE, color=C.WHITE)

    if card.layout in [C.LayoutType.SPL, C.LayoutType.FUS, C.LayoutType.AFT]:
        # For split card variants, we create two different half-templates
        # based on the color of each individual face
        # (which are saved in halfImage) and paste them
        # onto the final template

        for face in card.card_faces:
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


# Set icon functions

def resizeSetIcon(setIcon: Image.Image) -> Image.Image:
    iconSize = setIcon.size
    scaleFactor = max(iconSize[0] / C.DRAW_SIZE.ICON, iconSize[1] / C.DRAW_SIZE.ICON)
    setIcon = setIcon.resize(
        size=(int(iconSize[0] / scaleFactor), int(iconSize[1] / scaleFactor))
    )
    return setIcon


def calcIconPosition(setIcon: Image.Image, center: XY) -> XY:
    """
    Since we know the center of the icon,
    we need to shift it by the icon size in order to find
    the top left vertex (the only parameter that Image.paste will accept).

    We cannot store the icon top left, since it depends on the icon size
    (which is not fixed).
    """
    iconSize: XY = XY(*setIcon.size)
    return (center - iconSize.scale(0.5))


def pasteSetIcon(
    card: Card,
    image: Image.Image,
    setIcon: Image.Image,
    alternativeFrames: bool = False,
) -> Image.Image:
    """
    Given a card and a set icon image, pastes the icon on the correct place(s) of the card
    """
    if card.isTwoParts():
        faces = card.card_faces
    else:
        faces = [card]

    for face in faces:
        
        layoutData = getLayoutData(
            card=face, alternativeFrames=alternativeFrames
        )

        rotation = layoutData.ROTATION
        if rotation is not None:
            image = image.transpose(rotation[0])

        center = layoutData.ICON_CENTER

        image.paste(
            im=setIcon,
            box=calcIconPosition(setIcon=setIcon, center=center).tuple(),
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
    elif card.layout == C.LayoutType.EMB:
        illustrationSymbolName = "Emblem"
    else:
        return image

    layoutData = getLayoutData(card=card)

    position = layoutData.IMAGE_POSITION
    illustrationSymbol = Image.open(
        f"{C.BACK_CARD_SYMBOLS_LOC}/{illustrationSymbolName}.png"
    )
    # Here illustrationSymbol is RGBA, so mask uses the alpha channel and everything works
    image.paste(
        illustrationSymbol,
        box=position.tuple(),
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
        )
        if face.layout == C.LayoutType.ATR:
            image = drawAttractionColumn(
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

    rotation = layoutData.ROTATION
    if rotation is not None:
        image = image.transpose(rotation[0])

    manaCornerRight = layoutData.BORDER.CARD.RIGHT - C.DRAW_SIZE.SEPARATOR
    alignNameLeft = layoutData.BORDER.CARD.LEFT + C.DRAW_SIZE.SEPARATOR
    alignNameAnchor = "lt"

    pen = ImageDraw.Draw(image)

    if card.isTokenOrEmblem():
        # Token and Emblems have no mana cost, and have a centered title
        alignNameLeft = layoutData.BORDER.CARD.LEFT + layoutData.SIZE.CARD.HORIZ // 2
        alignNameAnchor = "mt"
        maxNameWidth = layoutData.SIZE.CARD.HORIZ - 2 * C.DRAW_SIZE.SEPARATOR
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
            fontSize=C.DRAW_SIZE.TITLE,
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
        maxNameWidth = xPos - alignNameLeft - C.DRAW_SIZE.SEPARATOR

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

        faceSymbolFont = ImageFont.truetype(C.TITLE_FONT, size=C.DRAW_SIZE.TITLE)
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
        fontSize=C.DRAW_SIZE.TITLE,
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

    # If card has also a flavor name we also write the oracle name
    # Card name goes at the top of the illustration, centered.
    # We exclude composite layouts because I could not care less
    if card.name in flavorNames and card.layout not in [
        C.LayoutType.SPL,
        C.LayoutType.FUS,
        C.LayoutType.AFT,
        C.LayoutType.FLP,
    ]:
        trueNameFont = ImageFont.truetype(font=C.TITLE_FONT, size=C.DRAW_SIZE.TEXT)
        pen.text(
            (
                (layoutData.BORDER.CARD.LEFT + layoutData.BORDER.CARD.RIGHT) // 2,
                layoutData.BORDER.IMAGE + C.DRAW_SIZE.SEPARATOR,
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

    rotation = layoutData.ROTATION
    if rotation is not None:
        image = image.transpose(rotation[0])

    alignTypeLeft = layoutData.BORDER.CARD.LEFT + C.DRAW_SIZE.SEPARATOR
    setIconMargin = (C.DRAW_SIZE.SEPARATOR + C.DRAW_SIZE.ICON) if hasSetIcon else 0
    maxWidth = layoutData.SIZE.CARD.HORIZ - 2 * C.DRAW_SIZE.SEPARATOR - setIconMargin

    pen = ImageDraw.Draw(image)

    typeFont = fitOneLine(
        fontPath=C.TITLE_FONT,
        text=card.type_line,
        maxWidth=maxWidth,
        fontSize=C.DRAW_SIZE.TYPE,
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


def drawAttractionColumn(
    card: Card,
    image: Image.Image
) -> Image.Image:
    """
    Draw Attraction column to Attractions (numbers from 1 to 6)
    We don't colour the numbers based on the card, because
    1) the colouring does dot translate well to a black/white proxy
    2) We should randomize the selected numbers and that does not translate well
    into a deterministic proxy generator
    """
    if card.layout != C.LayoutType.ATR:
        return image

    layoutData = getLayoutData(card=card)

    alignRulesTextAscendant = layoutData.BORDER.RULES.TOP + C.DRAW_SIZE.SEPARATOR

    pen = ImageDraw.Draw(image)

    textFont = ImageFont.truetype(C.RULES_FONT, C.DRAW_SIZE.ATTRACTION)
    pen.text(
        (
            layoutData.FONT_MIDDLE.ATTRACTION_H,
            alignRulesTextAscendant
        ),
        text=C.ATTRACTION_COLUMN,
        font=textFont,
        spacing=C.DRAW_SIZE.ATTRACTION_INTERLINE,
        fill=C.BLACK,
        anchor="ma",
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
    
    rotation = layoutData.ROTATION
    if rotation is not None:
        image = image.transpose(rotation[0])

    cardText = f"{card.color_indicator_reminder_text}{card.oracle_text}".strip()
    if useTextSymbols:
        cardText = printSymbols(cardText)

    alignRulesTextLeft = layoutData.BORDER.RULES.LEFT + C.DRAW_SIZE.SEPARATOR
    alignRulesTextAscendant = layoutData.BORDER.RULES.TOP + C.DRAW_SIZE.SEPARATOR

    maxWidth = layoutData.SIZE.RULES.HORIZ - 2 * C.DRAW_SIZE.SEPARATOR
    maxHeight = layoutData.SIZE.RULES.VERT - 2 * C.DRAW_SIZE.SEPARATOR

    pen = ImageDraw.Draw(image)

    (formattedText, textFont) = fitMultiLine(
        fontPath=C.RULES_FONT,
        cardText=cardText,
        maxWidth=maxWidth,
        maxHeight=maxHeight,
        fontSize=C.DRAW_SIZE.TEXT,
    )
    pen.text(
        (alignRulesTextLeft, alignRulesTextAscendant),
        text=formattedText,
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
        maxWidth=C.CARD_V - 2 * C.DRAW_SIZE.SEPARATOR,
        fontSize=C.DRAW_SIZE.TEXT,
    )
    pen.text(
        (
            C.DRAW_SIZE.SEPARATOR,
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

    rotation = layoutData.ROTATION
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
        maxWidth=layoutData.SIZE.PTL_BOX.HORIZ - 2 * C.DRAW_SIZE.SEPARATOR,
        fontSize=C.DRAW_SIZE.TITLE,
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
    
    layoutData = getLayoutData(
        card, alternativeFrames=alternativeFrames
    )

    rotation = layoutData.ROTATION
    if rotation is not None:
        image = image.transpose(rotation[0])

    alignCreditsLeft = layoutData.BORDER.CARD.LEFT + C.DRAW_SIZE.SEPARATOR

    pen = ImageDraw.Draw(image)

    credFont = ImageFont.truetype(C.RULES_FONT, size=C.DRAW_SIZE.CREDITS)
    pen.text(
        (
            alignCreditsLeft,
            calcTopValue(
                font=credFont,
                text=C.CREDITS,
                upperBorder=layoutData.BORDER.CREDITS,
                spaceSize=layoutData.SIZE.CREDITS,
            ),
        ),
        text=C.CREDITS,
        font=credFont,
        fill=C.BLACK,
        anchor="lt",
    )
    credLength = pen.textlength(text=C.CREDITS + "   ", font=credFont)

    proxyFont = ImageFont.truetype(C.TITLE_FONT, size=C.DRAW_SIZE.CREDITS * 4 // 3)
    pen.text(
        (
            alignCreditsLeft + credLength,
            calcTopValue(
                font=proxyFont,
                text=C.VERSION,
                upperBorder=layoutData.BORDER.CREDITS,
                spaceSize=layoutData.SIZE.CREDITS,
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
    pen.rectangle(((0, 0), C.CARD_SIZE), outline=C.DEFAULT_FRAME_COLOR, width=5)

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
