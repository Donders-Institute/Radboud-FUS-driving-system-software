# -*- coding: utf-8 -*-
"""
Fixtures local to igt_ds.py / utils.py tests.

The real unifus.pyd native extension is importable in this dev
environment and its plain data objects (Pulse, the various enums,
FUSListener) work standalone without touching any actual hardware --
verified interactively before writing these tests. So rather than
building a from-scratch fake unifus module, these fixtures only patch
the one call that *would* touch hardware: unifus.FUSSystem() (used by
connect()). Everything downstream of an established connection uses
self.gen/self.fus/self.listener directly, which the connected_instance
fixture below replaces with plain Mocks -- the same seam used for
citrus_ds.py/sonic_concepts_ds.py.
"""
import pytest

from fus_driving_systems.igt.igt_ds import IGT


@pytest.fixture
def igt_instance(tmp_path):
    """A bare IGT instance with an explicit tmp_path log_dir (IGT.__init__
    always does real faulthandler-log file I/O, so never rely on the
    default log_dir in tests)."""
    return IGT(log_dir=str(tmp_path))


@pytest.fixture
def connected_instance(tmp_path, mocker):
    """An IGT instance with gen/fus/listener replaced by plain Mocks,
    bypassing connect() entirely -- the natural seam for testing anything
    downstream of an established connection."""
    instance = IGT(log_dir=str(tmp_path))
    instance.gen = mocker.Mock()
    instance.fus = mocker.Mock()
    instance.listener = mocker.Mock()
    # Mirrors ExecListener's own default (unset/no error) -- a bare Mock() would otherwise
    # auto-create a truthy attribute here, which execute_protocol() now checks for a failed
    # protocol execution (see TestExecuteProtocol's exec_error_code tests).
    instance.listener.exec_error_code = None
    instance.n_channels = 2
    return instance


@pytest.fixture
def mock_fus_system(mocker):
    """Patches unifus.FUSSystem as imported in igt_ds.py; returns the Mock
    instance that connect() will end up assigning to self.fus. Only this
    one attribute is patched -- everything else on the real unifus module
    (enums, Pulse, sequenceDurationMs, setLogPath/setLogLevel) is safe to
    use as-is, see module docstring above."""
    mock_cls = mocker.patch("fus_driving_systems.igt.igt_ds.unifus.FUSSystem")
    return mock_cls.return_value
