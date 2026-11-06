# FDS 3.0 test plan: programmer

You check that the software is correct, and above all that the things that protect hardware and
people work as they should. **No hardware is needed**: everything below runs on a normal Windows
computer. The hardware behaviour itself is covered by the maintainer's report
(`FDS_maintainer_testreport.md`).

| | |
|---|---|
| Version tested (tag or commit) | |
| Date | |
| Name | |
| Windows version | |
| Python version(s) used | 3.12 (please use this one) |
| Time spent | |

Mark an item `- [x]` when it passes. If it fails, or you could not do it, leave it unmarked and
write why on the `Result:` line.

## A. Automated checks

Work from a fresh clone of the version under test, in a new virtual environment:

```
pip install -r requirements-dev.txt
```

- [ ] **P1** The install ends without errors. Python version (3.12):
  Result:
- [ ] **P2** The package tests pass and coverage stays at or above 80 %. Record the numbers.

  ```
  cd fus_ds_package
  pytest -m "not hardware"
  ```

  Result (passed / failed / coverage):
- [ ] **P3** The GUI tests pass.

  ```
  cd fus_ds_gui
  pytest
  ```

  Result (passed / failed):
- [ ] **P4** Style and quality checks pass in both folders: `flake8` is clean, `pylint` scores at least
  9.5 (CI pins `pylint==3.3.9`), and the duplication check stays under 3 %.

  ```
  pip install pylint==3.3.9 flake8
  cd fus_ds_package && flake8 && pylint fus_driving_systems --fail-under=9.5 && python dev_tools/check_duplication.py
  cd ../fus_ds_gui && flake8 && pylint fus_ds_gui --fail-under=9.5
  ```

  Result:
- [ ] **P5** The GitHub Actions run for the tested commit: `lint`, `security` and `test` ran for Python
  3.10 to 3.14. Everything is green, except that the dependency audit for 3.10 may show findings
  (known: `pillow` has fixes only for 3.11 and up, and that run does not block the workflow). Link:
  Result:
- [ ] **P6** The dependency audit for 3.11 to 3.14 is clean.
  Result:

## B. Packaging

Do this in a **new** environment, outside the repository folder, for at least one Python version.

```
python -m venv C:\Temp\fds_install_test
call C:\Temp\fds_install_test\Scripts\activate
pip install -r requirements.txt
```

- [ ] **P7** `pip list` shows the pinned dependencies and the package, and none of the test tools
  (`pytest`, `flake8`, `pylint`) or `PySide6`. The package is not an editable install: `pip show
  fus_driving_systems` has no "Editable project location" line.
  Result:
- [ ] **P8** From a folder outside the repository, the package comes from the environment and the
  `unifus` build is the one for your Python version.

  ```
  cd C:\Temp
  python -c "import fus_driving_systems; print(fus_driving_systems.__file__)"
  python -c "from fus_driving_systems.igt import unifus; print(unifus.__file__)"
  ```

  The first path is under `site-packages`. The second ends in `unifus.cpXYZ-win_amd64.pyd`, with
  `XYZ` your Python version (for example `cp311`).
  Result:
- [ ] **P9** The configuration and the calibration data are included in the installed package.

  ```
  python -c "import os, fus_driving_systems as p; d = os.path.dirname(p.__file__); print(os.path.exists(os.path.join(d, 'config', 'ds_config.ini')), os.path.isdir(os.path.join(d, 'igt', 'config', 'conversion_data')))"
  ```

  It prints `True True`.
  Result:
- [ ] **P10** The version numbers agree: `setup.py` of both packages, `CITATION.cff`, the citation in
  `README.md`, the table in `docs/python-usage.md` and the release notes. No stale `2.2.3` is left.

  ```
  git grep -n "2\.2\.3"
  ```

  Result:

## C. Safety-critical behaviour, without hardware

Run each snippet from `fus_ds_package` in the development environment. Each one is expected to
**fail with the stated error**, except where it says it succeeds.

```
from fus_driving_systems.tus_protocol import TUSProtocol
DS, TRAN = 'IGT-32-ch_comb_1x10-ch', 'IS_PCD15287_01001'
FOCUS, PRESS = 'Focus wrt exit plane [mm]', 'Max. pressure in free water [MPa]'
```

- [ ] **P11** A pressure above the configured maximum (1.4 MPa) is refused.

  ```
  TUSProtocol(DS).add_slot(TRAN, FOCUS, 20, PRESS, 1.5)
  ```

  `FDSSafetyError`: "...crossing the allowed limit of 1.40 [MPa]...". The same call with `1.0`
  succeeds.
  Result:
- [ ] **P12** An engineering-only power option cannot be used by accident.

  ```
  TUSProtocol(DS).add_slot(TRAN, 'Focus wrt mid bowl [mm]', 40, 'Amplitude [%]', 10)
  ```

  `FDSValidationError`: "Amplitude [%] mode is disabled. Enable engineering_mode...".
  Result:
- [ ] **P13** Nothing is sent without a connection, and nothing reconnects behind your back.

  ```
  from fus_driving_systems.igt.igt_ds import IGT
  igt = IGT(log_dir='C:/Temp/fds_probe')
  protocol = TUSProtocol(DS)
  protocol.add_slot(TRAN, FOCUS, 20, PRESS, 0.3)
  protocol.configure_timing(pulse_dur=1, pulse_rep_int=10, pulse_train_dur=10, pulse_train_rep_dur=1)
  igt.send_protocol(protocol)
  ```

  `FDSHardwareError`: "Not connected to the driving system, so send_protocol() cannot run. Call
  connect() first."
  Result:
