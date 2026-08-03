# -*- coding: utf-8 -*-
"""
Tests for fus_driving_systems.config.config.

config_info is a real, shared ConfigParser populated once from the real
ds_config.ini at import time. read_config/read_additional_config mutate it
in place (merge), which is why patch_config (see conftest.py) works for
per-key overrides elsewhere in this suite -- but a bulk merge test here
needs a full snapshot/restore instead of single-key tracking, hence the
local isolated_config_info fixture below rather than reusing patch_config.
"""
import io

import pytest

from fus_driving_systems.config import config as config_module


@pytest.fixture
def isolated_config_info():
    """Snapshots the full config_info content and restores it afterwards,
    so bulk-merging a test .ini file doesn't leak into other tests."""
    buffer = io.StringIO()
    config_module.config_info.write(buffer)
    snapshot = buffer.getvalue()

    yield config_module.config_info

    config_module.config_info.clear()
    config_module.config_info.read_string(snapshot)


def test_read_config_raises_file_not_found_for_missing_file(tmp_path):
    missing_path = tmp_path / "does_not_exist.ini"
    with pytest.raises(FileNotFoundError):
        config_module.read_config(missing_path)


def test_read_config_merges_new_file_into_shared_config_info(isolated_config_info, tmp_path):
    ini_path = tmp_path / "extra.ini"
    ini_path.write_text("[UnitTestSection]\nsome_key = some_value\n")

    config_module.read_config(ini_path)

    assert isolated_config_info["UnitTestSection"]["some_key"] == "some_value"


def test_read_additional_config_raises_file_not_found_for_missing_file(tmp_path):
    missing_path = tmp_path / "does_not_exist.ini"
    with pytest.raises(FileNotFoundError):
        config_module.read_additional_config(missing_path)


def test_read_additional_config_merges_into_shared_config_info(isolated_config_info, tmp_path):
    ini_path = tmp_path / "extra.ini"
    ini_path.write_text("[UnitTestSection]\nanother_key = another_value\n")

    config_module.read_additional_config(ini_path)

    assert isolated_config_info["UnitTestSection"]["another_key"] == "another_value"


def test_sync_config_replaces_module_reference_but_does_not_propagate_to_earlier_consumers():
    """
    Characterizes CURRENT (broken/unused) behavior: sync_config() rebinds
    config.py's own 'config_info' name to a new object, but every module
    that already did 'from ...config import config_info as config' at its
    own import time (driving_system.py, transducer.py, sequence.py, the
    hardware subpackages) keeps pointing at the OLD object -- the rebind
    never reaches them. sync_config() is confirmed unused anywhere in the
    codebase; this test documents why it wouldn't work if something started
    calling it, rather than asserting it's correct.
    """
    import configparser

    from fus_driving_systems import driving_system

    original_config_info = config_module.config_info
    new_config = configparser.ConfigParser()
    new_config["Marker"] = {"present": "yes"}

    try:
        config_module.sync_config(new_config)

        assert config_module.config_info is new_config
        assert driving_system.config is original_config_info
        assert driving_system.config is not new_config
    finally:
        config_module.sync_config(original_config_info)
