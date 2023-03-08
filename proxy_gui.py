from __future__ import annotations
from itertools import repeat
from typing import List
from PIL import Image
from tqdm import tqdm
from pathlib import Path
import os
from gooey import Gooey, GooeyParser # type: ignore
import argparse

from bwproxy import drawCard, loadCards, paginate, PageFormat, CardSize

@Gooey(
    show_restart_button=False,
    program_name="BWProxy",
) # type: ignore
def main():
    parser: argparse.ArgumentParser = GooeyParser(
        prog="BWProxy",
        description="Black and white MTG proxy generator",
    )
    parser.add_argument(
        "decklistPath",
        metavar="Decklist File",
        help="The location of the decklist file",
        widget="FileChooser",
    )
    optional = parser.add_argument_group(
        "Optional Arguments"
    )
    optional.add_argument(
        "--icon-path",
        "-i",
        metavar="Icon Path",
        dest="setIconPath",
        help="The location of the icon file, if desired",
        widget="FileChooser"
    )
    optional.add_argument(
        "--page-format",
        "-p",
        default=PageFormat.A4.value,
        choices=list(PageFormat.values()),
        dest="pageFormat",
        metavar="Page Format",
        help="The desired page size for printing",
    )
    optional.add_argument(
        "--color",
        "-c",
        action="store_true",
        metavar="Colored Proxies",
        help="Print card frames in color",
    )
    optional.add_argument(
        "--use-text-symbols",
        default=True,
        action="store_true",
        dest="useTextSymbols",
        metavar="Use Symbols",
        help="Replace plaintext text (e.g. {W}) with the corresponding symbol",
    )
    optional.add_argument(
        "--size",
        "-s",
        default=CardSize.STANDARD.value,
        choices=list(CardSize.values()),
        dest="cardSize",
        metavar="Card Size",
        help="Small is 75% scaled, playtest is narrower, like a Mistery Booster card",
    )
    optional.add_argument(
        "--no-card-space",
        action="store_true",
        dest="noCardSpace",
        metavar="Remove Card Space",
        help="Remove the tolerance space between the cards",
    )
    optional.add_argument(
        "--full-art-lands",
        action="store_true",
        dest="fullArtLands",
        metavar="Full Art Lands",
        help="Remove the big symbol from basic lands and emblems",
    )
    optional.add_argument(
        "--ignore-basic-lands",
        "--ignore-basics",
        action="store_true",
        dest="ignoreBasicLands",
        metavar="Ignore Basic Lands",
        help="Skip basic lands when generating images",
    )
    optional.add_argument(
        "--alternative-frames",
        action="store_true",
        dest="alternativeFrames",
        metavar="Alternative Frames",
        help="Print some cards with different frames. Consult the README to learn more"
        # help="print flip cards as DFC, aftermath as regular split",
    )
    optional.add_argument(
        "--no-acorn-stamp",
        action="store_true",
        default=True,
        dest="useAcornSymbol",
        metavar="Print Acorn Marker",
        help="Print the acorn symbol on non tournament legal cards",
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
        usePlaytestSize=args.cardSize == CardSize.PLAYTEST.value,
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
