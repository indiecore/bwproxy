import urllib.request 
from PIL import Image, ImageDraw, ImageColor, ImageOps, ImageFilter, ImageChops

import numpy as np
from pprint import pprint

from ..classes import RGB, XY, LayoutData, LayoutType, ManaColors, FrameColors
from ..card_wrapper import LayoutCard
from ..dimensions import DRAW_SIZE, BORDER_START_OFFSET, TOKEN_ARC_WIDTH

FRAME_COLORS = {
    ManaColors.White: "#fff53f",
    ManaColors.Blue: "#127db4",
    ManaColors.Black: "#430163",
    ManaColors.Red: "#e13c32",
    ManaColors.Green: "#006732",
    FrameColors.Colorless: "#919799",
    FrameColors.Multicolor: "#d4af37",  # Multicolor / Gold
}
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)

# Black frame

def drawStandardRectangle(pen: ImageDraw.ImageDraw, layout: LayoutData, bottom: int) -> None:
    """
    Draws a rectangle from the card's top left to the card's right and the bottom parameter.
    """
    pen.rectangle(
        (
            (layout.BORDER.CARD.LEFT, layout.BORDER.CARD.TOP),
            (layout.BORDER.CARD.RIGHT, bottom),
        ),
        outline=BLACK,
        width=DRAW_SIZE.BORDER,
    )

def drawCardArt(card:LayoutCard, pen: ImageDraw.Image, layout: LayoutData, bottom: int) -> None:
    url = card.art_crop;

    urllib.request.urlretrieve(url, "test.png") 
    img = Image.open("test.png")

    grayImg = img.convert("L")
    grayImg = grayImg.filter(filter=ImageFilter.SMOOTH_MORE)
    
    threshold = 40
    thresholded = grayImg.point(lambda p : p > threshold and 255)

    inverted = grayImg.point(lambda i: 255 - i) # invert
    blurredImage = inverted.filter(filter=ImageFilter.BLUR)

    result = Image.fromarray(dodge(np.asarray(blurredImage), np.asarray(grayImg)))
    result = result.filter(filter=ImageFilter.EDGE_ENHANCE)

    result = ImageChops.multiply(thresholded, result)

    originalRatio = img.height / img.width;
    imgWidth = card.layoutData.CARD_SIZE.h

    result = result.resize((imgWidth, round(imgWidth * originalRatio)))

    pen.paste(
        result,
        (DRAW_SIZE.BORDER, bottom)
    )

