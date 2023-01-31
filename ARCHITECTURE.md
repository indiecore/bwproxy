# BWProxy architecture

The proxy generator works in 5 phases:

1. Parse the input list;
2. Search Scryfall for the cards requested or collect the info from the input (in case of tokens);
3. Draw the card frame, using colors if requested;
4. Draw the card text (name, cost, rules text...);
5. Paginate the results and save them to a file.

The main file, `makeProxies.py`, works on phases 1, 2, and 5,
while phases 3 and 4 are managed by `bwproxy/drawUtil.py`.

The card JSON data retrieved from Scryfall is wrapped almost untouched in a Card class, providing easier access to the card info.
Additional layout informations, like whether or not to print the card with a different name, are saved in a LayoutCard class (inheriting from Card).
These two classes can be found in `projectTypes.py`.

## Input list and card search

The input list is parsed using regex in order to identify card numbers, token data and custom names.

The cards are saved in a `pickle` file cache for reuse. Tokens have a different cache, since tokens may have the same name of cards (see Blood tokens).
If the cards are not in cache, the program queries Scryfall using the `card/named` api in fuzzy mode, skipping cards when appropriate.

For tokens there are two paths: one is querying Scryfall, using the `card/search` api, and the other is specifying the token info directly in the input.

When querying Scryfall the data needs cleaning: some tokens are only on one face of a double faced token, while others may have two versions with the same name but different stats.

When reading the token data from input we assume it follows the specification from the readme file.
If this is false we print an error to the user and continue to the next card.

## Drawing cards

Different card (mainly two-in-one cards) need to be printed with different layouts in order to convey how the card works.
All the layout data (card positioning, rotation, section sizes...) is saved inside a dictionary mapping layout types to layout data, so that changes to the card appearance can almost always be made modifying the values in this dictionary. These valuese can be found in `projectConstants.py`.

When creating the layout, we start with all the structural lines, drawn using black rectangles.
If colored frames were requested, we create a full color image (possibly with a color gradient), and we select the points corresponding to the black lines.
We use this approach in order to simulate lines with a color gradient for multicolor cards.

The set icon, if present, is also pasted on the appropriate place.

After the structure we then proceed to write the text components.
There are three main helper functions: one to determine the ascendant position in order to center the text (for one line text), and two to determine the text size (one for one line text and another for multiline text).
Each text section gets its own function, in order to better showcase the logic and what each part is supposed to do.

