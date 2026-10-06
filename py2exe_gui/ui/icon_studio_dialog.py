"""Icon Studio: build a real multi-size .ico from an image or from letters.

Qt does the drawing and the PNG encoding; ``core.icon_studio.pack_ico``
assembles the .ico. No imaging library is needed.
"""

import os

from PyQt5.QtCore import QBuffer, QByteArray, QIODevice, QRectF, QSize, Qt
from PyQt5.QtGui import QColor, QFont, QImage, QPainter, QPainterPath, QPixmap
from PyQt5.QtWidgets import (
    QButtonGroup,
    QColorDialog,
    QComboBox,
    QDialog,
    QFileDialog,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QRadioButton,
    QVBoxLayout,
)

from py2exe_gui.core.icon_studio import ICO_SIZES, monogram, pack_ico
from py2exe_gui.strings import S
from py2exe_gui.ui.dialogs import _inherited_direction

SHAPE_ROUNDED = "rounded"
SHAPE_CIRCLE = "circle"
SHAPE_SQUARE = "square"
DEFAULT_COLOR = "#3b82f6"
PREVIEW_SIZES = (16, 32, 48, 128)


def _contrasting_text(color: QColor) -> QColor:
    """White on dark backgrounds, near-black on light ones."""
    luminance = 0.299 * color.red() + 0.587 * color.green() + 0.114 * color.blue()
    return QColor("#111111") if luminance > 160 else QColor("#ffffff")


