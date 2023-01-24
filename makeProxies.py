from __future__ import annotations
from typing import List, Tuple, Optional
from scrython import Search, ScryfallError
from PIL import Image
from tqdm import tqdm
from pathlib import Path
from textwrap import dedent
import pickle
import re
import os
import argparse

import bwproxy.drawUtil as drawUtil
import bwproxy.projectConstants as C
from bwproxy.projectTypes import Card, Deck, Flavor


def deduplicateTokenResults(query: str, results: list[Card]) -> list[Card]:
    """
    Removes duplicates from a list of tokens / emblems.
    Considers name, types, colors, rules text and p/t
    when searching for duplicates.
    """
    singleFaces: list[Card] = []
    deduplicatedList: dict[str, Card] = {}
    for card in results:
        # If a token has multiple faces, insert them all
        if card.isTwoParts():
            singleFaces.extend(card.card_faces)
        else:
            singleFaces.append(card)
    for card in singleFaces:
        if (
            # There probably is a reason for replacing commas, but I don't remember it
            query.lower().replace(",", "") in card.name.lower().replace(",", "")
            and card.type_line != "Token"
            and card.type_line != ""
        ):
            index = dedent( f"""\
                {card.name}
                {card.type_line}
                {sorted(c.value for c in card.colors)}
                {card.oracle_text}"""
            )
            # There are multiple tokens which differ only by power/toughness
            # So we have to include this info when deduplicating
            if card.hasPT():
                index += f"\n{card.power}/{card.toughness}"
            deduplicatedList[index] = card

    return list(deduplicatedList.values())


def searchToken(tokenName: str, tokenType: str = C.LayoutType.TOK.value) -> list[Card]:
    """
    Searches a token/emblem info based on their name.
    Returns a list of deduplicated tokens corresponding to the name,
    or the empty list if no tokens were found.
    """
    if tokenType == C.LayoutType.EMB.value:
        exactName = f"{tokenName} Emblem"
    else:
        exactName = tokenName
    try:
        cardQuery = Search(q=f"type:{tokenType} !'{exactName}'")
        results = [Card(cardData) for cardData in cardQuery.data()]  # type: ignore
    except ScryfallError:
        try:
            cardQuery = Search(q=f"type:{tokenType} {tokenName}")
            results = [Card(cardData) for cardData in cardQuery.data()]  # type: ignore
        except ScryfallError:
            results: list[Card] = []
    return deduplicateTokenResults(query=tokenName, results=results)


def parseToken(text: str, name: Optional[str] = None) -> Card:
    """
    Parse token data from input
    """
    # We split the input line into a list,
    # then keep popping the fields one by one
    # in order to manage the optional fields
    data = [line.strip() for line in text.split(";")]

    # Optional field
    supertypesList = [word.strip().title() for word in data[0].split()]
    if len(supertypesList) > 0 and set(supertypesList) <= set(C.CARD_SUPERTYPES):
        supertype = " ".join(supertypesList) + " "
        data.pop(0)
    else:
        supertype = ""

    # Optional field
    if "/" in data[0].lower():
        pt = data[0].split("/")
        power = pt[0]
        toughness = pt[1]
        data.pop(0)
    else:
        power = None
        toughness = None

    colors = [color for color in data.pop(0).upper() if color in C.ManaColors.values()]

    typesOrSubtypesList = [word.strip().title() for word in data[0].split()]
    maybeTypesList = [word.strip().title() for word in data[1].split()]

    if set(maybeTypesList) <= set(C.CARD_TYPES) | set(C.CARD_SUPERTYPES):
        # Since maybeTypesList contains types
        # (and not the next info in the token specification),
        # we can deduce that typesOrSubTypesList contains subtypes
        # We cannot check directly on the subtypes field,
        # since there are too many, they change frequently and
        # I don't want to search for a list

        # We delete subtypes and types from the data
        data.pop(0)
        data.pop(0)

        types = f"{supertype}{' '.join(maybeTypesList)}"
        subtypes = " ".join(typesOrSubtypesList)
        name = name if name else subtypes
        type_line = f"Token {types} — {subtypes}"
    else:
        # Since maybeTypesList does not contain types, the token info contains no subtypes
        # This means that the card types are in typesOrSubtypesList
        data.pop(0)
        type_line = f"Token {supertype}{' '.join(typesOrSubtypesList)}"

    if name is None:
        raise Exception(f"Missing name for token without subtypes: {text}")
        
    jsonData = {
        "type_line": type_line,
        "name": name,
        "colors": colors,
        "mana_cost": "",
    }

    # Creatures and vehicles should have P/T
    if "Creature" in jsonData["type_line"] or "Vehicle" in jsonData["type_line"]:
        try:
            assert power is not None
            assert toughness is not None
            jsonData["power"] = power
            jsonData["toughness"] = toughness
        except:
            raise Exception(f"Power/Toughness missing for token: {name}")
    
    text_lines = [line for line in data if line]
    jsonData["oracle_text"] = "\n".join(text_lines)
    return Card(jsonData)


