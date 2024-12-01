# -*- coding: utf-8 -*-

from functools import partial
from pathlib import Path

from .pilot_functions import run_before_for_reho_falff_preproc


def test_reho_at_features_tab(
    snap_compare,
    start_app,
    work_dir_path: Path,
    downloaded_data_path: Path,
) -> None:
    """Adds ReHo features. All options are modified plus all 'Remove confounds' options are selected."""

    run_before_with_extra_args = partial(
        run_before_for_reho_falff_preproc,
        data_path=downloaded_data_path,
        work_dir_path=work_dir_path,
        stage="at_features_tab",
        feature_type="reho",
    )
    assert snap_compare(app=start_app, terminal_size=(204, 53), run_before=run_before_with_extra_args)


def test_reho_at_spec_preview(
    snap_compare,
    start_app,
    work_dir_path: Path,
    downloaded_data_path: Path,
) -> None:
    """Same as test_reho_at_features_tab but now we check the spec preview if the atlas pattern propagated to the spec
    file. Moreover, the smoothing should be in this case in the features (not in settings as usually)."""

    run_before_with_extra_args = partial(
        run_before_for_reho_falff_preproc,
        data_path=downloaded_data_path,
        work_dir_path=work_dir_path,
        stage="at_spec_preview",
        feature_type="reho",
    )

    assert snap_compare(app=start_app, terminal_size=(204, 53), run_before=run_before_with_extra_args)
