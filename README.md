# figgiebot

Create bots to play the card game Figgie at https://figgie.com/

# Installation

Simply run `pip install figgiebot`. The PyPI package is at https://pypi.org/project/figgiebot/

You will need to install [Chromedriver](https://chromedriver.chromium.org/downloads)

# Dependencies

- **[Python](https://www.python.org/downloads/)** 3.8
- **[Selenium](https://pypi.org/project/selenium/)** >= 4.7.2
- **[beautifulsoup4](https://pypi.org/project/beautifulsoup4/)** >= 4.9.3

# Usage

For an example algorithm look at `example.py`

```python
from figgiebot import Bot

bot = Bot()

# <Bot Code>

bot.run(opponent_count=4)
```

The bot automatically starts new rounds.

### Events
There are 6 event decorators. These are called as events happen in the Figgie game.
The `tick` event is called every client tick (by default this is every 10ms + time to execute orders).
Suits for figgiebot are "s", "c", "d", "h".

```python
@bot.on_bid()
def on_bid(player, value, suit):
    # <write code here>


@bot.on_offer()
def on_offer(player, value, suit):
    # <write code here>


@bot.on_sold()
def on_sold(seller, buyer, value, suit):
    # <write code here>


@bot.on_bought()
def on_bought(buyer, seller, value, suit):
    # <write code here>


@bot.on_tick()
def on_tick():
    # <write code here>


@bot.on_round_start()
def on_round_start():
    # <write code here>
```

### Game Commands

There are 6 game commands. These use selenium action chains to execute so will slow the client tps.

```python
bot.bid(value, suit)

bot.offer(value, suit)

bot.buy(suit)

bot.sell(suit)

bot.cancel_suit_bids_and_offers(suit)

bot.cancel_all_bids_and_offers()
```

### Game Date

The bot maintains the following up-to-date data of the state of the game.

```python
bot.markets  # Dictionary with {"sell_value": 0, "buy_value": 0} for each suit

bot.hand  # e.g. {"s": 0, "c": 0, "d": 0, "h": 0}

bot.time_remaining  # The time remaining in seconds for the game round

bot.name  # The name of the bot in game

bot.opponents  # A list of names of opponents in the game

bot.opponent_chips  # A dictionary of the number of chips each opponent currently has

bot.chips  # The number of chips the bot currently has
```

### Decks

You can also import from figgiebot `figgie_decks` which will be useful for your trading algorithm.

```python
figgie_decks = [
    {"s": 12, "c": 8, "d": 10, "h": 10, "majority": 5, "payoff": 120, "goal": "c"},
    {"s": 12, "c": 10, "d": 10, "h": 8, "majority": 6, "payoff": 100, "goal": "c"},
    {"s": 12, "c": 10, "d": 8, "h": 10, "majority": 6, "payoff": 100, "goal": "c"},
    {"s": 8, "c": 12, "d": 10, "h": 10, "majority": 5, "payoff": 120, "goal": "s"},
    {"s": 10, "c": 12, "d": 10, "h": 8, "majority": 6, "payoff": 100, "goal": "s"},
    {"s": 10, "c": 12, "d": 8, "h": 10, "majority": 6, "payoff": 100, "goal": "s"},
    {"s": 8, "c": 10, "d": 10, "h": 12, "majority": 6, "payoff": 100, "goal": "d"},
    {"s": 10, "c": 8, "d": 10, "h": 12, "majority": 6, "payoff": 100, "goal": "d"},
    {"s": 10, "c": 10, "d": 8, "h": 12, "majority": 5, "payoff": 120, "goal": "d"},
    {"s": 8, "c": 10, "d": 12, "h": 10, "majority": 6, "payoff": 100, "goal": "h"},
    {"s": 10, "c": 8, "d": 12, "h": 10, "majority": 6, "payoff": 100, "goal": "h"},
    {"s": 10, "c": 10, "d": 12, "h": 8, "majority": 5, "payoff": 120, "goal": "h"}
]
```