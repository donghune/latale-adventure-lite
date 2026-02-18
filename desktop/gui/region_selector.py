from PyQt6.QtWidgets import QWidget, QApplication
from PyQt6.QtCore import Qt, QRect, pyqtSignal
from PyQt6.QtGui import QPainter, QColor, QPen, QFont


class RegionSelector(QWidget):
    """Fullscreen transparent overlay for selecting a screen region."""
    region_selected = pyqtSignal(str, int, int, int, int)  # name, left, top, width, height
    selection_cancelled = pyqtSignal()

    def __init__(self, region_name="region"):
        super().__init__()
        self.region_name = region_name
        self.start_pos = None
        self.end_pos = None
        self.is_selecting = False
        self._init_ui()

    def _init_ui(self):
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setCursor(Qt.CursorShape.CrossCursor)

        # Cover all screens
        screen = QApplication.primaryScreen()
        geometry = screen.geometry()
        for s in QApplication.screens():
            geometry = geometry.united(s.geometry())
        self.setGeometry(geometry)

    def paintEvent(self, event):
        painter = QPainter(self)
        # Semi-transparent dark overlay
        painter.fillRect(self.rect(), QColor(0, 0, 0, 100))

        if self.start_pos and self.end_pos:
            rect = QRect(self.start_pos, self.end_pos).normalized()
            # Clear the selected area
            painter.setCompositionMode(
                QPainter.CompositionMode.CompositionMode_Clear
            )
            painter.fillRect(rect, QColor(0, 0, 0, 0))
            painter.setCompositionMode(
                QPainter.CompositionMode.CompositionMode_SourceOver
            )
            # Draw border
            pen = QPen(QColor(37, 99, 235), 2)
            painter.setPen(pen)
            painter.drawRect(rect)
            # Draw size label
            painter.setPen(QColor(255, 255, 255))
            painter.setFont(QFont("sans-serif", 12))
            label = f"{self.region_name}: {rect.width()}x{rect.height()}"
            painter.drawText(rect.x(), rect.y() - 8, label)

        # Draw instructions
        painter.setPen(QColor(255, 255, 255))
        painter.setFont(QFont("sans-serif", 16))
        painter.drawText(
            self.rect(),
            Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter,
            f"\n\ub4dc\ub798\uadf8\ud558\uc5ec '{self.region_name}' \uc601\uc5ed\uc744 \uc120\ud0dd\ud558\uc138\uc694 (ESC: \ucde8\uc18c)",
        )
        painter.end()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.start_pos = event.pos()
            self.end_pos = event.pos()
            self.is_selecting = True
            self.update()

    def mouseMoveEvent(self, event):
        if self.is_selecting:
            self.end_pos = event.pos()
            self.update()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self.is_selecting:
            self.is_selecting = False
            self.end_pos = event.pos()
            rect = QRect(self.start_pos, self.end_pos).normalized()
            if rect.width() > 5 and rect.height() > 5:
                global_pos = self.mapToGlobal(rect.topLeft())
                self.region_selected.emit(
                    self.region_name,
                    global_pos.x(),
                    global_pos.y(),
                    rect.width(),
                    rect.height(),
                )
            self.close()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.selection_cancelled.emit()
            self.close()