def render_image_icon(source: QImage, size: int) -> QImage:
    """``source`` fitted (not cropped) into a transparent square."""
    canvas = QImage(size, size, QImage.Format_ARGB32)
    canvas.fill(Qt.transparent)
    scaled = source.scaled(size, size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
    painter = QPainter(canvas)
    painter.setRenderHint(QPainter.SmoothPixmapTransform)
    painter.drawImage((size - scaled.width()) // 2, (size - scaled.height()) // 2, scaled)
    painter.end()
    return canvas


def render_text_icon(text: str, size: int, color: QColor, shape: str) -> QImage:
    """Letters on a coloured shape, legible down to 16px."""
    canvas = QImage(size, size, QImage.Format_ARGB32)
    canvas.fill(Qt.transparent)
    painter = QPainter(canvas)
    painter.setRenderHint(QPainter.Antialiasing)
    painter.setRenderHint(QPainter.TextAntialiasing)

    rect = QRectF(0, 0, size, size)
    path = QPainterPath()
    if shape == SHAPE_CIRCLE:
        path.addEllipse(rect)
    elif shape == SHAPE_ROUNDED:
        radius = size * 0.22
        path.addRoundedRect(rect, radius, radius)
    else:
        path.addRect(rect)
    painter.fillPath(path, color)

    if text:
        font = QFont()
        font.setBold(True)
        # Two letters need a smaller face to fit the same square.
        font.setPixelSize(max(6, int(size * (0.62 if len(text) == 1 else 0.46))))
        painter.setFont(font)
        painter.setPen(_contrasting_text(color))
        painter.drawText(rect, Qt.AlignCenter, text)
    painter.end()
    return canvas


def png_bytes(image: QImage) -> bytes:
    data = QByteArray()
    buffer = QBuffer(data)
    buffer.open(QIODevice.WriteOnly)
    image.save(buffer, "PNG")
    buffer.close()
    return bytes(data)


class IconStudioDialog(QDialog):
    """Pick a source, preview the sizes, save the .ico."""

    def __init__(self, parent=None, app_name: str = "", start_dir: str = ""):
        super().__init__(parent)
        self.setWindowTitle(S.ICON_STUDIO_TITLE)
        self.setMinimumWidth(520)
        self.setLayoutDirection(_inherited_direction(parent))
        self.start_dir = start_dir
        self.app_name = app_name
        self.saved_path = ""
        self._image = QImage()
        self._color = QColor(DEFAULT_COLOR)

        layout = QVBoxLayout(self)
        hint = QLabel(S.ICON_STUDIO_HINT)
        hint.setWordWrap(True)
        layout.addWidget(hint)

        mode_row = QHBoxLayout()
        self.text_mode = QRadioButton(S.ICON_STUDIO_FROM_TEXT)
        self.image_mode = QRadioButton(S.ICON_STUDIO_FROM_IMAGE)
        self.text_mode.setChecked(True)
        group = QButtonGroup(self)
        group.addButton(self.text_mode)
        group.addButton(self.image_mode)
        self.text_mode.toggled.connect(self.refresh_preview)
        mode_row.addWidget(self.text_mode)
        mode_row.addWidget(self.image_mode)
        layout.addLayout(mode_row)

        grid = QGridLayout()
        grid.addWidget(QLabel(S.ICON_STUDIO_TEXT_LABEL), 0, 0)
        self.text_input = QLineEdit(monogram(app_name) or "A")
        self.text_input.setMaxLength(2)
        self.text_input.textChanged.connect(self.refresh_preview)
        grid.addWidget(self.text_input, 0, 1)
        self.color_btn = QPushButton(S.ICON_STUDIO_COLOR)
        self.color_btn.clicked.connect(self.choose_color)
        grid.addWidget(self.color_btn, 0, 2)

        grid.addWidget(QLabel(S.ICON_STUDIO_SHAPE_LABEL), 1, 0)
        self.shape_combo = QComboBox()
        for label, key in (
            (S.ICON_STUDIO_SHAPE_ROUNDED, SHAPE_ROUNDED),
            (S.ICON_STUDIO_SHAPE_CIRCLE, SHAPE_CIRCLE),
            (S.ICON_STUDIO_SHAPE_SQUARE, SHAPE_SQUARE),
        ):
            self.shape_combo.addItem(label, key)
        self.shape_combo.currentIndexChanged.connect(self.refresh_preview)
        grid.addWidget(self.shape_combo, 1, 1, 1, 2)

        self.image_btn = QPushButton(S.ICON_STUDIO_CHOOSE_IMAGE)
        self.image_btn.clicked.connect(self.choose_image)
        self.image_label = QLabel("")
        self.image_label.setObjectName("aboutMuted")
        grid.addWidget(self.image_btn, 2, 0)
        grid.addWidget(self.image_label, 2, 1, 1, 2)
        layout.addLayout(grid)

        preview_row = QHBoxLayout()
        preview_row.addWidget(QLabel(S.ICON_STUDIO_PREVIEW))
        self.previews = []
        for size in PREVIEW_SIZES:
            slot = QLabel()
            slot.setFixedSize(QSize(size, size))
            slot.setAlignment(Qt.AlignCenter)
            slot.setAccessibleName(f"{S.ICON_STUDIO_PREVIEW} {size}px")
            preview_row.addWidget(slot, alignment=Qt.AlignBottom)
            self.previews.append((size, slot))
        preview_row.addStretch(1)
        layout.addLayout(preview_row)

        save_btn = QPushButton(S.ICON_STUDIO_SAVE)
        save_btn.setObjectName("successBtn")
        save_btn.clicked.connect(self.save)
        layout.addWidget(save_btn)

        self._update_color_button()
        self.refresh_preview()

    # ── Rendering ──────────────────────────────────────────────────────────

    def shape(self) -> str:
        return self.shape_combo.currentData() or SHAPE_ROUNDED

    def render(self, size: int):
        """The icon at ``size``, or None when there is nothing to draw yet."""
        if self.image_mode.isChecked():
            if self._image.isNull():
                return None
            return render_image_icon(self._image, size)
        text = self.text_input.text().strip()
        if not text:
            return None
        return render_text_icon(text, size, self._color, self.shape())

    def refresh_preview(self, *_args):
        for size, slot in self.previews:
            image = self.render(size)
            slot.setPixmap(QPixmap.fromImage(image) if image is not None else QPixmap())

    def build_ico(self) -> bytes:
        """The finished .ico bytes; raises ValueError when there is no source."""
        images = {}
        for size in ICO_SIZES:
            image = self.render(size)
            if image is None:
                raise ValueError(S.ICON_STUDIO_NOTHING)
            images[size] = png_bytes(image)
        return pack_ico(images)

    # ── Inputs ─────────────────────────────────────────────────────────────

    def set_image(self, path: str) -> bool:
        image = QImage(path)
        if image.isNull():
            return False
        self._image = image
        self.image_label.setText(os.path.basename(path))
        self.image_mode.setChecked(True)
        self.refresh_preview()
        return True

    def choose_image(self):
        path, _ = QFileDialog.getOpenFileName(
            self, S.ICON_STUDIO_CHOOSE_IMAGE, self.start_dir, S.ICON_STUDIO_IMAGE_FILTER
        )
        if path and not self.set_image(path):
            QMessageBox.warning(self, S.MSG_WARNING, S.ICON_STUDIO_BAD_IMAGE)

    def set_color(self, color: QColor):
        if color.isValid():
            self._color = color
            self._update_color_button()
            self.refresh_preview()

    def choose_color(self):
        self.set_color(QColorDialog.getColor(self._color, self))

    def _update_color_button(self):
        self.color_btn.setStyleSheet(
            f"background-color: {self._color.name()};"
            f" color: {_contrasting_text(self._color).name()};"
        )

    # ── Saving ─────────────────────────────────────────────────────────────

    def write_to(self, path: str) -> None:
        data = self.build_ico()
        with open(path, "wb") as f:
            f.write(data)
        self.saved_path = path

    def save(self):
        default_name = (self.app_name or "icon") + ".ico"
        path, _ = QFileDialog.getSaveFileName(
            self,
            S.ICON_STUDIO_SAVE_DIALOG,
            os.path.join(self.start_dir, default_name),
            S.ICON_STUDIO_ICO_FILTER,
        )
        if not path:
            return
        if not path.lower().endswith(".ico"):
            path += ".ico"
        try:
            self.write_to(path)
        except ValueError as e:
            QMessageBox.warning(self, S.MSG_WARNING, str(e))
            return
        except OSError as e:
            QMessageBox.critical(self, S.MSG_ERROR, S.ICON_STUDIO_SAVE_FAIL.format(error=e))
            return
        self.accept()
