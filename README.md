# BWProxy

> Grayscale MTG proxy generators 

## What is this?

A program which generates test card-style grayscale proxies for Magic cards. You can cut them out, draw your own art, and sleeve them in front of real cards! 

[Click here for some examples from my fully-proxied illustrated Sai deck.](https://raw.githubusercontent.com/a11ce/bwproxy/main/docs/exampleCards.jpg)

## How to use

BWProxy is offered both via cli and via an executable for Windows and Linux systems.

If something doesn't work, please [open an issue on GitHub](https://github.com/a11ce/bwproxy/issues/new/choose) or message on Discord @a11ce#0027 or @uklusi#7926.

### Download

#### Graphical interface

* Grab the latest release from the [Releases page](https://github.com/a11ce/bwproxy/releases/latest).

#### Command line

* Install [Python](https://www.python.org). The program uses Python 3.7, but it should work with newer Python versions as well.
* Get dependencies with `python3 -m pip install -r requirements-cli.txt`
* Download with `git clone https://github.com/a11ce/bwproxy.git` or via the [Github link](https://github.com/a11ce/bwproxy/releases/latest), under `source code`.

### Write your decklist 

Save your decklist as a .txt in the format `Cardname`, `1 Cardname` or `1x Cardname`, one card per line.

- Empty lines will be ignored;
- You can add comments with `//` and `#`. Every line *starting* with `//` will be ignored, while every character from the `#` until the end of the line will be ignored;
- If the card is a modal or transforming double-faced card, both faces will be printed: you don't need to list both. Meld cards still need to be included separately;
- If you're searching for a flavor name (for example **Godzilla, King of the Monsters**), the flavor name will appear on the title, and the Oracle name will appear under the title;
- Optionally, you can put a custom flavor name in square brackets after a card name. It will appear like the official flavor names. Custom flavor names currently are only supported for standard card frames, meaning that (e.g.) Double-faced, Adventure or Flip cards won't have flavor names even if specified.
- If you want aesthetic consistency (or to play with an all-proxy deck cards), you can also generate basic land cards. They will be printed with a big mana symbol, but there is an option to remove the symbol and leave them as blank full-art lands, useful for testing a deck without sleeving. It's also the best option for customisation!

### Add tokens and emblems

1. Inside your decklist, you can also include tokens and emblems. The format is `(token) Token`, or `(emblem) Planeswalker Name` (ex. `(emblem) Ajani, Adversary of Tyrants`);
1. You can specify a quantity in the same way as the other cards, so for example two **Marit Lage** tokens are written as `2x (token) Marit Lage`;
1. If the token or emblem name is unique in the Scryfall database, all relevant info will be fetched automatically and put in the card;
1. The tokens will have an arched top, to better distinguish them from normal cards, and the emblems will have the Planeswalker symbol on the illustration. The symbol can be disabled with the `--full-art-lands` flag. They will also have their names centered;
1. If the token you are searching is not uniquely identified by its name (or you want some custom token!), you can specify the token info in detail.
    - The format is `(token) Legendary; P/T; colors; Subtypes; Types; text rule 1; text rule 2; ... [Custom Name]`. This should (mostly) respect the order in which the attributes are listed on the token-making card;
    - Spacing around the semicolon does not matter;
    - If a token does not have subtypes or Power/Toughness, or is not Legendary, skip the field;
    - The color should be given as a sequence of official abbreviations: `W` for White, `U` for Blue, `B` for Black, `R` for Red, `G` for Green. Colorless can be either an empty field or `C`;
    - To insert symbols in the token text, enclose the symbol abbreviation in braces: two generic mana is `{2}`, tap is `{T}`, etc;
    - If a token does not have a custom name, the subtypes will be used;
    - Here are some examples:
        - The **Marit Lage** token can be specified as `(token) Legendary; 20/20; B; Avatar; Creature; Flying, indestructible [Marit Lage]`
        - **Tamiyo's Notebook** (from *Tamiyo, Compleated Sage*) can be specified as `(token) Legendary; ; Artifact; Spells you cas cost {2} less to cast; {T}: Draw a card [Tamiyo's Notebook]`
        - An **Inkling** token from *Strixhaven* can be specified as `(token) 2/1;WB;Inkling;Creature;Flying`
        - A **Treasure** token can be specified as `(token) C; Treasure; Artifact; {T}, Sacrifice this artifact: Add one mana of any color`

### Run the program

#### Executable version

Double click on the executable file and follow the instructions on it.

#### Command line version

To run the program, run `python3 bwproxy-cli.py [options] path/to/your/decklist`. The options are listed below:

- Add `--icon-path path/to/your/icon` or `-i path/to/your/icon` to add a set icon. If the argument is not passed to the program, the cards will not have a set icon;
- Add `--page-format [format]` or `-p [format]` to specify the page format. Possible formats are `a4paper` and `letter` (default is `a4paper`);
- Add `--color` or `-c` to print the card borders in color. Colored mana symbols are WIP;
- Add `--no-text-symbols` or `--no-symbols` to have the rules text use the Scryfall text style for mana symbols (`{W}` instead of the white mana symbol, etc);
- Add `--size [size]` or `-s [size]` to choose the card size (default is `standard`). Possibe sizes are:
    - `standard`: the size of a MtG card;
    - `small`: a 75% scaled version of a normal card, useful if you want to print more cards in one page;
    - `playtest`: a 80% width version, like the appearance of the Mystery Booster exclusive cards.
- Add `--no-card-space` or `no-space` to print the cards without blank space between them.
- Add `--full-art-lands` to print basic lands without the big mana symbol, and emblems without the big planeswalker symbol.
- Add `--no-basic-lands` or `no-basics` to ignore basic lands when generating proxies.
- Add `--alternative-frames` to print:
    - Flip cards (the ones from Kamigawa) as if they were double-faced cards;
    - Aftermath cards as if they were split cards;
    - Vanilla tokens and creatures with a full art frame (same as full art lands).
- Add `--no-acorn-stamp` to print silver-border and acorn cards without an acorn symbol near their name.

--- 

Source code is available [here](https://github.com/a11ce/bwproxy). All contributions are welcome by pull request or issue.

Minor version numbers represent (possible) changes to the appearence of generated cards. Patch version numbers represent changes to the functionality of card generation.

BWProxy is licensed under GNU General Public License v3.0. See [LICENSE](https://github.com/a11ce/bwproxy/blob/main/LICENSE) for full text.

All mana and card symbol images are copyright Wizards of the Coast (http://magicthegathering.com).

Mana symbol vector images come from the [Mana Project](http://mana.andrewgioia.com/), licensed under MIT Licence.
