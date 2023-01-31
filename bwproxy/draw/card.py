from typing import Optional # type: ignore
from PIL import Image
from pathlib import Path

from ..card_wrapper import LayoutCard
from .frame import makeFrame
from .icon import getIcon, pasteIcon
from .text import drawText

def drawCard(
    card: LayoutCard,
    isColored: bool = False,
    setIconPath: Optional[Path] = None,
    useTextSymbols: bool = True,
    fullArtLands: bool = False,
    useAcornSymbol: bool = True,
) -> Image.Image:
    """
    Takes card info and external parameters, producing a complete image.
    """

    image = makeFrame(card=card, isColored=isColored)
    icon = getIcon(iconPath=setIconPath)
    if icon is not None:
        image = pasteIcon(card=card, image=image, icon=icon)
    image = drawText(
        card=card,
        image=image,
        useTextSymbols=useTextSymbols,
        fullArtLands=fullArtLands,
        hasSetIcon=icon is not None,
        useAcornSymbol=useAcornSymbol,
    )

    return image