- [ ] **P14** A protocol file that was edited after approval is refused, and the message names both ways to
  approve it again.

  ```
  import shutil
  from fus_driving_systems.protocol_loader import approve_protocol, load_protocol
  shutil.copy('../example_protocols/single_transducer/igt/direct_execute.yaml', 'C:/Temp/p.yaml')
  load_protocol('C:/Temp/p.yaml', require_hash=True)   # not approved yet: FDSSafetyError
  approve_protocol('C:/Temp/p.yaml')
  load_protocol('C:/Temp/p.yaml', require_hash=True)   # succeeds
  open('C:/Temp/p.yaml', 'a').write('\n# edited\n')
  load_protocol('C:/Temp/p.yaml', require_hash=True)   # FDSSafetyError: does not match its approved hash
  ```

  The last message mentions `python -m fus_driving_systems.approve_protocol` and the **Approve
  protocol** button in the GUI.
  Result:
- [ ] **P15** A changed pressure limit is announced. In `ds_config.ini` (inside the package you are
  testing), change `demo maximum pressure allowed in free water [mpa]`, start the GUI, and check
  that the console shows a warning about the modified limit. Restore the file afterwards.
  Result:
- [ ] **P16** A total duration that is not a whole number of repetitions is refused with a message that
  names the problem.

  ```
  protocol = TUSProtocol(DS)
  protocol.add_slot(TRAN, FOCUS, 20, PRESS, 0.3)
  protocol.configure_timing(pulse_dur=1, pulse_rep_int=300, pulse_train_rep_dur=80)
  IGT(log_dir='C:/Temp/fds_probe').validate_protocol(protocol)
  ```

  It returns a list with the message "Number of pulse trains within the pulse train repetition is not
  a whole number: ... is 266.67."
  Result:

- [ ] **P17** An interleaved group must have a total duration that is a whole number of rounds (one round is the
  pulse repetition intervals of all its protocols added up), and a duration that is not is refused.

  ```
  from fus_driving_systems.protocol_loader import load_protocol
  from fus_driving_systems.igt.igt_ds import IGT
  protocols, total_ms, *_ = load_protocol('../example_protocols/alternating_single_pulse_train/protocol.yaml')
  igt = IGT(log_dir='C:/Temp/fds_probe')
  for duration in (total_ms, total_ms + 50):
      try:
          igt.send_protocol(protocols, duration)
      except Exception as error:
          print(type(error).__name__, error)
  ```

  The first duration gets as far as the connection check (`FDSHardwareError`: "Not connected..."). The second
  fails earlier with `FDSValidationError`: "total_alternating_duration_ms of 80050 ms is not a whole number
  of rounds... 80050 / 200 = 400.25. Use a multiple of 200 ms...".
  Result:
- [ ] **P18** Every example protocol file loads, and the example scripts have no undefined names or syntax
  errors.

  ```
  cd fus_ds_package
  python -c "import glob; from fus_driving_systems.protocol_loader import load_protocol; [print(f, len(load_protocol(f)[0]), 'protocol(s)') for f in sorted(glob.glob('../example_protocols/**/*.yaml', recursive=True))]"
  flake8 --select=E9,F63,F7,F82 ../example_protocols
  ```

  Every file is listed without an error (the alternating example has 2 protocols, the others 1), and
  `flake8` prints nothing.
  Result:

## D. Code review of the critical paths

Read the code and answer the question at each point. Write the answer, even when it is "yes".

- [ ] **P19** `transducer_slot.py`: `_enforce_max_pressure()`, `_convert_press_to_ampl()` and
  `_convert_volt_to_ampl()`. Is the pressure limit applied on **every** path that leads to an
  amplitude (pressure in, amplitude in with engineering mode, voltage in, per-element values)? Does
  the range message state the true limit, where the amplitude reaches 100 %?
  Result:
- [ ] **P20** `igt/igt_ds.py`: `validate_protocol()`, `send_protocol()`, `execute_protocol()`,
  `_raise_if_run_failed()`. Can a protocol run that was not validated, or that does not match what was
  sent? Is a lost connection during a run always reported as an error, never as success?
  Result:
- [ ] **P21** `igt/igt_ds.py`: `connect()` and `disconnect()`. After a lost connection, does `connect()`
  wait longer between attempts? Does `disconnect()` still close the local connection when the driving
  system can no longer be reached?
  Result:
- [ ] **P22** `sonic_concepts/sonic_concepts_ds.py`: the handling of the `E1`, `E2` and `E3` responses and
  of the serial port. Is an error response always raised, never ignored?
  Result:
- [ ] **P23** `protocol_loader.py`: the hash check. Is there any way to load an approved protocol after it
  was changed?
  Result:
- [ ] **P24** `fus_ds_gui/executing/executing_panel.py`: `_on_worker_error()`, abort handling. After a worker
  error, is the connection released, and can an abort still reach the driving system while another
  call is blocked?
  Result:

## E. What was not covered

Write down anything you could not check, and anything you would want checked before this is used with
a subject.

## Sign-off

I did the items marked above, on the version and environment in the header.

Name:  Date:
