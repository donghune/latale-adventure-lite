from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QPushButton, QSpinBox, QFrame, QScrollArea, QSizePolicy,
    QApplication
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QPalette


class CardButton(QPushButton):
    """Custom button that emits different signals for left/right click."""
    left_clicked = pyqtSignal(int)
    right_clicked = pyqtSignal(int)

    def __init__(self, index, text="", parent=None):
        super().__init__(text, parent)
        self.index = index
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.left_clicked.emit(self.index)
        elif event.button() == Qt.MouseButton.RightButton:
            self.right_clicked.emit(self.index)


class DiceButton(QPushButton):
    """Dice button with left/right click support."""
    dice_clicked = pyqtSignal(int, bool)  # value, use_dice

    def __init__(self, value, parent=None):
        super().__init__(f"+{value}", parent)
        self.value = value
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.dice_clicked.emit(self.value, True)
        elif event.button() == Qt.MouseButton.RightButton:
            self.dice_clicked.emit(self.value, False)


def _is_dark():
    palette = QApplication.instance().palette()
    bg = palette.color(QPalette.ColorRole.Window)
    return bg.lightness() < 128


def _make_section(title=None, parent=None):
    """Create a simple section container with optional title."""
    widget = QWidget(parent)
    layout = QVBoxLayout(widget)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(6)
    if title:
        lbl = QLabel(title)
        lbl.setFont(QFont("sans-serif", 13, QFont.Weight.Bold))
        layout.addWidget(lbl)
    return widget, layout


