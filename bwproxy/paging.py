from __future__ import annotations
from typing import List, Tuple
from PIL import Image
from tqdm import tqdm

from .classes import XY, PageFormat # type: ignore
from .dimensions import PAGE_SIZE, SMALL_CARD_RESIZE_FACTOR, CARD_DISTANCE, CARD_DISTANCE_SMALL

def batchSpacing(
    n: int,
    batchSize: Tuple[int, int],
    pageSize: XY,
    cardSize: XY,
    noCardSpace: bool = False,
) -> Tuple[int, int]:
    cardDistance = CARD_DISTANCE_SMALL if noCardSpace else CARD_DISTANCE
    maxH = pageSize[0] - (cardDistance + (cardSize.h + cardDistance) * batchSize[0])
    maxV = pageSize[1] - (cardDistance + (cardSize.v + cardDistance) * batchSize[1])
    return (
        maxH // 2 + cardDistance + (cardSize.h + cardDistance) * (n % batchSize[0]),
        maxH // 2 + cardDistance + (cardSize.v + cardDistance) * (n // batchSize[0]),
    )

def paginate(
    images: List[Image.Image],
    cardSize: XY,
    small: bool = False,
    pageFormat: PageFormat = PageFormat.LETTER,
    noCardSpace: bool = False,
) -> List[Image.Image]:

    pageHoriz = False
    if not small:
        batchSize = (3, 3)
    else:
        batchSize = (4, 4)

    batchNum = batchSize[0] * batchSize[1]

    pageSize = PAGE_SIZE[pageFormat]

    if small:
        cardSize = cardSize.scale(factor=SMALL_CARD_RESIZE_FACTOR)
        images = [image.resize(cardSize) for image in images]

    if pageHoriz:
        pageSize = pageSize.transpose()

    pageList: List[Image.Image] = []
    for k in tqdm(
        range(0, len(images), batchNum),
        desc="Pagination progress: ",
        unit="page",
    ):
        batch = images[k : k + batchNum]
        page = Image.new("RGB", size=pageSize, color="white")
        for i in range(len(batch)):
            page.paste(
                batch[i],
                batchSpacing(
                    i,
                    batchSize=batchSize,
                    pageSize=pageSize,
                    cardSize=cardSize,
                    noCardSpace=noCardSpace,
                ),
            )
        
        pageList.append(page)

    return pageList