def loadCards(
    fileLoc: Path | None = None,
    requestedCards: str | None = None,
    ignoreBasicLands: bool = False,
    alternativeFrames: bool = False
) -> tuple[Deck, Flavor]:
    """
    Search the requested cards' data. The requested data can be specified
    via file or via plaintext string
    """

    cardCache: dict[str, Card]
    tokenCache: dict[str, Card]

    if os.path.exists(C.CACHE_LOC):
        with open(C.CACHE_LOC, "rb") as p:
            cardCache = pickle.load(p)
    else:
        cardCache = {}

    if os.path.exists(C.TOKEN_CACHE_LOC):
        with open(C.TOKEN_CACHE_LOC, "rb") as p:
            tokenCache = pickle.load(p)
    else:
        tokenCache = {}

    if fileLoc is not None:
        with open(fileLoc) as f:
            requestedCards = f.read()
        
    if requestedCards is None or requestedCards == "":
        raise ValueError("Missing file location and requested cards plaintext info")

    cardsInDeck: Deck = []
    flavorNames: Flavor = {}

    # This regex searches for // at the beginning of the line,
    # or for # at any point in the line
    removeCommentsRegex = re.compile(r"^//.*$|#.*$")
    # This regex searches for two or more spaces consecutively
    doubleSpacesRegex = re.compile(r" {2,}")
    # This regex searches for any number of digits at the beginning of the line,
    # Eventually followed by a question mark
    # The digits are saved into the first capturing group
    cardCountRegex = re.compile(r"^([0-9]+)x?")
    # This regex searches (case insensitive) for (token) or (emblem) at the beginning
    # Eventually preceded by the card count section
    # Token or Emblem is saved into the first capturing group
    tokenEmblemRegex = re.compile(r"^(?:[0-9]+x? )?\((token|emblem)\)", flags=re.I)
    # This regex searches for any section between square brackets
    # This should be the flavor name of the card
    # The flavor name is saved into the first capturing group
    flavorNameRegex = re.compile(r"\[(.*?)\]")
    # This regex excludes all other sections and saves the remaining info
    # (hopefully the card name) in the first capturing group
    cardNameRegex = re.compile(
        r"^(?:[0-9]+x? )?(?:\((?:token|emblem)\) )?(.*?)(?: \[.*?\])?$", flags=re.I
    )

    for line in requestedCards.split("\n"):
        line = removeCommentsRegex.sub("", line)
        line = doubleSpacesRegex.sub(" ", line.strip())

        if line == "":
            continue

        cardCountMatch = cardCountRegex.search(line)
        cardCount = int(cardCountMatch.groups()[0]) if cardCountMatch else 1

        flavorNameMatch = flavorNameRegex.search(line)
        cardNameMatch = cardNameRegex.search(line)
        tokenMatch = tokenEmblemRegex.search(line)

        if cardNameMatch:
            cardName = cardNameMatch.groups()[0]
        else:
            raise Exception(f"No card name found in line {line}")

        if ignoreBasicLands and cardName in C.BASIC_LANDS:
            print(
                f"You have requested to ignore basic lands. {cardName} will not be printed."
            )
            continue

        if tokenMatch:
            tokenType = tokenMatch.groups()[0].lower()
            if ";" in cardName:
                if flavorNameMatch:
                    tokenName = flavorNameMatch.groups()[0]
                else:
                    tokenName = None
                tokenData = parseToken(text=cardName, name=tokenName)
            elif cardName in tokenCache:
                tokenData = tokenCache[cardName]
            else:
                print(f"{cardName} not in cache. searching...")
                tokenList = searchToken(tokenName=cardName, tokenType=tokenType)

                if len(tokenList) == 0:
                    print(f"Skipping {cardName}. No corresponding tokens found")
                    continue
                if len(tokenList) > 1:
                    print(
                        f"Skipping {cardName}. Too many tokens found. Consider specifying the token info in the input file"
                    )
                    continue
                tokenData = tokenList[0]

            tokenCache[cardName] = tokenData
            for _ in range(cardCount):
                cardsInDeck.append(tokenData)
            continue

        if cardName in cardCache:
            cardData = Card(cardCache[cardName])
            cardCache[cardName] = cardData
        else:
            print(f"{cardName} not in cache. searching...")
            try:
                cardData: Card = Card.from_name(cardName)
            except ScryfallError as err:
                print(f"Skipping {cardName}. {err}")
                continue

            print(f"Card found! {cardData.name}")
            cardCache[cardName] = cardData

        if ignoreBasicLands and cardData.name in C.BASIC_LANDS:
            print(
                f"You have requested to ignore basic lands. {cardName} will not be printed."
            )
            continue

        if cardData.hasFlavorName():
            flavorNames[cardData.name] = cardData.flavor_name

        if flavorNameMatch:
            flavorName = flavorNameMatch.groups()[0]
            flavorNames[cardData.name] = flavorName

        if (
            cardData.layout in C.LAYOUT_TYPES_DF or (
                cardData.layout == C.LayoutType.FLP and alternativeFrames
            )
        ):
            facesData = cardData.card_faces
            for _ in range(cardCount):
                cardsInDeck.append(facesData[0])
                cardsInDeck.append(facesData[1])
        else:
            for _ in range(cardCount):
                cardsInDeck.append(cardData)

    os.makedirs(os.path.dirname(C.CACHE_LOC), exist_ok=True)
    with open(C.CACHE_LOC, "wb") as p:
        pickle.dump(cardCache, p)

    os.makedirs(os.path.dirname(C.TOKEN_CACHE_LOC), exist_ok=True)
    with open(C.TOKEN_CACHE_LOC, "wb") as p:
        pickle.dump(tokenCache, p)

    return (cardsInDeck, flavorNames)

