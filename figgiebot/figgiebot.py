import re

from time import sleep
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions
from selenium.webdriver.common.action_chains import ActionChains


class Bot:
    def __init__(self):
        options = webdriver.ChromeOptions()
        options.add_argument(f"--window-size=1920,1080")
        self.driver = webdriver.Chrome(executable_path="chromedriver.exe", options=options)
        self.notifications = []
        self.markets = {"s": {}, "c": {}, "d": {}, "h": {}}
        self.hand = {"s": 0, "c": 0, "d": 0, "h": 0}
        self.time_remaining = 242
        self.name = None
        self.opponents = []
        self.loop_delay = 0.01
        self.event_listener = {"sold": [], "at": [], "bid": [], "bought": [], "tick": [], "round_start": []}
        self.opponent_chips = {}
        self.chips = 0
        self.round_started = False

    def bid(self, value: int, suit: str) -> None:
        """ Place Bid """
        self.send_escape()
        self.send_command(f"{value}b{suit}")

    def offer(self, value: int, suit: str) -> None:
        """ Make Offer """
        self.send_escape()
        self.send_command(f"{suit}a{value}")

    def buy(self, suit: str) -> None:
        """ Buy Card """
        self.send_escape()
        self.send_command(f"{suit}ff")

    def sell(self, suit: str) -> None:
        """ Sell Card """
        self.send_escape()
        self.send_command(f"{suit}aa")

    def cancel_suit_bids_and_offers(self, suit: str) -> None:
        """ Selenium action chains for cancelling suit (Pressing ALT)"""
        actions = ActionChains(self.driver)
        actions.send_keys(suit)
        actions.perform()
        actions = ActionChains(self.driver)
        actions.key_down(Keys.ALT).send_keys("x")
        actions.perform()
        actions = ActionChains(self.driver)
        actions.key_up(Keys.ALT).send_keys("x")
        actions.perform()

    def cancel_all_bids_and_offers(self) -> None:
        """ Selenium action chains for cancelling all (Pressing ALT)"""
        actions = ActionChains(self.driver)
        actions.key_down(Keys.ALT).send_keys("c")
        actions.perform()

    @staticmethod
    def convert_time(time_remaining: str) -> int:
        """ Converts figgie game time to seconds """
        min, sec = time_remaining.split(":")
        return 60 * int(min) + int(sec)

    def on_sold(self):
        """ Decorate functions that will be called on any sale event """
        def wrapper(func):
            self.event_listener["sold"].append(func)
            return func
        return wrapper

    def on_offer(self):
        """ Decorate functions that will be called on any offer event """
        def wrapper(func):
            self.event_listener["at"].append(func)
            return func
        return wrapper

    def on_bid(self):
        """ Decorate functions that will be called on any bid event """
        def wrapper(func):
            self.event_listener["bid"].append(func)
            return func
        return wrapper

    def on_bought(self):
        """ Decorate functions that will be called on any buy event """
        def wrapper(func):
            self.event_listener["bought"].append(func)
            return func
        return wrapper

    def on_tick(self):
        """ Decorate functions that will be called every bot tick """
        def wrapper(func):
            self.event_listener["tick"].append(func)
            return func
        return wrapper

    def on_round_start(self):
        """ Decorate functions that will be called when the round starts """
        def wrapper(func):
            self.event_listener["round_start"].append(func)
            return func
        return wrapper

    def play(self):
        while True:
            # A combination of beautiful soup and regex is used for parsing game state
            soup = BeautifulSoup(self.driver.page_source, 'html.parser')

            previous_len = len(self.notifications)  # Used to trace new notifications
            self.notifications = re.findall("<li class=\"order \">.+?</li>|<li class=\"trade \">.+?</li>", self.driver.page_source)

            # Offers
            user_orders = soup.find_all("div", {"class": "low-offer"})
            if user_orders:
                for index, suit in enumerate(self.markets):
                    result = re.findall("user-order ([\w-]+)\">.+?label\">([\w-]+)<|low-offer\">([\w]+)<", str(user_orders[index]))
                    if result:  # An offer has been placed by a player
                        if result[0][0]:
                            self.markets[suit]["buy_value"] = int(result[0][1])  # You
                        else:
                            self.markets[suit]["buy_value"] = int(result[0][2])  # Another player
                    else:
                        self.markets[suit]["buy_value"] = 0  # No current offer

            # Bids
            user_orders = soup.find_all("div", {"class": "high-bid"})
            if user_orders:
                for index, suit in enumerate(self.markets):
                    result = re.findall("user-order ([\w-]+)\">.+?label\">([\w-]+)<|high-bid\">([\w]+)<", str(user_orders[index]))
                    if result:  # A bid has been placed by a player
                        if result[0][0]:
                            self.markets[suit]["sell_value"] = int(result[0][1])  # You
                        else:
                            self.markets[suit]["sell_value"] = int(result[0][2])  # Another player
                    else:
                        self.markets[suit]["sell_value"] = 0  # No current bid

            # Round Time
            time_remaining = soup.find_all("div", {"class": "clock"})
            self.time_remaining = self.convert_time(time_remaining[0].text) if time_remaining else 242

            # Your name
            bot_name = soup.find_all("div", {"class": "right-container"})
            self.name = bot_name[0].text if bot_name else None

            # Opponents Names
            self.opponents = re.findall("\">([\w-]+)</p>", str(soup.find_all("div", {"class": "username"})))

            # Your hand
            hand = [int(card.text) for card in soup.find_all("div", {"class": "card-count"})]
            self.hand = {"s": hand[0], "c": hand[1], "d": hand[2], "h": hand[3]} if hand else self.hand

            # Opponents chip counts
            players = [player.text for player in soup.find_all("div", {"class": "card-backs-view"})]
            self.opponent_chips = {name: 0 for name in self.opponents}
            for player in players:
                for opponent in self.opponents:
                    if opponent in player:
                        chips = player.split(opponent)[1]
                        self.opponent_chips[opponent] = int(chips)

            # Your chip count
            chips = soup.find_all("div", {"class": "aside-right-container"})
            if len(chips) > 1:
                self.chips = int(chips[1].text)

            if self.notifications:
                if not self.round_started and self.time_remaining != 0:
                    # Start bot at first notification
                    for func in self.event_listener["round_start"]:
                        func()  # Call decorated function (round start)
                    self.round_started = True
                if self.round_started:
                    sliced_notifications = self.notifications[:-previous_len] if previous_len != 0 else self.notifications  # New notifications only
                    for notification in reversed(sliced_notifications):
                        if "sold " in notification:  # Must be resolved first as it conflicts
                            args = re.findall("class=\"trade.+?\">([\w-]+)</span><span>sold ([\w-]+).+?>.+?to .+?\">([\w-]+).+?at ([\w-]+)<", notification)[0]
                            for func in self.event_listener["sold"]:
                                func(args[0], args[2], int(args[3]), args[1][0].lower())  # Call decorated functions
                        elif "at " in notification:
                            args = re.findall("\">([\w-]+): </span><span class=\"action\"><span><span>([\w ]+).+?at ([\w]+)<", notification)[0]
                            for func in self.event_listener["at"]:
                                func(args[0] if args[0] != "You" else self.name, int(args[2]), args[1][0].lower())  # Call decorated functions
                        elif " bid " in notification:
                            args = re.findall("\">([\w-]+): </span><span class=\"action\"><span><span>([\w-]+) bid ([\w-]+)<", notification)[0]
                            for func in self.event_listener["bid"]:
                                func(args[0] if args[0] != "You" else self.name, int(args[1]), args[2][0].lower())  # Call decorated functions
                        elif "bought " in notification:
                            args = re.findall("class=\"trade.+?\">([\w-]+)</span><span>bought ([\w-]+).+?>.+?from .+?\">([\w-]+).+?for ([\w-]+)<", notification)[0]
                            for func in self.event_listener["bought"]:
                                func(args[0], args[2], int(args[3]), args[1][0].lower())  # Call decorated functions

            if self.round_started:
                for func in self.event_listener["tick"]:
                    func()  # Call decorated function (tick)

            if self.time_remaining == 0 and self.round_started:
                # Round is over
                self.notifications = []
                self.markets = {"s": {"sell_value": 0, "buy_value": 0}, "c": {"sell_value": 0, "buy_value": 0}, "d": {"sell_value": 0, "buy_value": 0}, "h": {"sell_value": 0, "buy_value": 0}}
                self.hand = {"s": 0, "c": 0, "d": 0, "h": 0}
                self.time_remaining = 242
                self.name = None
                self.opponents = []
                self.opponent_chips = {}
                self.chips = 0
                self.round_started = False
                sleep(5)  # Wait time before starting next round
                self.click_element(method=By.XPATH, identifier="/html/body/div/div/main/div/div[2]/section[2]/div[2]/div[1]/button[2]/div", timeout=5)
            sleep(self.loop_delay)

    def run(self, opponent_count: int) -> None:
        """ Start a game  """
        assert opponent_count in [3, 4]  # Games must have 4 or 5 players
        self.driver.get("https://europe.figgie.com/")
        self.click_element(method=By.CLASS_NAME, identifier="play-button", timeout=5)
        self.click_element(method=By.CLASS_NAME, identifier="button-wrapper", timeout=5)
        self.click_element(method=By.CLASS_NAME, identifier="footer-container", timeout=5)
        for _ in range(opponent_count):  # Add bots
            self.click_element(method=By.XPATH, identifier="/html/body/div/div/main/div/div[3]/button[1]/div", timeout=5)
        self.click_element(method=By.XPATH, identifier="/html/body/div/div/main/div/div[2]/section[3]/div/div[2]/button", timeout=5)
        self.click_element(method=By.XPATH, identifier="/html/body/div/div/main/div/div[2]/section[2]/div[2]/div/div/button", timeout=5)
        self.play()

    def click_element(self, method: By, identifier: str, timeout: int = 20) -> None:
        WebDriverWait(self.driver, timeout).until(expected_conditions.element_to_be_clickable((method, identifier))).click()

    def send_escape(self) -> None:
        """ Cancel current command (preparation for next command) """
        actions = ActionChains(self.driver)
        actions.send_keys(Keys.ESCAPE)
        actions.perform()

    def send_command(self, command: str) -> None:
        """ Send command to game """
        self.send_escape()
        actions = ActionChains(self.driver)
        actions.send_keys(command + Keys.ENTER)
        actions.perform()


# The 12 possible figgie decks (Will be useful!)
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
