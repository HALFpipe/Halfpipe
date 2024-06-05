# -*- coding: utf-8 -*-
from dataclasses import dataclass

from textual import on
from textual.app import ComposeResult
from textual.containers import Grid, ScrollableContainer, Vertical
from textual.message import Message
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import Input, Select, SelectionList, Static, Switch
from textual.widgets.selection_list import Selection

from ....collect.events import collect_events
from ....ingest.events import ConditionFile
from ....model.filter import FilterSchema
from ...utils.custom_switch import TextSwitch
from .model_conditions_and_contrasts import ModelConditionsAndContrasts


class SwitchWithInputBox(Widget):
    value: reactive[bool] = reactive(None, init="")
    switch_value: reactive[bool] = reactive(None, init=False)

    @dataclass
    class Changed(Message):
        switch_with_input_box: "SwitchWithInputBox"
        value: str

        @property
        def control(self):
            """Alias for self.file_browser."""
            return self.switch_with_input_box

    @dataclass
    class SwitchChanged(Message):
        switch_with_select: "SwitchWithInputBox"
        switch_value: bool

        @property
        def control(self):
            """Alias for self.file_browser."""
            return self.switch_with_input_box

    def __init__(self, label="", value: str | None = None, switch_value: bool = False, **kwargs) -> None:
        self.label = label
        self._reactive_switch_value = switch_value
        self._reactive_value = str(value) if value is not None else None

        super().__init__(**kwargs)

    def watch_value(self) -> None:
        self.post_message(self.Changed(self, self.value))

    def watch_switch_value(self) -> None:
        self.post_message(self.SwitchChanged(self, self.switch_value))

    def compose(self) -> ComposeResult:
        yield Grid(
            Static(self.label),
            TextSwitch(value=self.value is not None),
            Input(value=self.value, placeholder="Value", id="input_switch_input_box"),
        )

    def update_label(self, label):
        self.query_one(Static).update(label)

    def on_mount(self):
        if self.switch_value is True or self.value is not None:
            self.get_widget_by_id("input_switch_input_box").styles.visibility = "visible"
        else:
            self.get_widget_by_id("input_switch_input_box").styles.visibility = "hidden"

    # def on_switch_changed(self):
    # last_switch = self.query("Switch").last()
    # if last_switch.value:
    # self.get_widget_by_id("input_switch_input_box").styles.visibility = "visible"
    # else:
    # self.get_widget_by_id("input_switch_input_box").styles.visibility = "hidden"
    # self.value = 0

    @on(Switch.Changed)
    def on_switch_changed(self, message):
        self.switch_value = message.value
        if self.switch_value is True:
            self.get_widget_by_id("input_switch_input_box").styles.visibility = "visible"
        else:
            self.get_widget_by_id("input_switch_input_box").styles.visibility = "hidden"

    @on(Input.Changed, "#input_switch_input_box")
    def update_from_input(self):
        self.value = str(self.get_widget_by_id("input_switch_input_box").value)


class SwitchWithSelect(SwitchWithInputBox):
    @dataclass
    class Changed(Message):
        switch_with_select: "SwitchWithSelect"
        value: str

        @property
        def control(self):
            """Alias for self.file_browser."""
            return self.switch_with_select

    @dataclass
    class SwitchChanged(Message):
        switch_with_select: "SwitchWithSelect"
        switch_value: bool

        @property
        def control(self):
            """Alias for self.file_browser."""
            return self.switch_with_select

    def __init__(self, label="", options: list | None = None, **kwargs) -> None:
        self.label = label
        super().__init__(label=label, **kwargs)
        self.options = [] if options is None else options

    def compose(self) -> ComposeResult:
        yield Grid(
            Static(self.label),
            TextSwitch(value=self.switch_value),
            Select(
                [(str(value[0]), value[1]) for value in self.options],
                value=self.options[0][1],
                allow_blank=False,
                id="input_switch_input_box",
            ),
        )

    @on(Select.Changed, "#input_switch_input_box")
    def update_from_input(self):
        self.value = str(self.get_widget_by_id("input_switch_input_box").value)