def greyscale(greyShades:int, pixel):
    conversionFactor = 255 / 3
    average = (pixel[0] + pixel[1] + pixel[2]) / 3;
    grey = round(average//conversionFactor * conversionFactor);
    return (grey, grey, grey)

def dodge(front, back) -> np.ndarray:
    result=back*256.0/(256.0-front) 
    result[result>255]=255
    result[front==255]=255
    return result.astype('uint8')

def makeFrameBlack(
    card: LayoutCard
) -> Image.Image:
    """
    Creates a black frame on which we can draw the card,
    based on the card layout info
    """

    cardSize = card.layoutData.CARD_SIZE
    frame = Image.new("RGB", size=cardSize, color=WHITE)
    pen = ImageDraw.Draw(frame)
    # Card border
    pen.rectangle(((0, 0), cardSize), outline=BLACK, width=5)

    for face in card.card_faces:

        layoutData = face.layoutData
        pprint(vars(face.layoutData.BORDER))
        rotation = layoutData.ROTATION
        if rotation is not None:
            frame = frame.transpose(rotation[0])

        pen = ImageDraw.Draw(frame)

        drawCardArt(card, frame, layoutData, layoutData.BORDER.IMAGE)
        drawStandardRectangle(pen, layoutData, layoutData.BORDER.IMAGE)
        drawStandardRectangle(pen, layoutData, layoutData.BORDER.TYPE)
        drawStandardRectangle(pen, layoutData, layoutData.BORDER.RULES.TOP)
        drawStandardRectangle(pen, layoutData, layoutData.BORDER.CREDITS)
        drawStandardRectangle(pen, layoutData, layoutData.BORDER.CARD.BOTTOM)

        if face.hasBottomData():
            pen.rectangle(
                (
                    (layoutData.BORDER.BOTTOM_BOX.LEFT, layoutData.BORDER.BOTTOM_BOX.TOP),
                    (layoutData.BORDER.BOTTOM_BOX.RIGHT, layoutData.BORDER.BOTTOM_BOX.BOTTOM)
                ),
                outline=BLACK,
                fill=WHITE,
                width=DRAW_SIZE.BORDER,
            )

        if face.layout == LayoutType.FUS:
            pen.rectangle(
                (
                    (layoutData.BORDER.FUSE.LEFT, layoutData.BORDER.FUSE.TOP),
                    (layoutData.BORDER.FUSE.RIGHT, layoutData.BORDER.FUSE.BOTTOM)
                ),
                outline=BLACK,
                fill=WHITE,
                width=DRAW_SIZE.BORDER,
            )

        if face.layout == LayoutType.ATR:
            pen.rectangle(
                (
                    (layoutData.BORDER.ATTRACTION.LEFT, layoutData.BORDER.ATTRACTION.TOP),
                    (layoutData.BORDER.ATTRACTION.RIGHT, layoutData.BORDER.ATTRACTION.BOTTOM)
                ),
                outline=BLACK,
                fill=WHITE,
                width=DRAW_SIZE.BORDER
            )
        if face.isTokenOrEmblem():
            pen.arc(
                (
                    # We need to offset this vertically because BORDER.IMAGE is the bottom pixel
                    # based on how it was drawn, while here we need the top pixel
                    layoutData.BORDER.CARD.LEFT,
                    layoutData.BORDER.IMAGE - BORDER_START_OFFSET,
                    layoutData.BORDER.CARD.RIGHT,
                    layoutData.BORDER.IMAGE + TOKEN_ARC_WIDTH - BORDER_START_OFFSET
                ),
                start=180,
                end=360,
                fill=BLACK,
                width=DRAW_SIZE.BORDER,
            )

        if rotation is not None:
            frame = frame.transpose(rotation[1])

    return frame


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


def makeColorTemplateSingleFace(card: LayoutCard, size: XY) -> Image.Image:
    """
    Create a new image of specified size that is completely colored.

    If monocolor, colorless or pentacolor the color is uniform,
    otherwise there's a gradient effect for all the card colors.

    """
    coloredTemplate = Image.new("RGB", size=size, color=WHITE)
    colors = card.colors

    pen = ImageDraw.Draw(coloredTemplate)

    if 1 < len(colors) < 5:
        imgColors = [ImageColor.getrgb(FRAME_COLORS[c]) for c in colors]
        # The length of each of the len(colors) - 1 color-shifting segments
        segmentLength = size.h // (len(imgColors) - 1)

        for columnIdx in range(size.h):
            # We could have a problem here if size.h is not divisible by 6
            # Since then it could happen that (size.h - 1) // segmentLength
            # is len(colors) - 1 which is out of bounds in the next rows
            # E.G. size.h = 7, len(colors) = 3 gives segmentLength = 3,
            # and colorIdx at the end will be 6 // 3 = 2
            colorIdx = columnIdx // segmentLength
            currentColor = imgColors[colorIdx]
            nextColor = imgColors[colorIdx + 1] if colorIdx < len(imgColors) else imgColors[colorIdx]
            pen.line(
                [(columnIdx, 0), (columnIdx, size.v)],
                interpolateColor(
                    currentColor,
                    nextColor,
                    (columnIdx % segmentLength) / segmentLength
                ),
                width=1,
            )

        return coloredTemplate

    if len(colors) == 0:
        imgColor = ImageColor.getrgb(FRAME_COLORS[FrameColors.Colorless])
    elif len(colors) == 1:
        imgColor = ImageColor.getrgb(FRAME_COLORS[colors[0]])
    else:
        # Card has 5 colors
        imgColor = ImageColor.getrgb(FRAME_COLORS[FrameColors.Multicolor])
    
    pen.rectangle(
        ((0, 0), (size.h, size.v)),
        fill=imgColor,
        outline=imgColor,
        width=1,
    )
    return coloredTemplate


def makeColorTemplate(card: LayoutCard) -> Image.Image:
    """
    Creates a template for two-colored card frames,
    with a color shift from the first color to the second.
    If the card is a split card variation, the template is separated in two parts,
    each one colored only with the single face colors.

    This template is used to set the colors in the real frame.
    """
    cardSize = card.layoutData.CARD_SIZE
    coloredTemplate = Image.new("RGB", size=cardSize, color=WHITE)

    if card.layout in [LayoutType.SPL, LayoutType.FUS, LayoutType.AFT]:
        # For split card variants, we create two different half-templates
        # based on the color of each individual face
        # (which are saved in halfImage) and paste them
        # onto the final template

        for face in card.card_faces:
            layoutData = face.layoutData
            rotation = layoutData.ROTATION
            if rotation is not None:
                coloredTemplate = coloredTemplate.transpose(rotation[0])

            size = XY(layoutData.SIZE.CARD.HORIZ, layoutData.SIZE.CARD.VERT)
            halfImage = makeColorTemplateSingleFace(card=face, size=size)
            coloredTemplate.paste(
                halfImage,
                box=(layoutData.BORDER.CARD.LEFT, layoutData.BORDER.CARD.TOP)
            )
            
            if rotation is not None:
                coloredTemplate = coloredTemplate.transpose(rotation[1])
            
        return coloredTemplate
    # Flip does not have multicolored cards, so I'm ignoring it
    # Adventure for now is monocolored or both parts are the same color
    else:
        return makeColorTemplateSingleFace(card=card, size=cardSize)


def makeFrameColored(card: LayoutCard) -> Image.Image:
    """
    Creates the black frame, and colors it by replacing each black pixel
    on the frame with the corresponding one in the colored template.
    """
    frame = makeFrameBlack(card=card)
    coloredTemplate = makeColorTemplate(card=card)
    # The mask parameter uses white to determine where to paste,
    # but since we want to paste on black, we take the negative of the image
    # (after converting it to greyscale)
    # This is significantly faster than checking the pixels one by one
    frame.paste(
        coloredTemplate,
        mask = ImageOps.invert(frame.convert("L"))
    )
    return frame

def makeFrame(card: LayoutCard, isColored: bool) -> Image.Image:
    """
    Creates the structural skeleton of the card, i.e. all the lines
    separating the different sections. This skeleton may be in black
    or colored, using a color gradient like the MTG card box borders.
    """
    if isColored:
        return makeFrameColored(card)
    else:
        return makeFrameBlack(card)
