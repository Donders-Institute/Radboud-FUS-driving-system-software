[← Back to README](../README.md)

# 🔊 Building and Loading Protocols

This covers two ways to define a protocol: Option 1 from a YAML file or Option 2 directly in
Python. It also describes how to wire FDS calls into a script you already have.

## 📄 Option 1: Load a Protocol from a YAML File <a name="load-yaml"></a>

Open [direct_execute.yaml](../example_protocols/single_transducer/igt/direct_execute.yaml) and its
matching [standalone_direct_execute.py](../example_protocols/single_transducer/igt/standalone_direct_execute.py)
alongside this section: both are real, working examples you can follow along with, and start from
for your own protocol.

Rather than defining a `TUSProtocol` directly in Python (Option 2 below), you can load one from a
YAML file instead: a simpler alternative aimed specifically at researchers who need to design a
protocol once and want to separate it from code. You don't need to hand-write the YAML either: for a single, non-interleaved protocol, the GUI's
Planning tab can build, save, and load these same `protocol.yaml` files directly (see
[Download the GUI](../README.md#gui) to install it); the GUI doesn't yet support editing an
interleaved file (more than one `protocols` entry).

A `protocol.yaml` might look like this:

```yaml
driving_sys_serial: IGT-32-ch_comb_1x10-ch  # print(driving_system.get_ds_serials()) for options

# 'None' means no trigger at all -- the protocol is executed directly via execute_protocol(),
# which is exactly what this file is for. trigger_option is whole-file, not per-protocol -- it's a
# parameter of IGT.send_protocol()/wait_for_trigger()/execute_protocol() itself, not of any one
# protocol below.
trigger_option: None

protocols:
  - slots:
      - transducer_serial: IS_PCD15287_01001  # print(transducer.get_tran_serials()) for options

        focus_option: Focus wrt exit plane [mm]
        focus_value: 80  # [mm], focal depth w.r.t. the exit plane and FWHM middle

        power_option: Max. pressure in free water [MPa]
        power_value: 0.3  # [MPa], maximum pressure in free water

        oper_freq: 300  # [kHz], operating frequency -- optional, defaults to the transducer's
                        # own fundamental frequency when omitted

        # Degree used to dephase every nth element. null = no dephasing. One value (>0) is the
        # degree of dephasing, e.g. 90 with 4 elements: element 1: 0, element 2: 90, element 3:
        # 180, element 4: 270. When the number of values matches the number of elements, this
        # overrides the phases that would otherwise be calculated from focus_value.
        dephasing_degree: null

    timing:
      # Each field below is deliberately a genuinely different value from the one before it (not
      # just mirroring the level below), to show the full timing hierarchy in one place: one
      # pulse, repeated into a pulse train, itself repeated some number of times.
      pulse_dur: 10          # [ms], pulse duration -- the only required timing field

      # pulse ramping -- both optional, default to "no ramping" / 0 when omitted
      pulse_ramp_shape: Rectangular - no ramping
      pulse_ramp_dur: 0      # [ms], ramp duration, with at least 70 us between ramp up/down

      pulse_rep_int: 50      # [ms], pulse repetition interval -- one pulse every 50 ms
      pulse_train_dur: 200   # [ms], pulse train duration -- 4 pulses per train (200 / 50)

      # pulse_train_rep_int/pulse_train_rep_dur (how many times the pulse train repeats) only
      # apply when trigger_option is not TriggerOnePulseTrain -- both optional; omitting both
      # means "repeat exactly once".
      # a new train starts every 400 ms (200 ms train, then a 200 ms gap before the next)
      pulse_train_rep_int: 400  # [ms]
      # keeps repeating for 2 s in total, i.e. 5 repetitions of the whole train (2000 / 400)
      pulse_train_rep_dur: 2    # [s]

# total_alternating_duration_ms is only needed when protocols above has more than one entry
# (interleaving several protocols) -- omit it entirely for a single protocol like this one.
```

This is the same content as [direct_execute.yaml](../example_protocols/single_transducer/igt/direct_execute.yaml) above, with only its file-specific header comment left out.

This gets read back into Python with `load_protocol()`:

```python
from fus_driving_systems.protocol_loader import load_protocol

protocols, total_alternating_duration_ms, trigger_option, n_triggers, buffer_num = load_protocol(
    'direct_execute.yaml'
)
ds.send_protocol(protocols, total_alternating_duration_ms, buffer_num)
ds.execute_protocol(protocols, total_alternating_duration_ms, buffer_num)
```

- `load_protocol(yaml_path, engineering_mode=False, require_hash=False)`: parses the YAML file into ready-to-use `TUSProtocol` object(s). Some options in the file are gated behind `engineering_mode` as an institutional safety policy choice; see `engineering-only options` in [Configuration](configuration.md#safety-setting) for which ones and why (it's a Python-level argument here, not something you set inside the YAML itself). Returns a 5-tuple, meant to be forwarded straight into `send_protocol()`/`wait_for_trigger()`/`execute_protocol()`, exactly as shown above:
  - `protocols`: always a list (even for a single protocol)
  - `total_alternating_duration_ms`: the total duration [ms] the whole interleaved/alternating group repeats for; `None` unless the file describes more than one protocol to interleave, required (and must be greater than `0`) whenever it does
  - `trigger_option`/`n_triggers`: `None` when the file omits them
  - `buffer_num`: defaults to `0` when the file omits it

See [Timing and Triggers](#timing-and-triggers) in Option 2 below for what `trigger_option` can actually
be set to (`'None'`, `'TriggerOnePulseTrain'`, `'TriggerWholeProtocol'`) and what `buffer_num` is
for; both mean the same thing whether they come from this YAML file or from Python directly.

Any optional field left out (or set to `null`) falls back to the same default the underlying Python code
would already use. Semantic mistakes (an unknown driving-system/transducer serial, an invalid
focus/power/trigger option, an out-of-range timing value) are not re-validated by the loader: they
surface via the package's own existing, clear error messages, which may reference a Python
function name (e.g. `add_slot()`). The loader does check the file's own structure: every required
key must be present, and an unrecognized/typo'd key (anywhere in the file) is rejected immediately.

When a file's `protocols` list has more than one entry (interleaving several protocols as one alternating group), every entry's `timing.pulse_ramp_shape`/`pulse_ramp_dur` must be identical; there is no way in YAML to share these values automatically between entries, so double-check they stay in sync if you ever change one. `trigger_option`/`n_triggers`, by contrast, are already whole-file (declared once, not per protocol entry), so there's nothing to keep in sync for those.

See [example_protocols/](../example_protocols) for a `protocol.yaml`/`standalone_yaml.py` pair in most scenario folders, alongside that scenario's `standalone_plain.py` (the full, manually-written Python equivalent).

### Protecting a Protocol File Against Accidental Edits

Once you're happy with a `protocol.yaml`, having a *fixed*, tamper-evident copy is often exactly
what you want for an experimental script, so its parameters can't silently drift mid-study. Run `python -m
fus_driving_systems.approve_protocol path/to/protocol.yaml` to write a sidecar
`path/to/protocol.yaml.sha256` file next to it, recording its current SHA-256 hash (the GUI's
Planning tab has the same "Approve protocol" button, so you don't need the command line either).
From then on,
`load_protocol()` will refuse to load that file (with a clear `sys.exit()`) if its content ever
changes without also re-running `approve_protocol` on it: catching an accidental edit before it
silently changes what gets sent to a driving system. This is opt-in by default: a protocol file
with no `.sha256` sidecar is loaded without any check at all, and `load_protocol()` itself never
creates or updates one; `approve_protocol()` is the only way to do that, so it always reflects a
deliberate decision that the current content is correct.

An existing sidecar's hash is always verified, regardless of `require_hash`; that parameter only
decides what happens when no sidecar exists at all. If you want a specific script to refuse to run
against an unapproved protocol in that case too (rather than silently loading it unchecked), pass
`require_hash=True` to `load_protocol()`. This is a Python-level parameter, set directly in your
own script.

```python
protocols, total_alternating_duration_ms, trigger_option, n_triggers, buffer_num = load_protocol(
    'protocol.yaml',
    require_hash=True,  # exits if protocol.yaml.sha256 is missing or doesn't match
)
```

## 🧱 Option 2: Define a Protocol in Python <a name="build-protocol"></a>

Open [standalone_plain.py](../example_protocols/single_transducer/igt/standalone_plain.py)
alongside this section: a real, working example you can follow along with, and start from for your
own protocol.

### Adding and Configuring Slots

```python
protocol = TUSProtocol('YOUR-SYSTEM-ID')
slot = protocol.add_slot('YOUR-TRANSDUCER-ID', 'Focus wrt exit plane [mm]', 40,
                          'Global power [W]', 2.5)

# Later, e.g. mid-experiment: adjust the same slot without rebuilding the protocol
slot.configure('Focus wrt exit plane [mm]', 45, 'Global power [W]', 3.0)

# Or swap to a different transducer entirely
slot.update_transducer('OTHER-TRANSDUCER-ID', 'Focus wrt exit plane [mm]', 40,
                        'Global power [W]', 2.5)
```

- `TUSProtocol(driving_sys_serial, engineering_mode=False)`: the driving system serial is required. Some options are gated behind `engineering_mode` as an institutional safety policy choice; see `engineering-only options` in [Configuration](configuration.md#safety-setting) for which ones and why. `protocol.get_power_options()`/`get_focus_options()` are available right away, before any slot exists.
- `protocol.add_slot(transducer_serial, focus_option, focus_value, power_option, power_value)`: adds one transducer slot; all five arguments are required, a slot is never half-configured (`oper_freq`/`dephasing_degree` can optionally be given too as keyword arguments). Returns the new slot, so scripts typically keep that reference (`slot = protocol.add_slot(...)`) instead of indexing back into `protocol.slots` later. For a driving system with `max. transducer slots > 1`, call it again for each additional transducer; each transducer's element count must fit within `available channels / max. transducer slots`, or you'll get a clear error.
- `slot.configure(focus_option, focus_value, power_option, power_value)`: changes an already-added slot's focus/power later (e.g. mid-experiment) without constructing a new `TUSProtocol`. Applies focus before power internally, regardless of argument order. `focus_wrt_exit_plane`/`focus_wrt_mid_bowl`/`global_power`/`press`/`volt`/`ampl` are read-only: this is the only way to set any of them.
- `slot.update_transducer(transducer_serial, focus_option, focus_value, power_option, power_value)`: swaps the slot's transducer for a different one; all five arguments are required again, the same as `add_slot()`. `oper_freq`/`dephasing_degree` are optional here too, but `dephasing_degree` always resets to `None` when not given, rather than carrying over from the old transducer.

There is no single-slot delegation on `TUSProtocol` itself (no `protocol.press`/`protocol.transducer`/etc.): every per-transducer attribute is always read via `protocol.slots[i].<attribute>`, whether there's one transducer or several. Reading is all you can do this way, though: `press`/`volt`/`ampl`/the focus attributes are read-only, as noted above; `configure()`/`update_transducer()` are the only way to set them. `IGT.send_protocol()`/`wait_for_trigger()`/`execute_protocol()` also accept a *list* of `TUSProtocol` objects to interleave them as one alternating group; each protocol then contributes exactly one pulse per round (`pulse_dur`/`pulse_rep_int` still apply per protocol, but `pulse_train_dur`/`pulse_train_rep_int`/`pulse_train_rep_dur` have no effect in that case).

### Timing and Triggers

```python
protocol.configure_timing(pulse_dur=10, pulse_rep_int=50, pulse_train_dur=1000)
ds.send_protocol(protocol)
ds.wait_for_trigger(protocol, trigger_option='TriggerOnePulseTrain', n_triggers=10)
```

- `protocol.configure_timing(pulse_dur, pulse_rep_int=None, pulse_train_dur=None, pulse_ramp_shape=None, pulse_ramp_dur=None, pulse_train_rep_int=None, pulse_train_rep_dur=None)`: the only way to set any timing parameter: you can read them individually afterward, but not set them one at a time, since they interact with and build on each other. `pulse_dur` is the only required argument: every level above it defaults to the level directly below it when not given, so a single pulse train, repeated once, is already complete. `pulse_ramp_shape`/`pulse_ramp_dur` do **not** inherit whatever was configured before: they reset to their own safe/off default ("no ramping"; `0`) every single call.
- `ds.send_protocol(protocols, total_alternating_duration_ms=None, buffer_num=0)`: uploads the protocol to the driving system's hardware, ready to run. Always call this first, before `execute_protocol()`/`wait_for_trigger()` below. `buffer_num` picks which hardware buffer to upload it to, defaulting to `0` (the only valid value for a driving system with no real multi-buffer concept). `total_alternating_duration_ms` is the total duration [ms] the whole interleaved group repeats for: required (and must be greater than `0`) whenever more than one protocol is interleaved, since there's no single protocol's own repetition count to fall back on; unused for a single protocol.
- `ds.execute_protocol(protocols, total_alternating_duration_ms=None, buffer_num=0)`/`ds.wait_for_trigger(protocols, trigger_option, n_triggers=None, total_alternating_duration_ms=None, buffer_num=0)`: run the already-sent protocol, either immediately (`execute_protocol()`) or only once an external trigger signal arrives (`wait_for_trigger()`). For the latter, `trigger_option` decides how triggering works:
  - `'None'`: no trigger at all; runs immediately, same as calling `execute_protocol()` instead
  - `'TriggerWholeProtocol'`: one trigger signal fires the entire, already-timed protocol
  - `'TriggerOnePulseTrain'`: a separate trigger signal is needed before every pulse train, so you must also say in advance, via `n_triggers`, how many to expect (`pulse_train_rep_int`/`pulse_train_rep_dur` don't apply in this case)

  Call `ds.get_trigger_options()` to check which of these your driving system actually supports.

`pulse_train_rep_int`/`pulse_train_rep_dur` are both optional, and control how the pulse train itself repeats: leave both out to repeat it exactly once; set only `pulse_train_rep_dur` to repeat back-to-back for that total duration; set only `pulse_train_rep_int` to space repetitions that far apart (repeated exactly once unless `pulse_train_rep_dur` is also given). See the worked example in [direct_execute.yaml](../example_protocols/single_transducer/igt/direct_execute.yaml) above.

## 🔗 Integrating into an Existing Experimental Script <a name="integrating"></a>

The example scripts are self-contained: their own logging setup, their own `try`/`finally` to
guarantee `disconnect()` still runs on an error or an abruptly stopped script. That scaffolding is
there so the example runs standalone, but it isn't something to copy into a script you already
have. Only the FDS-specific calls below (creating the driving system, loading the protocol,
`connect()`, `send_protocol()`, `execute_protocol()`, `disconnect()`) need to go into your own
existing structure:

```python
from fus_driving_systems.igt import igt_ds  # or fus_driving_systems.sonic_concepts.sonic_concepts_ds
from fus_driving_systems.protocol_loader import load_protocol

protocols, total_alternating_duration_ms, trigger_option, n_triggers, buffer_num = load_protocol(
    'direct_execute.yaml'
)

ds = igt_ds.IGT()
ds.connect(protocols[0].driving_sys.connect_info)  # once, at the start of your experiment

try:
    ds.send_protocol(protocols, total_alternating_duration_ms, buffer_num)  # once per protocol version
    ds.execute_protocol(protocols, total_alternating_duration_ms, buffer_num)  # again each trial
finally:
    ds.disconnect()  # always, so an abruptly stopped script doesn't leave it firing
```

`connect()` only needs to run once, when your experiment starts. `send_protocol()` only needs to
run again when the protocol itself has actually changed (e.g. you loaded a different
`protocol.yaml`, or called `slot.configure()`/`update_transducer()`); calling it again with an
unchanged protocol is harmless but unnecessary. `execute_protocol()`/`wait_for_trigger()` can then
be called as many times as you like, e.g. once per trial, as long as something was already sent.

If your own script already has its own logging set up, don't call `initialize_logger()` too (it
would reconfigure logging globally); call `sync_logger(your_own_logger)` instead, from
`fus_driving_systems.config.logging_config`, so FDS's own log messages go through your existing
logger rather than setting up a second, separate one:
```python
import logging
from fus_driving_systems.config.logging_config import sync_logger

your_own_logger = logging.getLogger('your_experiment')
sync_logger(your_own_logger)
```

Calling neither doesn't crash your script, but you'll get no log file at all, and almost nothing
will show up on the console either. If something goes wrong, you'll have no record to debug it
with or share when reporting an issue, so call one of the two above.

This minimal example only covers the simplest case: `execute_protocol()` directly, with no
external trigger and a single protocol. For other patterns, e.g. waiting for an external trigger
(`wait_for_trigger()`/`wait_for_trigger_result()`) or interleaving several protocols as one
alternating group, see the corresponding scenario folders under
[example_protocols/](../example_protocols) (e.g. `alternating_single_pulse_train`,
`switch_active_transducer`).

[← Back to README](../README.md)