class TaskBased(Widget):
    def __init__(self, app, ctx, available_images, this_user_selection_dict, **kwargs) -> None:
        """At the beginning there is a bunch of 'if not in'. If a new widget is created the pass
        this_user_selection_dict is empty and the nested keys need some initialization. On the other
        hand, if a new widget is created automatically then this dictionary is not empty and these
        values are then used for the various widgets within this widget.
        """
        super().__init__(**kwargs)
        self.top_parent = app
        self.ctx = ctx
        self.available_images = available_images

        self.feature_dict = this_user_selection_dict["features"]
        self.setting_dict = this_user_selection_dict["settings"]

        if "contrasts" not in self.feature_dict:
            self.feature_dict["contrasts"] = []
        if "type" not in self.feature_dict:
            self.feature_dict["type"] = "task_based"
        if "bandpass_filter" not in self.setting_dict:
            self.setting_dict["bandpass_filter"] = {"type": "gaussian", "hp_width": None, "lp_width": None}
        if "smoothing" not in self.setting_dict:
            self.setting_dict["smoothing"] = {"fwhm": None}

        if "filters" not in self.setting_dict:
            self.setting_dict["filters"] = [{"type": "tag", "action": "include", "entity": "task", "values": []}]
        if "grand_mean_scaling" not in self.setting_dict:
            self.setting_dict["grand_mean_scaling"] = {"mean": 10000.0}
        self.images_to_use = {"task": {task: False for task in self.available_images["task"]}}
        for image in self.setting_dict["filters"][0]["values"]:
            self.images_to_use["task"][image] = True

        confounds_options = {
            "ICA-AROMA": ["ICA-AROMA", False],
            "(trans|rot)_[xyz]": ["Motion parameters", False],
            "(trans|rot)_[xyz]_derivative1": ["Derivatives of motion parameters", False],
            "(trans|rot)_[xyz]_power2": ["Motion parameters squared", False],
            "(trans|rot)_[xyz]_derivative1_power2": ["Derivatives of motion parameters squared", False],
            "a_comp_cor_0[0-4]": ["aCompCor (top five components)", False],
            "white_matter": ["White matter signal", False],
            "csf": ["CSF signal", False],
            "global_signal": ["Global signal", False],
        }

        if "confounds_removal" in self.setting_dict:
            for confound in self.setting_dict["confounds_removal"]:
                confounds_options[confound][1] = True

        self.confounds_options = confounds_options
        print("111qqqqqqqqqqqqqqqqqqqq", this_user_selection_dict)
        print("ppppppppppppppppppp", self.feature_dict)

    def compose(self) -> ComposeResult:
        # note_1 = "▪️ Grand mean scaling will be applied with a mean of 10000.0"
        # note_2 = "▪️ Temporal filtering will be applied using a gaussian-weighted filter"
        # Here I need to get all possible conditions based on all possible images.
        all_condition_dict = {}
        all_possible_conditions = []
        for v in self.images_to_use["task"].keys():
            all_condition_dict[v] = self.extract_conditions(entity="task", values=[v])
            all_possible_conditions += self.extract_conditions(entity="task", values=[v])

        with ScrollableContainer(id="top_container_task_based"):
            yield Grid(
                SelectionList[str](
                    *[
                        Selection(image, image, self.images_to_use["task"][image])
                        for image in self.images_to_use["task"].keys()
                    ],
                    id="images_to_use_selection",
                ),
                id="images_to_use",
                classes="components",
            )
            with Vertical(id="preprocessing", classes="components"):
                yield SwitchWithInputBox(
                    label="Smoothing (FWHM in mm)",
                    value=self.setting_dict["smoothing"]["fwhm"],
                    classes="switch_with_input_box",
                    id="smoothing",
                )

                #      yield Static(note_1 + "\n" + note_2, classes="components", id="notes")
                yield SwitchWithInputBox(
                    label="Grand mean scaling",
                    value=self.setting_dict["grand_mean_scaling"]["mean"],
                    classes="switch_with_input_box additional_preprocessing_settings",
                    id="grand_mean_scaling",
                )
                yield SwitchWithSelect(
                    "Temporal filter",
                    options=[("Gaussian-weighted", "gaussian"), ("Frequency-based", "frequency_based")],
                    switch_value=True,
                    id="bandpass_filter_type",
                    classes="additional_preprocessing_settings",
                )
                yield SwitchWithInputBox(
                    label="Low-pass temporal filter width \n(in seconds)",
                    value=self.setting_dict["bandpass_filter"]["lp_width"],
                    classes="switch_with_input_box",
                    id="bandpass_filter_lp_width",
                )
                yield SwitchWithInputBox(
                    label="High-pass temporal filter width \n(in seconds)",
                    value=self.setting_dict["bandpass_filter"]["hp_width"],
                    classes="switch_with_input_box",
                    id="bandpass_filter_hp_width",
                )
            yield ModelConditionsAndContrasts(
                self.top_parent,
                all_possible_conditions,
                feature_contrasts_dict=self.feature_dict["contrasts"],
                id="model_conditions_and_constrasts",
                classes="components",
            )
            yield Grid(
                SelectionList[str](
                    *[
                        Selection(self.confounds_options[key][0], key, self.confounds_options[key][1])
                        for key in self.confounds_options
                    ],
                    classes="components",
                    id="confounds_selection",
                ),
                id="confounds",
                classes="components",
            )

    def on_mount(self) -> None:
        print("mmmmmmmmmmmmmmmmmmmm mount superclass")
        self.get_widget_by_id("images_to_use").border_title = "Images to use"
        self.get_widget_by_id("confounds").border_title = "Remove confounds"
        self.get_widget_by_id("preprocessing").border_title = "Preprocessing setting"
        if self.get_widget_by_id("bandpass_filter_type").switch_value is False:
            self.get_widget_by_id("bandpass_filter_lp_width").styles.visibility = "hidden"
            self.get_widget_by_id("bandpass_filter_hp_width").styles.visibility = "hidden"

        # self.get_widget_by_id("temporal_filter").styles.visibility = "hidden"
        # self.get_widget_by_id("grand_mean_scaling").styles.visibility = "hidden"
        # on_mount in subclasses is not entirely overridden and this one has also some effect
        # try:
        # self.get_widget_by_id("notes").border_title = "Notes"
        # self.get_widget_by_id("bandpass_filter_type").styles.visibility = "hidden"
        # self.get_widget_by_id("grand_mean_scaling").styles.visibility = "hidden"
        # except:  # noqa E722
        # pass

    @on(SelectionList.SelectedChanged, "#images_to_use_selection")
    def _on_selection_list_changed_images_to_use_selection(self):
        # this has to be split because when making a subclass, the decorator causes to ignored redefined function in the
        # subclass
        self.update_conditions_table()

    def update_conditions_table(self):
        condition_list = []
        for value in self.get_widget_by_id("images_to_use_selection").selected:
            condition_list += self.extract_conditions(entity="task", values=[value])
        self.feature_dict["conditions"] = condition_list
        self.setting_dict["filters"][0]["values"] = self.get_widget_by_id("images_to_use_selection").selected
        # force update of model_conditions_and_constrasts to reflect conditions given by the currently selected images
        self.get_widget_by_id("model_conditions_and_constrasts").condition_values = condition_list

    @on(SelectionList.SelectedChanged, "#confounds_selection")
    def feed_feature_dict_confounds(self):
        confounds = self.get_widget_by_id("confounds_selection").selected.copy()
        # "ICA-AROMA" is in a separate field, so here this is taken care of
        if "ICA-AROMA" in self.get_widget_by_id("confounds_selection").selected:
            confounds.remove("ICA-AROMA")
            self.setting_dict["ica_aroma"] = True
        else:
            self.setting_dict["ica_aroma"] = False

        self.setting_dict["confounds_removal"] = confounds

    @on(SwitchWithSelect.SwitchChanged, "#bandpass_filter_type")
    def setting_change_bandpass_filter_type(self, message):
        print("heeeeeeeeeeeeeeeeere", message.switch_value)
        if message.switch_value is True:
            self.get_widget_by_id("bandpass_filter_lp_width").styles.visibility = "visible"
            self.get_widget_by_id("bandpass_filter_hp_width").styles.visibility = "visible"
            self.get_widget_by_id("preprocessing").styles.height = 19
        else:
            self.get_widget_by_id("bandpass_filter_lp_width").styles.visibility = "hidden"
            self.get_widget_by_id("bandpass_filter_hp_width").styles.visibility = "hidden"
            self.get_widget_by_id("preprocessing").styles.height = 13

    @on(SwitchWithInputBox.Changed)
    @on(SwitchWithSelect.Changed)
    def on_switch_with_input_box_changed(self, message):
        # todo, need some unified simple global approach for the value passing
        the_id = message.control.id
        if message.control.id == "bandpass_filter_type":
            if message.value == "frequency_based":
                self.get_widget_by_id("bandpass_filter_lp_width").update_label("Low-pass temporal filter width \n(in Hertz)")
                self.get_widget_by_id("bandpass_filter_hp_width").update_label("Low-pass temporal filter width \n(in Hertz)")
            elif message.value == "gaussian":
                self.get_widget_by_id("bandpass_filter_lp_width").update_label("Low-pass temporal filter width \n(in seconds)")
                self.get_widget_by_id("bandpass_filter_hp_width").update_label("Low-pass temporal filter width \n(in seconds)")
        print("dddddddddddddddddddddddddd", the_id, message.value)
        if "bandpass_filter" in the_id:
            the_id = the_id.replace("bandpass_filter_", "")
            self.setting_dict["bandpass_filter"][the_id] = message.value
        elif "grand_mean_scaling" in the_id:
            self.setting_dict[the_id]["mean"] = message.value
        elif "smoothing" in the_id:
            self.setting_dict[the_id]["fwhm"] = message.value
        else:
            self.feature_dict[the_id] = message.value

    def extract_conditions(self, entity, values):
        filter_schema = FilterSchema()
        _filter = filter_schema.load(
            {
                "type": "tag",
                "action": "include",
                "entity": entity,
                "values": values,
            }
        )
        return get_conditions(self.ctx, _filter)


def get_conditions(ctx, _filter):
    bold_file_paths = find_bold_file_paths(ctx, _filter)

    conditions: list[str] = list()
    seen = set()
    for bold_file_path in bold_file_paths:
        event_file_paths = collect_events(ctx.database, bold_file_path)
        if event_file_paths is None:
            continue

        if event_file_paths in seen:
            continue

        cf = ConditionFile(data=event_file_paths)
        for condition in cf.conditions:  # maintain order
            if condition not in conditions:
                conditions.append(condition)

        seen.add(event_file_paths)

    return conditions


def find_bold_file_paths(ctx, _filter):
    bold_file_paths = ctx.database.get(datatype="func", suffix="bold")

    if bold_file_paths is None:
        raise ValueError("No BOLD files in database")

    #  filters = ctx.spec.settings[-1].get("filters")
    bold_file_paths = set(bold_file_paths)

    if _filter is not None:
        bold_file_paths = ctx.database.applyfilters(bold_file_paths, [_filter])

    return bold_file_paths


def tag_the_string(tagvals):
    return [f'"{tagval}"' for tagval in tagvals]