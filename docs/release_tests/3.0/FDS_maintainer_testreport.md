# FDS 3.0 test report: maintainer

What the maintainer tested on hardware and with instruments, next to what the reviewers did
(`FDS_user_testreport.md`, `FDS_programmer_testreport.md`).

| | |
|---|---|
| Version tested (tag or commit) | |
| Date(s) | |
| Name | |
| Driving systems used (and which has an active calibration) | |
| Transducers used (and which were real or stand-ins on a dummy load) | |

Mark an item `- [x]` when it passes. If it fails, or was not done, leave it unmarked and write why.

## A. Hardware tests per Python version

Run `run_hardware_tests.bat` (see "Hardware tests" in `docs/python-usage.md`) with `VENV_DIR` set to the
environment of each version. For the calibrated system, set the driving system and transducer that have an
active calibration, so that `test_measured_voltage_follows_the_calibration` runs and is not skipped.
Paste the "What the hardware tests show" block of each run in the notes.

| Python | `unifus` build | pandas | Driving system | Passed | Failed | Skipped | Notes |
|---|---|---|---|---|---|---|---|
| 3.10 | `unifus.cp310-win_amd64.pyd` | 2.2.2 | | | | | |
| 3.11 | `unifus.cp311-win_amd64.pyd` | 2.2.2 | | | | | |
| 3.12 | `unifus.cp312-win_amd64.pyd` | 2.2.2 | | | | | |
| 3.13 | `unifus.cp313-win_amd64.pyd` | 3.1.0 | | | | | |
| 3.14 | `unifus.cp314-win_amd64.pyd` | 3.1.0 | | | | | |

- [ ] **M1** The hardware tests ran on all five versions.
- [ ] **M2** On a system with an active calibration, the measured voltage matches the calibration on every version.
  Result:

## B. Oscilloscope checks (Python 3.10 and 3.11)

Same protocol on each build, with the `unifus` from the previous release (v2.2.5) next to the new
0.17.1 build where possible (only 3.10 has both). Record what you measure.

| Quantity | Setting | 3.10, previous `unifus` | 3.10, 0.17.1 | 3.11, 0.17.1 |
|---|---|---|---|---|
| Frequency | | | | |
| Pulse duration | | | | |
| Pulse repetition interval | | | | |
| Pulses per train | | | | |
| Amplitude, step 1 | | | | |
| Amplitude, step 2 | | | | |
| Amplitude, step 3 | | | | |
| Phase per channel, with dephasing | | | | |
| Trigger delay (trigger to first pulse) | | | | |
| Time from `abort()` to the output stopping | | | | |

- [ ] **M3** The new builds give the same output as the previous one within your tolerance. Tolerance used:
  Result:

## C. Pressure and amplitude on the calibrated system

On the system with an active calibration that the hardware tests above ran on.

- [ ] **M4** Pressure to amplitude conversion on the calibrated system: send a protocol set in pressure and a native
  one with the resulting amplitude and focus, and see that both run.
  Result:
- [ ] **M5** The pressure limit and the 100 % limit give the messages described in the programmer's plan on this system.
  Result:

## D. The example scripts on a dummy load

Every example file was touched for this release (one driving system serial per script, new hints, the
Sonic Concepts scripts). Run each script from start to end on the dummy load, at a safe power. Some
need a driving system you do not have; mark those as not done and write why.

| Folder | Script | Reads | Needs |
|---|---|---|---|
| `single_transducer/igt` | `standalone_plain.py` | | IGT 32 ch, 1 x 10 ch |
| `single_transducer/igt` | `standalone_direct_execute.py` | `direct_execute.yaml` | IGT 32 ch, 1 x 10 ch |
| `single_transducer/igt` | `standalone_wait_for_trigger.py` | `wait_for_trigger.yaml` | IGT and a trigger |
| `single_transducer/igt` | `standalone_wait_for_trigger_poll.py` | `wait_for_trigger.yaml` | IGT and a trigger |
| `single_transducer/sonic_concepts` | `standalone_plain.py` | | Sonic Concepts |
| `single_transducer/sonic_concepts` | `standalone_yaml.py` | `protocol.yaml` | Sonic Concepts |
| `alternating_single_pulse_train` | `standalone_plain.py` | | IGT 32 ch, 2 x 10 ch |
| `alternating_single_pulse_train` | `standalone_yaml.py` | `protocol.yaml` | IGT 32 ch, 2 x 10 ch |
| `switch_active_transducer` | `standalone_plain.py` | | IGT 32 ch, 2 x 10 ch |
| `switch_active_transducer` | `standalone_yaml.py` | `protocol.yaml` | IGT 32 ch, 2 x 10 ch |
| `two_transducers_simultaneous` | `standalone_plain.py` | | IGT 32 ch, 2 x 10 ch |
| `two_transducers_simultaneous` | `standalone_yaml.py` | `protocol.yaml` | IGT 32 ch, 2 x 10 ch |

