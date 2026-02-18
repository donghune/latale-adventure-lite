import copy
import math
import random

from .data import card_info, stage


class Board:
    def __init__(self):
        self.score = 1
        self.reward = 0
        self.dice_use = 0
        self.is_double = False
        self.cards = []
        self.ex_scores = [0] * 6
        self.ex_values = {
            'min': [0] * 6,
            'max': [0] * 6,
            'std': [0] * 6,
            'mid': [0] * 6,
        }
        self.ex_score = float('inf')
        self.ex_action = None
        self.auto_process = False
        self.rank_reg = False
        self.card_index = list(range(len(card_info)))
        self.card_info = copy.deepcopy(card_info)
        self.card_info_scroll_offset = 0

    def reset_card_info(self):
        self.card_index = list(range(len(card_info)))
        self.card_info = copy.deepcopy(card_info)

    def get_random(self):
        val1 = random.randint(1, 6)
        val2 = random.randint(1, 6)
        if self.is_double or not self.auto_process:
            self.is_double = False
        else:
            self.is_double = val1 == val2
            self.dice_use += 1
        return val1 + val2

    def get_card(self, index=None, push_yn=True):
        if index is None:
            if not self.auto_process:
                return
            rnd = random.randint(0, len(self.card_index) - 1)
            index = self.card_index[rnd]
        else:
            if self.auto_process:
                return
            self.rank_reg = True
            rnd = self.card_index.index(index)

        if self.card_info[index][3] == 0:
            self.card_index.pop(rnd)

        row = self.card_info[index]
        row[3] = 1

        if len(self.cards) < 5 and push_yn:
            self.cards.append(row)

        if len(self.card_index) == 0:
            self.reset_card_info()

    def update_score(self, value, stop=False):
        if stop:
            value = self.check_stop(value)
        self.score = min(2898, self.score + value)
        self.check_event()

    def check_stop(self, value):
        start_index = self.score
        end_index = min(2897, self.score + value - 1)
        for i in range(start_index, end_index):
            if stage[i][5] == 6 or stage[i][5] == 9:
                value = i - self.score + 1
                break
        return value

    def check_event(self):
        event_type = stage[self.score - 1][5]
        if event_type == 2:
            self.get_card()
        elif event_type == 4:
            self.update_score(stage[self.score - 1][4], False)

    def step(self, n):
        if self.dice_use >= 100 and not self.is_double:
            return True
        if n == 0:
            self.update_score(self.get_random(), True)
        else:
            self.use_card(n)
        return self.dice_use >= 100 and not self.is_double

    def use_card(self, n):
        if n > len(self.cards):
            return
        n -= 1
        card_type = self.cards[n][1]
        card_value = self.cards[n][2]
        self.cards.pop(n)

        if card_type == 1:
            self.update_score(card_value, False)
        elif card_type == 2:
            self.update_score(self.get_random() * card_value, False)
        elif card_type == 3:
            value = stage[self.score - 1][1] + card_value
            for i in range(self.score, len(stage) - 1):
                if stage[i][1] == value:
                    value = i - self.score + 1
                    break
            self.update_score(value, False)

    def move_stage(self, v):
        value = max(1, min(75, stage[self.score - 1][1] + v))
        score = self.score
        for i in range(len(stage) - 1):
            if stage[i][1] == value and stage[i][2] == 1:
                score = i - self.score + 1
                break
        self.update_score(score, False)

    def reset_board(self):
        self.score = 1
        self.reward = 0
        self.dice_use = 0
        self.is_double = False
        self.cards = []
        self.ex_scores = [0] * 6
        self.ex_score = float('inf')
        self.ex_action = None
        self.rank_reg = False
        self.reset_card_info()

    def get_state(self):
        state = [
            self.rank_reg,
            self.auto_process,
            self.score,
            stage[self.score - 1][1],
            stage[self.score - 1][2],
            self.dice_use,
            1 if self.is_double else 0,
        ]
        for i in range(5):
            state.append(self.cards[i][0] if i < len(self.cards) else 0)
        for card in self.card_info:
            state.append(card[3])
        return state

    def set_state(self, state):
        self.auto_process = False
        self.score = state[2]
        self.dice_use = state[5]
        self.is_double = state[6] == 1
        self.cards = []
        for i in range(7, 12):
            if state[i] != 0:
                self.cards.append(self.card_info[state[i] - 1])
        self.reset_card_info()
        for i in range(12, 42):
            if state[i] == 1:
                self.get_card(i - 12, False)
        self.rank_reg = state[0]
        self.auto_process = state[1]

    def choose_action(self):
        length = len(self.cards)
        if length == 0:
            return 0

        # Check: distance card leads to jump -> card event
        for i in range(length):
            if (self.cards[i][1] == 1
                    and self.score + self.cards[i][2] - 1 < 2898
                    and stage[self.score + self.cards[i][2] - 1][4] is not None
                    and stage[self.score + self.cards[i][2] - 1][4] > 0
                    and stage[self.score + self.cards[i][2] + stage[self.score + self.cards[i][2] - 1][4] - 1][5] == 2):
                return i + 1

        # Check: distance card lands on card event
        for i in range(length):
            if (self.cards[i][1] == 1
                    and self.score + self.cards[i][2] - 1 < 2898
                    and stage[self.score + self.cards[i][2] - 1][5] == 2):
                return i + 1

        # Check: distance card leads to 29+ space jump
        for i in range(length):
            if (self.cards[i][1] == 1
                    and self.score + self.cards[i][2] - 1 < 2898
                    and stage[self.score + self.cards[i][2] - 1][4] is not None
                    and stage[self.score + self.cards[i][2] - 1][4] >= 29):
                return i + 1

        # Check: stop event within +8, use multiplier card
        for i in range(self.score, min(2897, self.score + 8)):
            if stage[i][5] == 6 or stage[i][5] == 9:
                for j in range(length):
                    if self.cards[j][1] == 2:
                        return j + 1

        # Count remaining spaces in current stage
        cnt = 0
        for i in range(min(2897, self.score + 1), min(2897, self.score + 50)):
            if stage[i][1] == stage[self.score - 1][1]:
                cnt += 1

        # Use stage card if 26+ spaces remaining
        for i in range(length):
            if self.cards[i][1] == 3 and cnt >= 26:
                return i + 1

        # When hand full or near dice limit
        if length == 5 or self.dice_use + length >= 100:
            for i in range(length):
                if self.cards[i][1] == 3 and cnt >= 20:
                    return i + 1
            for i in range(length):
                if self.cards[i][1] == 2:
                    return i + 1
            for i in range(length):
                for j in range(length):
                    if (i != j
                            and self.cards[i][1] == 1
                            and self.cards[j][1] == 1
                            and self.score + self.cards[i][2] + self.cards[j][2] - 1 < 2898
                            and self.score + self.cards[i][2] - 1 < 2898
                            and stage[self.score + self.cards[i][2] - 1][4] is not None
                            and stage[self.score + self.cards[i][2] - 1][4] > 0
                            and stage[self.score + self.cards[i][2] + self.cards[j][2] - 1][5] == 2):
                        return i + 1
            for i in range(length):
                if (self.cards[i][1] == 1
                        and self.score + self.cards[i][2] - 1 < 2898
                        and _sign(stage[self.score + self.cards[i][2] - 1][4]) != -1):
                    return i + 1
            for i in range(length):
                if self.cards[i][1] != 1:
                    return i + 1

        return 0

    def copy(self):
        return copy.deepcopy(self)

    def change_mode(self):
        self.auto_process = not self.auto_process
        self.rank_reg = True


def _sign(value):
    """Port of JS Math.sign behavior: Math.sign(null) === 0, Math.sign(undefined) === NaN.
    In the stage data, None represents JS null, so treat None as 0."""
    if value is None:
        return 0
    if value > 0:
        return 1
    if value < 0:
        return -1
    return 0
