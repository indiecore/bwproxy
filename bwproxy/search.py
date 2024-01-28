from __future__ import annotations
from time import sleep

from typing import List, Optional, Dict, Tuple
from scrython import Search, ScryfallError
from pathlib import Path
from textwrap import dedent
import re
import os
import json

from .classes import LayoutType, ManaColors, JsonDict # type: ignore
from .card_wrapper import Card, LayoutCard
from .other_constants import CARD_TYPES, CARD_SUPERTYPES, BASIC_LANDS, LAYOUT_TYPES_DF




# Cards and Tokens/Emblems have different caches, since there are cards with the same name as tokens
# Notable example: Blood token and Flesh // Blood
CACHE_FOLDER = Path("cardcache")
CACHE_LOC = CACHE_FOLDER / "cardcache.json"
TOKEN_CACHE_LOC = CACHE_FOLDER / "tokencache.json"

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


def searchToken(tokenName: str, tokenType: str = LayoutType.TOK.value) -> list[Card]:
    """
    Searches a token/emblem info based on their name.
    Returns a list of deduplicated tokens corresponding to the name,
    or the empty list if no tokens were found.
    """
    if tokenType == LayoutType.EMB.value:
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
    if len(supertypesList) > 0 and set(supertypesList) <= set(CARD_SUPERTYPES):
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

    colors = [color for color in data.pop(0).upper() if color in ManaColors.values()]

    typesOrSubtypesList = [word.strip().title() for word in data[0].split()]
    maybeTypesList = [word.strip().title() for word in data[1].split()]

    if set(maybeTypesList) <= set(CARD_TYPES) | set(CARD_SUPERTYPES):
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
    alternativeFrames: bool = False,
    usePlaytestSize: bool = False
) -> List[Tuple[LayoutCard, int]]:
    """
    Search the requested cards' data. The requested data can be specified
    via file or via plaintext string
    """

    cardCache: Dict[str, JsonDict]
    tokenCache: Dict[str, JsonDict]

    if os.path.exists(CACHE_LOC):
        with open(CACHE_LOC, "r") as cacheFile:
            try:
                cardCache = json.load(cacheFile)
            except json.JSONDecodeError:
                cardCache = {}
    else:
        cardCache = {}

    if os.path.exists(TOKEN_CACHE_LOC):
        with open(TOKEN_CACHE_LOC, "r") as cacheFile:
            try:
                tokenCache = json.load(cacheFile)
            except json.JSONDecodeError:
                tokenCache = {}
    else:
        tokenCache = {}

    if fileLoc is not None:
        with open(fileLoc) as f:
            requestedCards = f.read()
        
    if requestedCards is None or requestedCards == "":
        raise ValueError("Missing file location and requested cards plaintext info")

    cardsInDeck: List[Tuple[LayoutCard, int]] = []

    # This regex searches for // at the beginning of the line,
    # or for # at any point in the line
    commentsRegex = re.compile(r"^//.*$|#.*$")
    # This regex searches for two or more spaces consecutively
    doubleSpacesRegex = re.compile(r" {2,}")
    # This regex searches for any number of digits at the beginning of the line,
    # Eventually followed by a x.
    # The digits are saved into the first capturing group
    cardCountRegex = re.compile(r"^([0-9]+)x?")
    # This regex searches (case insensitive) for (token) or (emblem) at the beginning
    # Token or Emblem is saved into the first capturing group
    tokenEmblemRegex = re.compile(r"^\((token|emblem)\)", flags=re.I)
    # This regex searches for any section between square brackets
    # This should be the flavor name of the card
    # The flavor name is saved into the first capturing group
    flavorNameRegex = re.compile(r"\[(.*?)\]")

    for origLine in requestedCards.split("\n"):
        line = origLine
        line = commentsRegex.sub("", line)
        line = doubleSpacesRegex.sub(" ", line.strip())

        if line == "":
            continue

        cardCountMatch = cardCountRegex.search(line)
        if cardCountMatch:
            cardCount = int(cardCountMatch.groups()[0])
            line = cardCountRegex.sub("", line).strip()
        else:
            cardCount = 1

        flavorNameMatch = flavorNameRegex.search(line)
        if flavorNameMatch:
            line = flavorNameRegex.sub("", line).strip()

        tokenMatch = tokenEmblemRegex.search(line)
        if tokenMatch:
            line = tokenEmblemRegex.sub("", line).strip()

        if line:
            cardName = line
        else:
            print(f"No card name found in line {origLine}. This line will be skipped.")
            continue

        if ignoreBasicLands and cardName in BASIC_LANDS:
            print(
                f"You have requested to ignore basic lands. {cardName} will not be printed."
            )
            continue
        
        if tokenMatch:
            tokenType = tokenMatch.groups()[0].lower()
            if ";" in cardName:
                # Token is specified in the input, so we need to parse it
                if flavorNameMatch:
                    tokenName = flavorNameMatch.groups()[0]
                else:
                    tokenName = None

                try:
                    tokenData = parseToken(text=cardName, name=tokenName)
                except:
                    print(f"Line '{origLine}' contains a {tokenType}, but the info specified was not formatted correctly.")
                    continue
            # Token is a named token
            elif cardName in tokenCache:
                tokenData = Card(tokenCache[cardName])
            else:
                print(f"{cardName} not in cache. searching...")
                tokenList = searchToken(tokenName=cardName, tokenType=tokenType)
                sleep(0.1)

                if len(tokenList) == 0:
                    print(f"Skipping {cardName}. No corresponding tokens found.")
                    continue
                if len(tokenList) > 1:
                    print(
                        f"Skipping {cardName}. Too many tokens found. Consider specifying the token info in the input file."
                    )
                    continue
                tokenData = tokenList[0]
                print(f"Token {tokenData.name} found!")

            tokenCache[cardName] = tokenData.data
            cardsInDeck.append(
                (
                    LayoutCard(
                        tokenData.data,
                        alternativeFrames,
                        isPlaytest=usePlaytestSize,
                    ),
                    cardCount
                )
            )
            continue

        # Card is not a token

        if flavorNameMatch:
            flavorName = flavorNameMatch.groups()[0]
        else:
            flavorName = None

        if cardName in cardCache:
            cardData = LayoutCard(
                cardCache[cardName],
                alternativeFrames,
                flavorName,
                isPlaytest=usePlaytestSize,
            )
        else:
            print(f"{cardName} not in cache. searching...")
            try:
                cardData = LayoutCard.from_name(
                    cardName,
                    alternativeFrames,
                    flavorName,
                    isPlaytest=usePlaytestSize,
                )
            except ScryfallError as err:
                print(f"Skipping {cardName}. {err}")
                continue
            print(f"Card {cardData.name} found!")

        cardCache[cardName] = cardData.data

        if cardData.layout in LAYOUT_TYPES_DF:
            for face in cardData.card_faces:
                cardsInDeck.append(
                    (face, cardCount)
                )
        else:
            cardsInDeck.append((cardData, cardCount))

    os.makedirs(os.path.dirname(CACHE_LOC), exist_ok=True)
    with open(CACHE_LOC, "w") as cacheFile:
        json.dump(cardCache, cacheFile)

    os.makedirs(os.path.dirname(TOKEN_CACHE_LOC), exist_ok=True)
    with open(TOKEN_CACHE_LOC, "w") as cacheFile:
        json.dump(tokenCache, cacheFile)

    return cardsInDeck