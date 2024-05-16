# -*- coding: utf-8 -*-
from textual.containers import Horizontal, Vertical
from textual.widgets import Button, Label

from .draggable_modal_screen import DraggableModalScreen


class FalseInputWarning(DraggableModalScreen):
    CSS_PATH = ["tcss/false_input_warning.tcss"]

    def __init__(self, warning_message, title="", id: str | None = None, classes: str | None = None) -> None:
        self.warning_message = warning_message
        super().__init__(id=id, classes=classes)
        self.title_bar.title = title

    def on_mount(self) -> None:
        self.content.mount(
            Vertical(
                Label(self.warning_message),
                Horizontal(Button("Ok", variant="error")),
            )
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.dismiss()

    def key_escape(self):
        self.dismiss()
