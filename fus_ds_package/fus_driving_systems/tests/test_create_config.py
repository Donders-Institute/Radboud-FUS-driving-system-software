# -*- coding: utf-8 -*-
"""
Regression net against config drift: fus_driving_systems/config/ds_config.ini is a generated
artifact (its own header says so) -- it must never be hand-edited, only produced by running
create_config.py. This test actually re-runs create_config.py and diffs its output byte-for-byte
against the checked-in ds_config.ini, catching a generator change that wasn't followed by
regenerating the shipped file (the same class of drift the config.ini itself already warns
about for a hand-edit).
"""
import pathlib
import runpy

_CONFIG_DIR = pathlib.Path(__file__).resolve().parents[1] / 'config'
_CREATE_CONFIG_PATH = _CONFIG_DIR / 'create_config.py'
_SHIPPED_INI_PATH = _CONFIG_DIR / 'ds_config.ini'


def test_ds_config_ini_matches_freshly_generated_output(tmp_path, monkeypatch):
    # create_config.py writes CONFIG_FILE ('ds_config.ini') relative to the current working
    # directory -- run it from a scratch directory so this never touches the real shipped file.
    monkeypatch.chdir(tmp_path)

    runpy.run_path(str(_CREATE_CONFIG_PATH), run_name='regenerate_ds_config_for_test')

    generated_contents = (tmp_path / 'ds_config.ini').read_text(encoding='utf-8')
    shipped_contents = _SHIPPED_INI_PATH.read_text(encoding='utf-8')

    assert generated_contents == shipped_contents, (
        'ds_config.ini no longer matches create_config.py\'s own output -- regenerate it by '
        'running create_config.py from inside fus_driving_systems/config/ and committing the '
        'result.')
