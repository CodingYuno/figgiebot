from figgiebot import Bot, figgie_decks
from math import comb, floor, ceil
from random import uniform

bot = Bot()


class CardOwnership:
    """ Tracks ownership of cards across players for a suit"""
    def __init__(self, starting: int):
        self.players = {player: 0 for player in bot.opponents}
        self.players[bot.name] = starting

    def trade(self, buyer: str, seller: str) -> None:
        """ Card movements tracked by trades """
        if self.players[seller] == 0:
            self.players[buyer] += 1
        else:
            self.players[buyer] += 1
            self.players[seller] -= 1

    def if_less_set(self, player: str, value: int) -> None:
        """ Set a players card count to a value if the value is below previous value """
        if self.players[player] < value:
            self.players[player] = value


class Deck:
    """ Tracks state of the card deck """
    def __init__(self):
        self.deck = {suit: CardOwnership(start_count) for suit, start_count in bot.hand.items()}

    def __getitem__(self, suit: str) -> CardOwnership:
        return self.deck[suit]

    def card_count(self, suit: str) -> int:
        """ The total number of cards known for the suit """
        return sum(self.deck[suit].players.values())

    def deck_combinations(self, s: int, c: int, d: int, h: int) -> int:
        """ Given a deck `s, c, d, h` from the 12 possible decks return the number of combinations that can form it """
        s_combinations = comb(s, self.card_count("s"))
        c_combinations = comb(c, self.card_count("c"))
        d_combinations = comb(d, self.card_count("d"))
        h_combinations = comb(h, self.card_count("h"))
        return s_combinations * c_combinations * d_combinations * h_combinations

    @property
    def multinomial_distribution(self) -> list:
        """ Probabilities that the deck being played is each of the 12 possible decks """
        total_combinations = [self.deck_combinations(s=pos_decks["s"], c=pos_decks["c"], d=pos_decks["d"], h=pos_decks["h"]) for pos_decks in figgie_decks]
        return [x / sum(total_combinations) for x in total_combinations]

    def expected_buy_value(self, suit: str, majority_constant: float = 1.1, own_count: int = None) -> float:
        assert majority_constant > 1

        def majority_value(pos_deck_index: int) -> float:
            """ Portion of card value that is dependent on how close to majority the bot is for the suit """
            if own_count < figgie_decks[pos_deck_index]["majority"]:
                # As we get closer to having a majority of the goal suit the more cards of the goal suit are worth to us
                return ((figgie_decks[pos_deck_index]["payoff"] * (1 - majority_constant)) / (1 - (majority_constant ** figgie_decks[pos_deck_index]["majority"]))) * (majority_constant ** own_count)
            else:
                return 0  # Already have a majority so the card is worth only 10

        def value(pos_deck_index: int) -> float:
            """ The value of the card to the player """
            if figgie_decks[pos_deck_index]["goal"] == suit:
                return 10 + majority_value(pos_deck_index)  # Card is from the goal suit so is worth 10 + a value that is dependent on how close to majority the bot is
            else:
                return 0  # Card is not from the goal suit

        own_count = self.deck[suit].players[bot.name] if own_count is None else own_count
        return sum([self.multinomial_distribution[pos_deck_index] * value(pos_deck_index) for pos_deck_index in range(12)])

    def expected_sell_value(self, suit: str, majority_constant: float = 1.1) -> float:
        assert majority_constant > 1

        # Uses the expected_buy function as its value is based on if the player has one less of the suit
        return self.expected_buy_value(suit=suit, own_count=self.deck[suit].players[bot.name] - 1, majority_constant=majority_constant)

    def bid_assumptions(self, suit: str, player: str, value: int) -> None:
        """ Some simple assumptions on cards players are likely to have based on bids """
        if player != bot.name:  # We accurately know our own cards
            if value >= 20:  # If player bid over 20 for a card we assume they already have at least 3 of the suit
                self.deck[suit].if_less_set(player, 3)
            elif value >= 15:  # If player bid over 15 for a card we assume they already have at least 2 of the suit
                self.deck[suit].if_less_set(player, 2)
            elif value >= 12:  # If player bid over 12 for a card we assume they already have at least 1 of the suit
                self.deck[suit].if_less_set(player, 1)

    @property
    def card_counts(self) -> dict:
        """ For Logging """
        return {suit: sum(self.deck[suit].players.values()) for suit in self.deck}

    @property
    def deck_probabilities(self) -> dict:
        """ For Logging """
        md = self.multinomial_distribution
        return {"s": sum([md[3], md[4], md[5]]) * 100, "c": sum([md[0], md[1], md[2]]) * 100,
                "d": sum([md[6], md[7], md[8]]) * 100, "h": sum([md[9], md[10], md[11]]) * 100}


@bot.on_bid()
def on_bid(player, value, suit):
    deck.bid_assumptions(suit, player, value)


@bot.on_offer()
def on_offer(player, value, suit):
    if player != bot.name:  # The game prevents users from placing offers they are unable to fulfil
        deck[suit].if_less_set(player, 1)


@bot.on_sold()
def on_sold(seller, buyer, value, suit):
    deck.bid_assumptions(suit, buyer, value)
    # Once the bid assumption above is handled we can handle the trade
    deck[suit].trade(buyer=buyer, seller=seller)


@bot.on_bought()
def on_bought(buyer, seller, value, suit):
    deck.bid_assumptions(suit, buyer, value)
    # Once the bid assumption above is handled we can handle the trade
    deck[suit].trade(buyer=buyer, seller=seller)


@bot.on_tick()
def on_tick():
    print(f"Chips: {bot.chips}, Count Used To Predict: {sum(deck.card_counts.values())}, Cards: {deck.card_counts}, Deck Probabilities: {deck.deck_probabilities}")

    for suit, values in bot.markets.items():
        expected_buy_value = deck.expected_buy_value(suit=suit, majority_constant=1.1)
        eb = floor(uniform(0, expected_buy_value))  # We bid between 0 and our buy value
        bot.bid(value=min(eb, values["buy_value"]), suit=suit)
        if bot.hand[suit]:
            expected_sell_value = deck.expected_sell_value(suit=suit, majority_constant=1.1)
            es = ceil(uniform(expected_sell_value, (1 + (2 * (bot.time_remaining / 240))) * expected_sell_value))  # As the game goes on we place offers closer to our sell value
            bot.offer(value=max(es, values["sell_value"]), suit=suit)


@bot.on_round_start()
def on_round_start():
    global deck
    deck = Deck()


bot.run(opponent_count=4)