- [ ] **M6** Every script above ran from start to end. Scripts not run, and why:
  Result:
- [ ] **M7** The ready-made program (the Windows build of the tested commit, not the Python route) connects to the
  IGT, sends, executes and aborts on the dummy load. This is the only check that the bundled `unifus` works
  with a real connection.
  Result:
- [ ] **M8** The user plan's section E (hardware) was done by the user. If not, write down who did the same
  steps instead and when, or that it was not done. The release notes must say the same.
  Result:

## E. The earlier hardware test plan

Mark what you did and note the outcome for each. Items that the plans of the reviewers cover are marked
with their plan.

**GUI**
- [ ] gui-1 Planning tab: build a full protocol end to end
- [ ] gui-2 Save, Load and Approve in the Planning tab
- [ ] gui-3 Demo mode versus Advanced mode toggle
- [ ] gui-4 The equipment picker reflects the current catalog
- [ ] gui-5 Executing panel against the Mock driving system (also user U24 to U29)
- [ ] gui-6 Trigger arming from the GUI, both modes, both driving system families
- [ ] gui-7 The Abort button reaches real IGT hardware while the main thread is blocked
- [ ] gui-8 Error dialogs show validation and hardware errors instead of crashing
- [ ] gui-9 Exploratory pass: state left behind after a change

**IGT, essential**
- [ ] igt-p1-1 An inactive transducer is rejected
- [ ] igt-p1-2 Crash detection catches and archives a crash (#126)
- [ ] igt-p1-3 A dropped connection gives a clear error, nothing reconnects by itself, and the next connect waits longer (#163)
- [ ] igt-p1-4 `abort()` from a second thread while the main thread is blocked

**IGT, further**
- [ ] igt-p2-1 Trigger modes: `TriggerOnePulseTrain` and `TriggerWholeProtocol`
- [ ] igt-p2-2 Multi-buffer behavior
- [ ] igt-p2-3 Interleaved protocols in one `send_protocol()` call
- [ ] igt-p2-4 Native versus calibrated power and focus (see also M4)
- [ ] igt-p2-5 Voltage feedback tracker (#137)
- [ ] igt-p2-8 The measured voltage follows the calibration (see also M2)
- [ ] igt-p2-6 A pressure-limit warning appears when the limit is raised by hand (also programmer P15)
- [ ] igt-p2-7 Electrical characterization into a dummy load

**Sonic Concepts**
- [ ] sc-1 End-to-end smoke test: connect, send, execute, disconnect
- [ ] sc-2 Pulse timing appears in the send confirmation
- [ ] sc-3 Native power (`GLOBALPOWER`) accuracy
- [ ] sc-7 `abort()` while a pulse train is running
- [ ] sc-4 The ceiling for the number of elements and channels triggers correctly
- [ ] sc-5 Focus range edges for at least one transducer
- [ ] sc-6 The transducer selection confirmation dialog

**CITRUS**
- [ ] citrus-1 Connect, send, execute, disconnect smoke test
- [ ] citrus-2 Sequence validation rejects an obviously invalid protocol

**Core**
- [ ] core-1 A tampered protocol file is rejected (also programmer P14)
- [ ] core-2 The configuration drift tests catch drift
- [ ] core-3 Failures that used to end the program now raise an `FDSError`
- [ ] core-4 An unconfirmed IGT execution is detected and not reported as success (#78)

**Package**
- [ ] pkg-1 A fresh install on a clean machine, following the README (also user U7 to U11)
- [ ] pkg-2 A normal install pulls no test-only dependencies and is not editable (also programmer P7)
- [ ] pkg-3 At least one example protocol runs end to end (see section D for all of them)

## F. Not required for this release

- Acoustic pressure and focus with a hydrophone. Optional for this release, as nothing in it changes
  the calibration or the conversion math. Planned for December; the result will be added then.

## Sign-off

I did the items marked above, on the version and environment in the header.

Name:  Date:
