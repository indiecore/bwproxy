from __future__ import annotations
from itertools import repeat
from typing import List
from PIL import Image
from tqdm import tqdm
from pathlib import Path
import os
import argparse

from bwproxy import drawCard, loadCards, paginate, PageFormat, CardSize

def main():
    parser = argparse.ArgumentParser(description="Black and white MTG proxy generator")
    parser.add_argument(
        "decklistPath",
        metavar="decklist_path",
        help="location of decklist file",
    )
    parser.add_argument(
        "--icon-path",
        "-i",
        metavar="icon_path",
        dest="setIconPath",
        help="location of set icon file",
    )
    parser.add_argument(
        "--page-format",
        "-p",
        default=PageFormat.A4.value,
        choices=list(PageFormat.values()),
        dest="pageFormat",
        help="printing page format",
    )
    parser.add_argument(
        "--color",
        "-c",
        action="store_true",
        help="print card frames and mana symbols in color",
    )
    parser.add_argument(
        "--no-symbols",
        "--no-text-symbols",
        action="store_false",
        dest="useTextSymbols",
        help="print cards with e.g. {W} instead of the corresponding symbol",
    )
    parser.add_argument(
        "--size",
        "-s",
        default=CardSize.STANDARD.value,
        choices=list(CardSize.values()),
        dest="cardSize",
        help="the size the card wil be printed at"
    )
    parser.add_argument(
        "--no-space",
        "--no-card-space",
        action="store_true",
        dest="noCardSpace",
        help="print cards without space between them",
    )
    parser.add_argument(
        "--full-art-lands",
        action="store_true",
        dest="fullArtLands",
        help="print full art basic lands instead of big symbol basic lands",
    )
    parser.add_argument(
        "--no-basics",
        "--no-basic-lands",
        action="store_true",
        dest="ignoreBasicLands",
        help="skip basic lands when generating images",
    )
    parser.add_argument(
        "--alternative-frames",
        action="store_true",
        dest="alternativeFrames",
        help="print flip cards as DFC, aftermath as regular split",
    )
    parser.add_argument(
        "--no-acorn-stamp",
        action="store_false",
        dest="useAcornSymbol",
        help="do not print the acorn symbol on silver-border and acorn cards",
    )

    args = parser.parse_args()

    decklistPath = Path(args.decklistPath)
    setIconPath = Path(args.setIconPath) if args.setIconPath is not None else None

    if not decklistPath.exists():
        print(f"The deck list file {args.decklistPath} does not exist, aborting...")
        exit(1)
    if setIconPath is not None and not setIconPath.exists():
        print(f"The icon file {args.setIconPath} does not exist, aborting...")
        exit(1)


    pageFormat = PageFormat(args.pageFormat)

    cardsWithCount = loadCards(
        fileLoc=decklistPath,
        ignoreBasicLands=args.ignoreBasicLands,
        alternativeFrames=args.alternativeFrames,
        usePlaytestSize=args.cardSize == CardSize.PLAYTEST.value
    )
    
    images: List[Image.Image] = []
    for (layoutCard, count) in tqdm(
        cardsWithCount,
        desc="Card drawing progress: ",
        unit="card",
    ):
        image = drawCard(
            card=layoutCard,
            setIconPath=setIconPath,
            isColored=args.color,
            useTextSymbols=args.useTextSymbols,
            fullArtLands=args.fullArtLands,
            useAcornSymbol=args.useAcornSymbol
        )
        images.extend(repeat(image, count))
    
    pages = paginate(
        images=images,
        cardSize=cardsWithCount[0][0].layoutData.CARD_SIZE,
        small=args.cardSize == CardSize.SMALL.value,
        pageFormat=pageFormat,
        noCardSpace=args.noCardSpace,
    )
    
    deckName = decklistPath.stem
    outputFolder = Path(f"output")
    os.makedirs(outputFolder, exist_ok=True)
    pages[0].save(outputFolder / f"{deckName}.pdf", "pdf", save_all=True, append_images=pages[1:])

    exit(0)

if __name__ == '__main__':
    main()
