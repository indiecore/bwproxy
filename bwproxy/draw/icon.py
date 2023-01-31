from PIL import Image
from typing import Dict, Optional, overload
from pathlib import Path

from ..classes import XY, LayoutType
from ..dimensions import DRAW_SIZE
from ..card_wrapper import LayoutCard

@overload
def getIcon(iconPath: Path) -> Image.Image:
    ...
@overload
def getIcon(iconPath: None) -> None:
    ...

_icon_cache: Dict[Path, Image.Image] = {}
def getIcon(iconPath: Optional[Path]) -> Optional[Image.Image]:
    """
    The set icon passed to the program can (and probably will)
    be of a different size than needed.
    
    This function will resize the icon such that it fits in a square
    of dimensions ICON_SIZE × ICON_SIZE.
    """
    if iconPath is None:
        return None
    if iconPath in _icon_cache:
        return _icon_cache[iconPath]
    icon = Image.open(iconPath).convert("RGBA")
    iconSize = XY(*icon.size)
    scaleFactor = min(DRAW_SIZE.ICON / iconSize.h, DRAW_SIZE.ICON / iconSize.v)
    icon = icon.resize(
        size = iconSize.scale(scaleFactor).tuple()
    )
    _icon_cache[iconPath] = icon
    return icon


def calcIconPosition(icon: Image.Image, center: XY) -> XY:
    """
    Since we know the center of the icon,
    we need to shift it by the icon size in order to find
    the top left vertex (the only parameter that Image.paste will accept).

    We cannot store the icon top left, since it depends on the icon size
    (which is not fixed).
    """
    iconSize: XY = XY(*icon.size)
    return (center - iconSize.scale(0.5))


def pasteIcon(
    card: LayoutCard,
    image: Image.Image,
    icon: Image.Image,
) -> Image.Image:
    """
    Given a card and a set icon image, pastes the icon on the correct place(s) of the card
    """

    for face in card.card_faces:

        # Adventures have no set icon
        if face.layout == LayoutType.ADV and face.face_num == 1:
            continue
        
        layoutData = face.layoutData

        rotation = layoutData.ROTATION
        if rotation is not None:
            image = image.transpose(rotation[0])

        center = layoutData.ICON_CENTER

        image.paste(
            im=icon,
            box=calcIconPosition(icon=icon, center=center).tuple(),
            mask=icon
        )

        if rotation is not None:
            image = image.transpose(rotation[1])

    return image
