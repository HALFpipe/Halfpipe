# -*- coding: utf-8 -*-
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from textual import on
from textual.app import ComposeResult
from textual.containers import Container, Grid, Horizontal
from textual.message import Message
from textual.reactive import reactive
from textual.screen import ModalScreen
from textual.widget import Widget
from textual.widgets import Button, DirectoryTree, Input, Label


class FilteredDirectoryTree(DirectoryTree):
    def filter_paths(self, paths: Iterable[Path]) -> Iterable[Path]:
        return [path for path in paths if not path.name.startswith(".")]


class FileBrowserScreen(ModalScreen):
    """
    Here goes docstring.
    """

    CSS_PATH = ["tcss/file_browser.tcss"]

    def __init__(self, path_to, **kwargs) -> None:
        super().__init__(**kwargs)
        self.path_to = path_to

    def compose(self) -> ComposeResult:
        yield Container(
            FilteredDirectoryTree("/", classes="browse_tree"),
            Input(placeholder="Set path to the " + self.path_to, id="path_input_box2"),
            Grid(
                Button("Ok", classes="button ok"),
                Button("Cancel", classes="button cancel"),
            ),
            id="file_browser_screen",
        )

    @on(FilteredDirectoryTree.DirectorySelected, ".browse_tree")
    def on_filtered_directory_tree_directory_selected(self, message):
        self.selected_directory = message.path
        label = self.get_widget_by_id("path_input_box2")
        label.value = str(self.selected_directory)

    @on(Input.Submitted, "#path_input_box2")
    def update_from_input(self):
        self.selected_directory = self.get_widget_by_id("path_input_box2").value

    @on(Button.Pressed, "#file_browser_screen .ok")
    def ok(self):
        self._confirm_window()

    @on(Button.Pressed, "#file_browser_screen .cancel")
    def cancel(self):
        self._cancel_window()

    def key_escape(self):
        self._cancel_window()

    def _confirm_window(self):
        self.update_from_input()
        self.dismiss(self.selected_directory)

    def _cancel_window(self):
        self.dismiss(None)


class FileBrowser(Widget):
    """
    Here goes docstring.
    """

    DEFAULT_CSS = """
    FileBrowser {
        border: tall transparent;
        background: $boost;
        height: auto;
        width: auto;
        padding: 0 2;
    }
    """

    selected_path: reactive[str] = reactive("", init=False)

    @dataclass
    class Changed(Message):
        file_browser: "FileBrowser"
        selected_path: str

        @property
        def control(self):
            return self.file_browser

    def watch_selected_path(self) -> None:
        self.post_message(self.Changed(self, self.selected_path))

    def __init__(self, app, path_to, **kwargs) -> None:
        super().__init__(**kwargs)
        self.top_parent = app
        self.path_to = path_to

    def compose(self) -> ComposeResult:
        with Horizontal(id="file_browser"):
            yield Button("Browse", id="file_browser_edit_button", classes="button")
            yield Label(self.path_to + ":", id="path_input_box")

    @on(Button.Pressed, "#file_browser_edit_button")
    def open_browse_window(self):
        self.top_parent.push_screen(FileBrowserScreen(self.path_to), self.update_input)

    @on(Input.Submitted, "#path_input_box")
    def update_from_input(self):
        self.update_input(self.get_widget_by_id("path_input_box").value)

    def update_input(self, selected_path: str) -> None:
        if selected_path != "":
            label = self.get_widget_by_id("path_input_box")
            label.update(self.path_to + ": " + str(selected_path))
            label.value = self.path_to + ": " + str(selected_path)
            self.selected_path = str(selected_path)