# Paging


def batchSpacing(
    n: int,
    batchSize: Tuple[int, int],
    pageSize: C.XY,
    cardSize: C.XY,
    noCardSpace: bool = False,
) -> Tuple[int, int]:
    cardDistance = 1 if noCardSpace else C.CARD_DISTANCE
    maxH = pageSize[0] - (cardDistance + (cardSize.h + cardDistance) * batchSize[0])
    maxV = pageSize[1] - (cardDistance + (cardSize.v + cardDistance) * batchSize[1])
    return (
        maxH // 2 + cardDistance + (cardSize.h + cardDistance) * (n % batchSize[0]),
        maxV // 2 + cardDistance + (cardSize.v + cardDistance) * (n // batchSize[0]),
    )


def savePages(
    images: List[Image.Image],
    deckName: str,
    small: bool = False,
    pageFormat: C.PageFormat = C.PageFormat.A4,
    noCardSpace: bool = False,
) -> None:
    outputFolder = Path(f"output/{deckName}/")
    os.makedirs(outputFolder, exist_ok=True)
    pageHoriz = False
    cardSize = C.CARD_SIZE
    if not small:
        batchSize = (3, 3)
    else:
        batchSize = (4, 4)

    batchNum = batchSize[0] * batchSize[1]

    pageSize = C.PAGE_SIZE[pageFormat]

    if small:
        cardSize = C.SMALL_CARD_SIZE
        images = [image.resize(cardSize) for image in images]

    if pageHoriz:
        pageSize = pageSize.transpose()

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

        page.save(outputFolder / f"{k // batchNum + 1:02}.png", "PNG")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate printable MTG proxies")
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
        default=C.PageFormat.A4,
        choices=C.PageFormat,
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
        "--no-text-symbols",
        action="store_false",
        dest="useTextSymbols",
        help="print cards with e.g. {W} instead of the corresponding symbol",
    )
    parser.add_argument(
        "--small",
        "-s",
        action="store_true",
        help="print cards at 75%% in size, allowing to fit more in one page",
    )
    parser.add_argument(
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
        "--ignore-basic-lands",
        "--ignore-basics",
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
        help="do not print the acorn symbol on non tournament legal cards",
    )

    args = parser.parse_args()

    decklistPath = Path(args.decklistPath)

    if args.setIconPath:
        setIcon = drawUtil.resizeSetIcon(Image.open(args.setIconPath).convert("RGBA"))
    else:
        setIcon = None

    (allCards, flavorNames) = loadCards(
        fileLoc=decklistPath,
        ignoreBasicLands=args.ignoreBasicLands,
        alternativeFrames=args.alternativeFrames,
    )
    
    images = [
        drawUtil.drawCard(
            card=card,
            setIcon=setIcon,
            flavorNames=flavorNames,
            isColored=args.color,
            useTextSymbols=args.useTextSymbols,
            fullArtLands=args.fullArtLands,
            alternativeFrames=args.alternativeFrames,
            useAcornSymbol=args.useAcornSymbol
        ) for card in tqdm(
            allCards,
            desc="Card drawing progress: ",
            unit="card",
        )
    ]
    
    savePages(
        images=images,
        deckName=decklistPath.stem,
        small=args.small,
        pageFormat=args.pageFormat,
        noCardSpace=args.noCardSpace,
    )
