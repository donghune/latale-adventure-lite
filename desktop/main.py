import sys
import os
import copy
import multiprocessing
from threading import Thread

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer, QObject, pyqtSignal

from engine.data import stage, card_info, user_card_info, stage_names
from engine.board import Board
from engine.simulator import simulate_action, calc_loss
from capture.screen import ScreenCapture
from capture.matcher import DigitMatcher
from gui.main_window import MainWindow
from gui.region_selector import RegionSelector


class SimulationWorker(QObject):
    """Runs Monte Carlo simulation in background threads."""
    result_ready = pyqtSignal(int, object)  # action_index, stats_dict_or_None
    all_done = pyqtSignal()

    def __init__(self):
        super().__init__()
        self._pending = 0

    def run(self, state, actions, iteration=10000):
        self._pending = len(actions)
        for action in actions:
            t = Thread(
                target=self._simulate,
                args=(action, state, iteration),
                daemon=True,
            )
            t.start()

    def _simulate(self, action_index, state, iteration):
        idx, stats = simulate_action(action_index, state=state, iteration=iteration)
        self.result_ready.emit(idx, stats)
        self._pending -= 1
        if self._pending <= 0:
            self.all_done.emit()


class App:
    """Application controller that wires GUI, engine, and capture together."""

    HISTORY_LIMIT = 50

    def __init__(self):
        self.board = Board()
        self.history_stack: list[list] = []
        self.iteration = 10000
        self.sim_worker = SimulationWorker()
        self.sim_req_id = 0

        # Capture
        self.screen_capture = ScreenCapture()
        self.digit_matcher = DigitMatcher()
        self._prev_position = None
        self._prev_dice = None

        # GUI
        self.window = MainWindow()
        self._region_selector = None
        self._capture_timer = QTimer()
        self._capture_timer.setInterval(1000)
        self._capture_timer.timeout.connect(self._on_capture_tick)

        self._connect_signals()
        self._render_all()
        self._calc_expected()

    def _connect_signals(self):
        w = self.window
        w.dice_value_clicked.connect(self._on_dice_value)
        w.card_button_clicked.connect(self._on_card_button)
        w.use_card_clicked.connect(self._on_use_card)
        w.move_requested.connect(self._on_move)
        w.dice_use_changed.connect(self._on_dice_use)
        w.undo_requested.connect(self._on_undo)
        w.calculate_requested.connect(self._calc_expected)
        w.region_select_requested.connect(self._on_region_select)
        w.auto_capture_toggled.connect(self._on_auto_capture_toggle)
        self.sim_worker.result_ready.connect(self._on_sim_result)

    # ── History ───────────────────────────────────────────────────────

    def _push_history(self):
        self.history_stack.append(self.board.get_state())
        if len(self.history_stack) > self.HISTORY_LIMIT:
            self.history_stack.pop(0)

    def _pop_history(self):
        return self.history_stack.pop() if self.history_stack else None

    # ── Rendering ─────────────────────────────────────────────────────

    def _render_all(self):
        b = self.board
        stage_id = stage[b.score - 1][1]
        space_id = stage[b.score - 1][2]
        name = stage_names[stage_id - 1] if 1 <= stage_id <= len(stage_names) else "?"
        self.window.update_status(b.score, stage_id, name, space_id, b.dice_use, b.auto_process)
        self.window.update_expected(
            b.ex_scores, b.ex_values, b.ex_action, b.cards
        )
        self.window.update_card_list(b.card_info)
        self.window.set_iteration_count(self.iteration)

    # ── Simulation ────────────────────────────────────────────────────

    def _calc_expected(self):
        b = self.board
        b.ex_scores = ["계산중..."] * 6
        b.ex_values = {
            "min": [0] * 6, "max": [0] * 6,
            "std": [0] * 6, "mid": [0] * 6,
        }
        b.ex_action = None
        b.ex_score = float("inf")
        self._render_all()

        actions = list(range(len(b.cards) + 1))
        self.sim_req_id += 1
        self._sim_results = {}
        self._sim_actions = actions
        state = b.get_state()
        self.sim_worker.run(state, actions, self.iteration)

    def _on_sim_result(self, action_index, stats):
        b = self.board
        if stats is None:
            b.ex_scores[action_index] = b.score
        else:
            b.ex_scores[action_index] = stats["avg"]
            b.ex_values["min"][action_index] = stats["min"]
            b.ex_values["max"][action_index] = stats["max"]
            b.ex_values["std"][action_index] = round(stats["std"], 3)
            b.ex_values["mid"][action_index] = stats["mid"]

        # Check if all done
        all_done = all(
            not isinstance(s, str) for s in b.ex_scores[:len(b.cards) + 1]
        )
        if all_done:
            numeric = [
                s for s in b.ex_scores[:len(b.cards) + 1]
                if isinstance(s, (int, float))
            ]
            if numeric:
                max_val = max(numeric)
                b.ex_action = b.ex_scores.index(max_val)
                b.ex_score = max_val - calc_loss(self.iteration)

        self._render_all()

    # ── Event Handlers ────────────────────────────────────────────────

    def _on_dice_value(self, val, use_dice):
        self._push_history()
        if use_dice:
            self.board.dice_use = min(100, self.board.dice_use + 1)
        self.board.is_double = False
        self.board.update_score(val, True)
        self._render_all()
        self._calc_expected()

    def _on_move(self, position):
        if position < 1 or position > 2898:
            return
        self._push_history()
        self.board.score = position
        self.board.rank_reg = True
        self.board.check_event()
        self._render_all()
        self._calc_expected()

    def _on_dice_use(self, value):
        self._push_history()
        self.board.dice_use = value
        self.board.rank_reg = True
        self._render_all()
        self._calc_expected()

    def _on_undo(self):
        prev = self._pop_history()
        if prev is None:
            return
        self.board.set_state(prev)
        self._render_all()
        self._calc_expected()

    def _on_card_button(self, index, add_to_hand):
        self._push_history()
        card_id = self.board.card_info[index][0]
        self.board.rank_reg = True

        if not add_to_hand:
            # Left click: toggle obtained status
            if self.board.card_info[index][3] == 1:
                self.board.card_info[index][3] = 0
                if index not in self.board.card_index:
                    self.board.card_index.append(index)
                self.board.cards = [c for c in self.board.cards if c[0] != card_id]
            else:
                self.board.card_info[index][3] = 1
                if index in self.board.card_index:
                    self.board.card_index.remove(index)
        else:
            # Right click: add to hand
            self.board.card_info[index][3] = 1
            if index in self.board.card_index:
                self.board.card_index.remove(index)
            in_hand = any(c[0] == card_id for c in self.board.cards)
            if not in_hand and len(self.board.cards) < 5:
                self.board.cards.append(self.board.card_info[index])

        if len(self.board.card_index) == 0:
            self.board.reset_card_info()

        self._render_all()
        self._calc_expected()

    def _on_use_card(self, slot_idx):
        if slot_idx >= len(self.board.cards):
            return
        self._push_history()
        self.board.step(slot_idx + 1)
        self._render_all()
        self._calc_expected()

    # ── Screen Capture ────────────────────────────────────────────────

    def _on_region_select(self, region_name):
        self._region_selector = RegionSelector(region_name)
        self._region_selector.region_selected.connect(self._on_region_selected)
        self._region_selector.selection_cancelled.connect(
            lambda: self.window.update_recognition_status("영역 선택 취소됨", False)
        )
        self._region_selector.show()

    def _on_region_selected(self, name, left, top, width, height):
        self.screen_capture.set_region(name, left, top, width, height)
        self.window.update_recognition_status(
            f"'{name}' 영역이 설정되었습니다 ({width}x{height})", True
        )

    def _on_auto_capture_toggle(self, enabled):
        if enabled:
            has_pos = self.screen_capture.has_region("position_region")
            has_dice = self.screen_capture.has_region("dice_region")
            if not has_pos and not has_dice:
                self.window.update_recognition_status(
                    "영역을 먼저 설정해주세요.", False
                )
                self.window._auto_capture_active = False
                self.window._btn_auto.setText("자동 인식 시작")
                return
            if not self.digit_matcher.has_templates():
                self.window.update_recognition_status(
                    "숫자 템플릿이 없습니다. templates/ 폴더에 0~9 이미지를 추가하세요.",
                    False,
                )
                self.window._auto_capture_active = False
                self.window._btn_auto.setText("자동 인식 시작")
                return
            self._capture_timer.start()
            self.window.update_recognition_status("자동 인식 실행 중...", True)
        else:
            self._capture_timer.stop()
            self.window.update_recognition_status("자동 인식 중지됨", False)

    def _on_capture_tick(self):
        """Periodic capture and recognition."""
        changed = False

        # Recognize position
        if self.screen_capture.has_region("position_region"):
            try:
                img = self.screen_capture.capture_region("position_region")
                number, conf = self.digit_matcher.recognize_number(img)
                if number is not None and 1 <= number <= 2898:
                    if number != self._prev_position:
                        self._prev_position = number
                        self._push_history()
                        self.board.score = number
                        self.board.rank_reg = True
                        self.board.check_event()
                        changed = True
            except Exception:
                pass

        # Recognize dice usage
        if self.screen_capture.has_region("dice_region"):
            try:
                img = self.screen_capture.capture_region("dice_region")
                number, conf = self.digit_matcher.recognize_number(img)
                if number is not None and 0 <= number <= 100:
                    if number != self._prev_dice:
                        self._prev_dice = number
                        self._push_history()
                        self.board.dice_use = number
                        self.board.rank_reg = True
                        changed = True
            except Exception:
                pass

        if changed:
            self.window.update_recognition_status(
                f"위치: {self._prev_position}, 주사위: {self._prev_dice}", True
            )
            self._render_all()
            self._calc_expected()


def main():
    multiprocessing.freeze_support()
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    controller = App()
    controller.window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