class MainWindow(QMainWindow):
    # Signals
    dice_value_clicked = pyqtSignal(int, bool)
    card_button_clicked = pyqtSignal(int, bool)
    use_card_clicked = pyqtSignal(int)
    move_requested = pyqtSignal(int)
    dice_use_changed = pyqtSignal(int)
    undo_requested = pyqtSignal()
    calculate_requested = pyqtSignal()
    region_select_requested = pyqtSignal(str)
    auto_capture_toggled = pyqtSignal(bool)
    always_on_top_toggled = pyqtSignal(bool)

    def __init__(self):
        super().__init__()
        self.compact_mode = True
        self.current_columns = 5
        self.card_buttons: list[CardButton] = []
        self.expected_labels: list[QLabel] = []
        self.use_buttons: list[QPushButton] = []
        self._auto_capture_active = False
        self._init_ui()

    def _init_ui(self):
        self.setWindowTitle("라테일 어드벤처 계산기")
        self.setMinimumSize(360, 500)
        self._apply_stylesheet()

        central = QWidget()
        self.setCentralWidget(central)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll_content = QWidget()
        col = QVBoxLayout(scroll_content)
        col.setSpacing(12)
        col.setContentsMargins(16, 16, 16, 16)

        self._build_status_panel(col)
        self._build_controls_panel(col)
        self._build_expected_panel(col)
        self._build_card_list_panel(col)
        self._build_capture_panel(col)
        col.addStretch()

        scroll.setWidget(scroll_content)
        wrapper = QVBoxLayout(central)
        wrapper.setContentsMargins(0, 0, 0, 0)
        wrapper.addWidget(scroll)

    @staticmethod
    def _is_dark_mode():
        palette = QApplication.instance().palette()
        bg = palette.color(QPalette.ColorRole.Window)
        return bg.lightness() < 128

    def _apply_stylesheet(self):
        dark = self._is_dark_mode()
        if dark:
            self.setStyleSheet("""
                QMainWindow { background: #1e1e2e; }
                QPushButton {
                    padding: 8px 10px; border: 1px solid #45475a;
                    border-radius: 8px; background: #313244; color: #cdd6f4;
                }
                QPushButton:hover { background: #45475a; }
                QPushButton[primary="true"] {
                    background: #89b4fa; color: #1e1e2e; border-color: #74c7ec;
                }
                QPushButton[primary="true"]:hover { background: #74c7ec; }
                QPushButton[active="true"] {
                    background: #89b4fa; color: #1e1e2e; border-color: #74c7ec;
                }
                QSpinBox {
                    padding: 6px; border: 1px solid #45475a; border-radius: 8px;
                    background: #313244; color: #cdd6f4;
                }
                QLabel { color: #cdd6f4; }
                QScrollArea { background: transparent; }
            """)
            self._dark = True
        else:
            self.setStyleSheet("""
                QMainWindow { background: #f5f6fb; }
                QPushButton {
                    padding: 8px 10px; border: 1px solid #cbd5e1;
                    border-radius: 8px; background: #eef2ff;
                }
                QPushButton:hover { background: #dbeafe; }
                QPushButton[primary="true"] {
                    background: #2563eb; color: white; border-color: #1d4ed8;
                }
                QPushButton[primary="true"]:hover { background: #1d4ed8; }
                QPushButton[active="true"] {
                    background: #2563eb; color: white; border-color: #1d4ed8;
                }
                QSpinBox {
                    padding: 6px; border: 1px solid #cbd5e1; border-radius: 8px;
                }
            """)
            self._dark = False

    # ── Status Panel ──────────────────────────────────────────────────

    def _build_status_panel(self, parent_layout):
        frame, lay = _make_section("상태")
        grid = QGridLayout()
        grid.setSpacing(8)

        self._lbl_position = QLabel("1칸 (스페이스 1)")
        self._lbl_stage = QLabel("1단계 - 벨로스")
        self._lbl_dice = QLabel("0 / 100")
        self._lbl_recog = QLabel("대기")

        sub_color = "#9399b2" if self._dark else "#6b7280"
        for col, (label_text, widget) in enumerate([
            ("현재 위치", self._lbl_position),
            ("현재 스테이지", self._lbl_stage),
            ("주사위 사용", self._lbl_dice),
            ("인식 상태", self._lbl_recog),
        ]):
            lbl = QLabel(label_text)
            lbl.setStyleSheet(f"color: {sub_color}; font-size: 12px;")
            widget.setFont(QFont("sans-serif", 12, QFont.Weight.Bold))
            grid.addWidget(lbl, 0, col)
            grid.addWidget(widget, 1, col)

        lay.addLayout(grid)
        parent_layout.addWidget(frame)

    # ── Controls Panel ────────────────────────────────────────────────

    def _build_controls_panel(self, parent_layout):
        frame, lay = _make_section("이동/주사위")

        # Move input row
        move_row = QHBoxLayout()
        lbl_move = QLabel("이동 (칸 번호 입력)")
        lbl_move.setStyleSheet(f"color: {'#9399b2' if self._dark else '#6b7280'}; font-size: 12px;")
        self._spin_move = QSpinBox()
        self._spin_move.setRange(1, 2898)
        self._spin_move.setValue(1)
        btn_move = QPushButton("이동")
        btn_move.setProperty("primary", True)
        btn_move.clicked.connect(lambda: self.move_requested.emit(self._spin_move.value()))
        move_row.addWidget(lbl_move)
        move_row.addWidget(self._spin_move, 1)
        move_row.addWidget(btn_move)
        lay.addLayout(move_row)

        # Dice use input row
        dice_row = QHBoxLayout()
        lbl_dice = QLabel("주사위 사용 횟수")
        lbl_dice.setStyleSheet(f"color: {'#9399b2' if self._dark else '#6b7280'}; font-size: 12px;")
        self._spin_dice = QSpinBox()
        self._spin_dice.setRange(0, 100)
        btn_dice = QPushButton("적용")
        btn_dice.setProperty("primary", True)
        btn_dice.clicked.connect(lambda: self.dice_use_changed.emit(self._spin_dice.value()))
        dice_row.addWidget(lbl_dice)
        dice_row.addWidget(self._spin_dice, 1)
        dice_row.addWidget(btn_dice)
        lay.addLayout(dice_row)

        # Hint label
        hint = QLabel("좌클릭 사용 횟수 증가, 우클릭 미증가(보너스 바로 뒤)")
        hint.setStyleSheet(f"color: {'#f38ba8' if self._dark else '#dc2626'}; font-size: 12px;")
        lay.addWidget(hint)

        # Dice buttons: row 1 (+2..+7), row 2 (+8..+12)
        for values in ([2, 3, 4, 5, 6, 7], [8, 9, 10, 11, 12]):
            row = QHBoxLayout()
            row.setSpacing(6)
            for v in values:
                btn = DiceButton(v)
                btn.dice_clicked.connect(self.dice_value_clicked)
                row.addWidget(btn)
            lay.addLayout(row)

        # Action buttons
        actions = QHBoxLayout()
        btn_undo = QPushButton("이전으로 되돌리기")
        btn_undo.clicked.connect(self.undo_requested)
        btn_calc = QPushButton("예상 점수 계산")
        btn_calc.setProperty("primary", True)
        btn_calc.clicked.connect(self.calculate_requested)
        actions.addWidget(btn_undo)
        actions.addWidget(btn_calc)
        lay.addLayout(actions)

        parent_layout.addWidget(frame)

    # ── Expected Scores Panel ─────────────────────────────────────────

    def _build_expected_panel(self, parent_layout):
        frame, lay = _make_section("예상 점수")

        self.expected_labels = []
        self.use_buttons = []

        # Row 0: dice
        row = QHBoxLayout()
        lbl = QLabel("주사위 : 0점")
        lbl.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        btn = QPushButton("사용")
        btn.setVisible(False)
        row.addWidget(lbl)
        row.addWidget(btn)
        lay.addLayout(row)
        self.expected_labels.append(lbl)
        self.use_buttons.append(btn)

        # Rows 1-5: card slots
        for i in range(5):
            row = QHBoxLayout()
            lbl = QLabel("N/A : Undefined")
            lbl.setStyleSheet("color: #9ca3af;")
            lbl.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
            btn = QPushButton("사용")
            btn.setVisible(False)
            slot_idx = i
            btn.clicked.connect(lambda checked, s=slot_idx: self.use_card_clicked.emit(s))
            row.addWidget(lbl)
            row.addWidget(btn)
            lay.addLayout(row)
            self.expected_labels.append(lbl)
            self.use_buttons.append(btn)

        self._lbl_iteration = QLabel("계산 횟수: 10,000")
        self._lbl_iteration.setStyleSheet(f"color: {'#f38ba8' if self._dark else '#dc2626'}; font-size: 12px;")
        lay.addWidget(self._lbl_iteration)

        parent_layout.addWidget(frame)

    # ── Card List Panel ───────────────────────────────────────────────

    def _build_card_list_panel(self, parent_layout):
        frame, lay = _make_section("카드 목록")

        hint = QLabel("좌클릭: 획득 표시 · 우클릭: 보유 추가")
        hint.setStyleSheet(f"color: {'#f38ba8' if self._dark else '#dc2626'}; font-size: 12px;")
        lay.addWidget(hint)

        self._card_grid_widget = QWidget()
        self._card_grid = QGridLayout(self._card_grid_widget)
        self._card_grid.setSpacing(6)
        lay.addWidget(self._card_grid_widget)

        parent_layout.addWidget(frame)
        self._build_card_buttons()

    def _build_card_buttons(self):
        """Create 30 card buttons."""
        from engine.data import user_card_info
        self.card_buttons = []
        for i in range(30):
            info = user_card_info[i]
            if self.compact_mode:
                text = self._compact_name_from_info(info)
            else:
                text = f"{info[0]}번 - {info[1]}"
            btn = CardButton(i, text)
            btn.left_clicked.connect(lambda idx: self.card_button_clicked.emit(idx, False))
            btn.right_clicked.connect(lambda idx: self.card_button_clicked.emit(idx, True))
            self.card_buttons.append(btn)
        self._layout_card_buttons()

    def _layout_card_buttons(self):
        """Re-layout card buttons in the grid."""
        while self._card_grid.count():
            item = self._card_grid.takeAt(0)
            if item.widget():
                item.widget().setParent(None)
        for i, btn in enumerate(self.card_buttons):
            row = i // self.current_columns
            col = i % self.current_columns
            self._card_grid.addWidget(btn, row, col)

    @staticmethod
    def _compact_name_from_info(info):
        card_type = info[2] if len(info) > 2 else 1
        card_value = info[3] if len(info) > 3 else 0
        if card_type == 1:
            return f"+{card_value}" if card_value >= 0 else str(card_value)
        elif card_type == 2:
            return f"x{card_value}"
        elif card_type == 3:
            return "NEXT"
        return str(info[0])

    # ── Auto Capture Panel ────────────────────────────────────────────

    def _build_capture_panel(self, parent_layout):
        frame, lay = _make_section("자동 인식")

        self._btn_auto = QPushButton("자동 인식 시작")
        self._btn_auto.setProperty("primary", True)
        self._btn_auto.clicked.connect(self._toggle_auto_capture)
        lay.addWidget(self._btn_auto)

        btn_pos = QPushButton("위치 영역 설정")
        btn_pos.clicked.connect(lambda: self.region_select_requested.emit("position_region"))
        lay.addWidget(btn_pos)

        btn_dice = QPushButton("주사위 영역 설정")
        btn_dice.clicked.connect(lambda: self.region_select_requested.emit("dice_region"))
        lay.addWidget(btn_dice)

        self._lbl_capture_status = QLabel("영역을 설정한 후 자동 인식을 시작하세요.")
        self._lbl_capture_status.setStyleSheet(f"color: {'#9399b2' if self._dark else '#6b7280'}; font-size: 12px;")
        self._lbl_capture_status.setWordWrap(True)
        lay.addWidget(self._lbl_capture_status)

        self._btn_on_top = QPushButton("항상 위")
        self._btn_on_top.clicked.connect(self._toggle_on_top)
        lay.addWidget(self._btn_on_top)

        parent_layout.addWidget(frame)

    # ── Public update methods ─────────────────────────────────────────

    def update_status(self, score, stage_id, stage_name, space_id, dice_use, auto_mode):
        """Update the status panel."""
        self._lbl_position.setText(f"{score}칸 (스페이스 {space_id})")
        self._lbl_stage.setText(f"{stage_id}단계 - {stage_name}")
        self._lbl_dice.setText(f"{dice_use} / 100")

    def update_expected(self, ex_scores, ex_values, ex_action, cards):
        """Update expected scores panel."""
        best_idx = ex_action

        # Dice row (index 0)
        dice_score = ex_scores[0] if ex_scores else 0
        is_number = isinstance(dice_score, (int, float))
        extra = ""
        if is_number and ex_values:
            extra = f" ({int(ex_values['min'][0])} ~ {int(ex_values['max'][0])})"
        is_best = best_idx == 0
        star = "★ " if is_best else ""
        text = f"{star}주사위 : {int(dice_score)}점{extra}" if is_number else f"{star}주사위 : {dice_score}"
        self.expected_labels[0].setText(text)
        red = "#f38ba8" if self._dark else "#dc2626"
        if is_best and is_number:
            self.expected_labels[0].setStyleSheet(f"color: {red}; font-weight: bold;")
        else:
            self.expected_labels[0].setStyleSheet("")
        self.use_buttons[0].setVisible(False)

        # Card slots (index 1-5)
        for i in range(5):
            idx = i + 1
            lbl = self.expected_labels[idx]
            btn = self.use_buttons[idx]

            if i < len(cards) and cards[i] is not None:
                card = cards[i]
                score = ex_scores[idx] if idx < len(ex_scores) else 0
                is_num = isinstance(score, (int, float))
                extra = ""
                if is_num and ex_values:
                    extra = f" ({int(ex_values['min'][idx])} ~ {int(ex_values['max'][idx])})"
                is_best = best_idx == idx
                star = "★ " if is_best else ""
                card_name = self._compact_card_name(card)
                text = f"{star}{card_name} : {int(score)}점{extra}" if is_num else f"{star}{card_name} : {score}"
                lbl.setText(text)
                if is_best and is_num:
                    lbl.setStyleSheet(f"color: {red}; font-weight: bold;")
                else:
                    lbl.setStyleSheet("")
                btn.setVisible(True)
            else:
                lbl.setText("N/A : Undefined")
                lbl.setStyleSheet("color: #9ca3af;")
                btn.setVisible(False)

    def update_card_list(self, card_info_list):
        """Update the card list buttons appearance (obtained status)."""
        from engine.data import user_card_info
        for i, btn in enumerate(self.card_buttons):
            info = card_info_list[i] if i < len(card_info_list) else None
            if info is None:
                continue

            if self.compact_mode:
                ui_info = user_card_info[i]
                btn.setText(self._compact_name_from_info(ui_info))
            else:
                ui_info = user_card_info[i]
                btn.setText(f"{ui_info[0]}번 - {ui_info[1]}")

            if info[3] == 1:
                if self._dark:
                    btn.setStyleSheet("background: #45475a; color: #9399b2;")
                else:
                    btn.setStyleSheet("background: #e5e7eb; color: #4b5563;")
            else:
                btn.setStyleSheet("")

    def update_recognition_status(self, status_text, is_ok=True):
        """Update auto-recognition status display."""
        color = "#166534" if is_ok else "#dc2626"
        self._lbl_recog.setText(status_text)
        self._lbl_recog.setStyleSheet(f"color: {color}; font-weight: bold;")
        self._lbl_capture_status.setText(status_text)

    def set_iteration_count(self, count):
        self._lbl_iteration.setText(f"계산 횟수: {count:,}")

    # ── Card display helpers ──────────────────────────────────────────

    @staticmethod
    def _compact_card_name(card):
        card_type = card[1]
        card_value = card[2]
        if card_type == 1:
            return f"+{card_value}" if card_value >= 0 else str(card_value)
        elif card_type == 2:
            return f"x{card_value}"
        elif card_type == 3:
            return "NEXT"
        return str(card[0])

    # ── Internal slots ────────────────────────────────────────────────

    def _toggle_auto_capture(self):
        self._auto_capture_active = not self._auto_capture_active
        if self._auto_capture_active:
            self._btn_auto.setText("자동 인식 중지")
        else:
            self._btn_auto.setText("자동 인식 시작")
        self.auto_capture_toggled.emit(self._auto_capture_active)

    def _toggle_on_top(self):
        is_on_top = bool(self.windowFlags() & Qt.WindowType.WindowStaysOnTopHint)
        if is_on_top:
            self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowStaysOnTopHint)
            self._btn_on_top.setProperty("active", "false")
        else:
            self.setWindowFlags(self.windowFlags() | Qt.WindowType.WindowStaysOnTopHint)
            self._btn_on_top.setProperty("active", "true")
        self._btn_on_top.style().unpolish(self._btn_on_top)
        self._btn_on_top.style().polish(self._btn_on_top)
        self.show()
        self.always_on_top_toggled.emit(not is_on_top)
