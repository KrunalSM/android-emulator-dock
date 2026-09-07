"""Workspace manager handling layout organization (Single, Columns, Grid) and multiple slots."""

from typing import List, Optional
from PyQt6.QtWidgets import QWidget, QGridLayout, QSizePolicy
from aed.workspace.slot import EmulatorSlot

class WorkspaceLayoutManager(QWidget):
    """Manages slot arrangement in Single, Two-Column, or 2x2 Grid modes."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._slots: List[EmulatorSlot] = []
        self._mode = "AUTO"  # "AUTO", "SINGLE", "COLUMNS", "GRID"

        self.grid_layout = QGridLayout(self)
        self.grid_layout.setContentsMargins(8, 8, 8, 8)
        self.grid_layout.setSpacing(8)

    @property
    def slots(self) -> List[EmulatorSlot]:
        return list(self._slots)

    def add_slot(self, slot: EmulatorSlot):
        self._slots.append(slot)
        slot.close_requested.connect(self.remove_slot)
        self.relayout()

    def remove_slot(self, slot: EmulatorSlot):
        if slot in self._slots:
            self._slots.remove(slot)
            slot.instance.stop()
            self.grid_layout.removeWidget(slot)
            slot.setParent(None)
            slot.deleteLater()
            self.relayout()

    def set_mode(self, mode: str):
        self._mode = mode
        self.relayout()

    def relayout(self):
        # Clear layout items without deleting slots
        while self.grid_layout.count() > 0:
            item = self.grid_layout.takeAt(0)

        count = len(self._slots)
        if count == 0:
            return

        if self._mode == "SINGLE" or (self._mode == "AUTO" and count == 1):
            for i, slot in enumerate(self._slots):
                if i == 0:
                    slot.setVisible(True)
                    self.grid_layout.addWidget(slot, 0, 0)
                else:
                    slot.setVisible(False)
        elif self._mode == "COLUMNS" or (self._mode == "AUTO" and count == 2):
            for i, slot in enumerate(self._slots):
                slot.setVisible(True)
                self.grid_layout.addWidget(slot, 0, i)
        else:  # GRID or AUTO with 3+
            cols = 2
            for i, slot in enumerate(self._slots):
                slot.setVisible(True)
                r = i // cols
                c = i % cols
                self.grid_layout.addWidget(slot, r, c)
