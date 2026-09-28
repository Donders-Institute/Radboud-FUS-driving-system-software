[← Back to README](../README.md)

## 📻 Adding Your Own Equipment <a name="add-equip"></a>

### Currently Supported Hardware

*Driving systems*
- Sonic Concepts 203-035
- Sonic Concepts 105-010
- IGT 128 channels
- IGT 32 channels

*Transducers*
- Sonic Concepts CTX-250-009
- Sonic Concepts CTX-250-014
- Sonic Concepts CTX-500-006
- Sonic Concepts CTX-250-001
- Sonic Concepts CTX-250-026
- Sonic Concepts CTX-500-024
- Sonic Concepts CTX-500-026
- Sonic Concepts DPX-500-022
- Imasonic PCD15287_01001
- Imasonic PCD15287_01002
- Imasonic PCD15473_01001
- Imasonic PCD15473_01002

You can extend the software to support new hardware by following these steps:

### Step 1: Create a New Manufacturer Module
1. Create a new folder within [fus_ds_package/fus_driving_systems/](../fus_ds_package/fus_driving_systems) (e.g., `your_manufacturer_name/`)
2. Add an empty `__init__.py` file to that folder
3. Create a new Python class that inherits from the abstract `ControlDrivingSystem` class

For example:

```python
from fus_driving_systems import control_driving_system as ds

class YourManufacturer(ds.ControlDrivingSystem):
    # Implement required methods here
```

### Step 2: Implement Required Methods

Your class must implement these abstract methods:

```python
def connect(self, connect_info):
    """
    Establish connection with the ultrasound driving system
    Args:
        connect_info: Connection details (COM port, IP address, etc.)
    """
    pass

def send_protocol(self, protocol):
    """
    Translate and send ultrasound protocol to the driving system
    Args:
        protocol: A TUSProtocol instance containing, amongst other things, of:
				the timing/power/focus parameters (focus, pulse duration, pulse rep. interval
				and etcetera) and the equipment used (driving system and transducer)
    """
    pass

def execute_protocol(self):
    """
    Execute the previously sent protocol
    """
    pass

def disconnect(self):
    """
    Disconnect from the ultrasound driving system
    """
    pass
```

You can add additional helper methods as needed to support your implementation.

#### Error Handling

This package signals failures by raising exceptions from `fus_driving_systems.exceptions`, not by exiting the process: `FDSValidationError` (invalid caller input), `FDSSafetyError` (a value that would be unsafe to actually send to hardware), `FDSHardwareError` (an SDK/hardware/OS failure), `FDSConfigError` (broken or missing static configuration), and `FDSInternalError` (a should-never-happen internal bug) -- all inherit from a common `FDSError`. When implementing a new manufacturer module, log via `get_logger().critical(...)` and raise whichever of these matches the failure, rather than calling `sys.exit()` or raising a bare/builtin exception.

Every standalone example script wraps its own body in `except FDSError as e: sys.exit(str(e))`, so any of these still produce today's clean, single-line command-line output when run directly.

### Step 3: Create a Standalone Script

1. Create a new scenario folder under [example_protocols/](../example_protocols) (e.g., `example_protocols/your_manufacturer/`), or add a manufacturer subfolder to an existing scenario if it fits one already.
2. Use existing scripts (like [standalone_plain.py](../example_protocols/single_transducer/sonic_concepts/standalone_plain.py)) as templates.
3. In the first section: Define user input by setting appropriate TUSProtocol parameters. Configure the code according to your specific equipment by adjusting timing parameters, power input levels, and other relevant settings.
4. In the second section: Import your new driving system script and initialize an instance of the class. The invocation of the implemented abstract functions (connect, send_protocol, execute_protocol, disconnect) can remain the same.

A `TUSProtocol` is created with its driving system serial as a required argument (e.g. `TUSProtocol('YOUR-SYSTEM-ID')`). `protocol.get_power_options()`/`get_focus_options()` are available right away, before any slot has been added, since `add_slot()` itself needs a valid option string to call. It starts with zero transducer slots; call `add_slot(transducer_serial, focus_option, focus_value, power_option, power_value)` once per transducer before using the protocol (all five arguments are required -- a slot is never half-configured; `oper_freq`/`dephasing_degree` can optionally be given too, as keyword arguments, though neither has the same ordering hazard so setting them on the returned slot afterward works just as well). There is no single-slot delegation on `TUSProtocol` itself (no `protocol.press`/`protocol.transducer`/etc.) -- every per-transducer attribute is always addressed via `protocol.slots[i].<attribute>`, whether there's one transducer or several, so a script is never in doubt about which access style applies. `add_slot()` returns the newly added slot, so scripts typically just keep that reference (`slot = protocol.add_slot(...)`) rather than indexing back into `protocol.slots` afterward. For a driving system with `max. transducer slots > 1`, call `add_slot()` again for each additional transducer (each transducer's element count must fit within `available channels / max. transducer slots`); `IGT.send_protocol()`/`wait_for_trigger()`/`execute_protocol()` also accept a *list* of `TUSProtocol` objects to interleave them as one alternating group. When interleaving, each protocol contributes exactly one pulse per round of the alternating group, not a repeated pulse train of its own -- `pulse_dur`/`pulse_rep_int` still apply per protocol (`pulse_rep_int` decides how much of the shared round this protocol's own pulse occupies), but `pulse_train_dur`/`pulse_train_rep_int`/`pulse_train_rep_dur` currently have no effect in that case.

To change an already-added slot's focus/power later (e.g. mid-experiment, then re-send the same protocol) without constructing an entirely new `TUSProtocol`, call `protocol.slots[i].configure(focus_option, focus_value, power_option, power_value)` -- it applies focus before power internally, same as `add_slot()`, regardless of the order the arguments are given in. `focus_wrt_exit_plane`/`focus_wrt_mid_bowl`/`global_power`/`press`/`volt`/`ampl` are read-only -- `configure()` is the only way to set any of them, since setting one directly, without an already-correct focus, can silently compute a wrong value on driving systems that need a calibration curve to convert between them.

To swap an already-added slot's transducer for a different one, call `protocol.slots[i].update_transducer(transducer_serial, focus_option, focus_value, power_option, power_value)` directly on that slot -- like `add_slot()`, all five of these are required (the new transducer's calibration curve/geometric range differ from the old one's, so old focus/power numbers can't just be assumed to still be correct). `oper_freq`/`dephasing_degree` are optional here too, but `dephasing_degree` always resets to `None` (no dephasing) when not given, rather than carrying over from the old transducer -- a dephasing list is sized to a specific transducer's element count, so one built for the old transducer isn't safe to assume for the new one. `add_slot()` itself is a thin wrapper around this same method (it constructs a bare slot, then calls `update_transducer()` on it) -- so this per-slot element-count check always runs, whether a slot is being configured for the first time or swapped later; `TUSProtocol`'s own aggregate channel-count check only runs from `add_slot()`, since (per the per-slot ceiling `available channels / max. transducer slots`) a swap that keeps every slot within its own ceiling can never push the total over `available channels` either.

`TUSProtocol.configure_timing(pulse_dur, pulse_rep_int=None, pulse_train_dur=None, pulse_ramp_shape=None, pulse_ramp_dur=None, pulse_train_rep_int=None, pulse_train_rep_dur=None)` is the only way to set any timing parameter -- `pulse_dur`, `pulse_rep_int`, `pulse_train_dur`, `pulse_train_rep_int`, `pulse_train_rep_dur`, `pulse_ramp_shape` and `pulse_ramp_dur` all have getters only, precisely because they cascade/interact with each other and are prone to ordering hazards if set individually and out of order (e.g. `pulse_train_dur` before `pulse_dur`). `pulse_dur` is the only required argument -- every level above it defaults to the level directly below it when not given, so a single pulse train, repeated once, is already a complete, self-consistent result. `pulse_ramp_shape`/`pulse_ramp_dur` left as `None` do **not** inherit whatever was configured before -- they reset to their own safe/off default every single call ("no ramping"; `0`), the same way `pulse_dur`'s own family resets to "repeat once" rather than reusing a stale value.

Trigger configuration (`trigger_option`/`n_triggers`) is **not** part of `configure_timing()`, and `TUSProtocol` has no trigger-related attribute or method at all (no `wait_for_trigger`, `trigger_option`, `n_triggers`, `buffer_num` or `get_trigger_options()`) -- these are call-level parameters of `IGT.send_protocol()`/`wait_for_trigger()`/`execute_protocol()` instead (see below): there is exactly one hardware buffer and one trigger event per execute-call, regardless of how many `TUSProtocol` objects are interleaved into it.

`'TriggerOnePulseTrain'` fires exactly one pulse train per external trigger received, so the driving system needs to know in advance how many to expect: `n_triggers` is *required* (not optional) specifically for this `trigger_option`, and `pulse_train_rep_int`/`pulse_train_rep_dur` don't apply at all. Every other `trigger_option` -- `'None'` (no trigger, use `execute_protocol()` directly) or `'TriggerWholeProtocol'` (one trigger fires the entire, already fully-timed protocol at once, equivalent to executing it directly but gated behind a single external trigger) alike -- uses `pulse_train_rep_int`/`pulse_train_rep_dur` instead, and `n_triggers` isn't valid there. `pulse_train_rep_int`/`pulse_train_rep_dur` may be given together, or just one of the two, or neither: `pulse_train_rep_int` defaults to `pulse_train_dur` (back-to-back repetition) when not given; only *then* does `pulse_train_rep_dur` default to that interval (i.e. "repeat exactly once") when not given -- so giving only `pulse_train_rep_dur` (a total span) fills it back-to-back, while giving only `pulse_train_rep_int` (or neither) collapses to a single repetition.

`IGT.wait_for_trigger(protocols, trigger_option, n_triggers=None, total_alternating_duration_ms=None, buffer_num=0)` is where `trigger_option`/`n_triggers` are actually given -- `trigger_option` has no default (calling `wait_for_trigger()` at all already means a trigger is wanted); use `execute_protocol()` directly instead when it isn't. `IGT.send_protocol(protocols, total_alternating_duration_ms=None, buffer_num=0)`/`execute_protocol(protocols, total_alternating_duration_ms=None, buffer_num=0)` share the same `buffer_num` parameter: a group of one or several interleaved protocols is always sent to exactly one hardware buffer; it defaults to `0`, the only valid value for a driving system with no real multi-buffer concept. To check available trigger options, call `IGT.get_trigger_options()` on the driving-system instance.

#### Load a protocol from a YAML file

Instead of building a `TUSProtocol` directly in Python, `fus_driving_systems.protocol_loader.load_protocol(yaml_path, engineering_mode=False, require_hash=False)` parses a YAML file into ready-to-use `TUSProtocol` object(s) -- a simpler alternative aimed specifically at researchers who need to adjust a protocol's parameters without writing or editing Python. It returns a 5-tuple `(protocols, total_alternating_duration_ms, trigger_option, n_triggers, buffer_num)`: `protocols` is always a list (even for a single protocol); `total_alternating_duration_ms` is `None` unless the file describes more than one protocol to interleave; `trigger_option`/`n_triggers` are `None` when the file omits them; `buffer_num` defaults to `0` when the file omits it. All five are meant to be forwarded straight into `send_protocol()`/`wait_for_trigger()`/`execute_protocol()`.

```yaml
driving_sys_serial: IGT-32-ch_comb_2x10-ch

# trigger_option/n_triggers/buffer_num are whole-file, top-level keys -- siblings of
# driving_sys_serial/protocols/total_alternating_duration_ms, not nested under any protocol's
# own timing: block -- since they're parameters of send_protocol()/wait_for_trigger()/
# execute_protocol() themselves, not of any one TUSProtocol.
trigger_option: TriggerWholeProtocol  # optional
# n_triggers: 4                       # optional -- only valid when trigger_option: TriggerOnePulseTrain
# buffer_num: 0                       # optional -- defaults to 0

protocols:
  - slots:
      - transducer_serial: IS_PCD15287_01001
        focus_option: Focus wrt exit plane [mm]
        focus_value: 40
        power_option: Max. pressure in free water [MPa]
        power_value: 0.5
        oper_freq: 300          # optional
        dephasing_degree: null  # optional
    timing:
      pulse_dur: 45             # the only required timing field
      pulse_rep_int: 100        # optional

total_alternating_duration_ms: null  # only needed when protocols above has more than one entry
```

Every field mirrors a Python parameter name 1:1 (`slots[i]` -> `add_slot()`'s arguments, `timing` -> `configure_timing()`'s keyword arguments, top-level `trigger_option`/`n_triggers`/`buffer_num` -> the same-named parameters of `send_protocol()`/`wait_for_trigger()`/`execute_protocol()`) -- an omitted or `null` optional field falls back to exactly the same default the matching Python call would already use. Semantic mistakes (an unknown driving-system/transducer serial, an invalid focus/power/trigger option, an out-of-range timing value) are not re-validated by the loader -- they surface via `TUSProtocol`/`add_slot()`/`configure_timing()`/`IGT.wait_for_trigger()`'s own existing, clear error messages, exactly as if you'd written the equivalent Python yourself. The loader does check the file's own structure: every required key must be present, and an unrecognized/typo'd key (anywhere in the file) is rejected immediately rather than silently doing nothing.

When a file's `protocols` list has more than one entry (interleaving several protocols as one alternating group), every entry's `timing.pulse_ramp_shape`/`pulse_ramp_dur` must be identical (the same requirement `send_protocol()` already enforces for Python-built protocols) -- there is no way in YAML to share these values automatically between entries, so double-check they stay in sync if you ever change one. `trigger_option`/`n_triggers`, by contrast, are already whole-file (declared once, not per protocol entry), so there's nothing to keep in sync for those.

See [example_protocols/](../example_protocols) for a `protocol.yaml`/`standalone_yaml.py` pair in most scenario folders, alongside that scenario's `standalone_plain.py` (the full, manually-written Python equivalent).

**Optional: protect a protocol file against accidental edits.** Once you're happy with a `protocol.yaml`, you can run `python -m fus_driving_systems.approve_protocol path/to/protocol.yaml` to write a sidecar `path/to/protocol.yaml.sha256` file next to it, recording its current SHA-256 hash. From then on, `load_protocol()` will refuse to load that file (with a clear `sys.exit()`) if its content ever changes without also re-running `approve_protocol` on it -- catching an accidental edit before it silently changes what gets sent to a driving system. This is opt-in by default: a protocol file with no `.sha256` sidecar is loaded without any check at all, and `load_protocol()` itself never creates or updates one -- `approve_protocol()` is the only way to do that, so it always reflects a deliberate decision that the current content is correct.

If you want a specific script to refuse to run against an unapproved protocol at all (rather than silently loading it unchecked whenever no sidecar happens to exist), pass `require_hash=True` to `load_protocol()`. This is a Python-level parameter, set directly in your own script, next to `engineering_mode`.

```python
protocols, total_alternating_duration_ms, trigger_option, n_triggers, buffer_num = load_protocol(
    'protocol.yaml',
    require_hash=True,  # exits if protocol.yaml.sha256 is missing or doesn't match
)
```

To use your new equipment with custom serial numbers for driving systems and transducers, you'll need to update the configuration file. You can either modify the [ds_config.ini](../fus_ds_package/fus_driving_systems/config/ds_config.ini) file directly or modify and regenerate it using the provided [create_config.py](../fus_ds_package/fus_driving_systems/config/create_config.py) script. How and what to modify is explained in the next step.

### Step 4: Update the Configuration File

`ds_config.ini` is a **generated file** -- never add your equipment there directly, since any hand-edit is silently lost the next time [create_config.py](../fus_ds_package/fus_driving_systems/config/create_config.py) runs, or the moment a new package release is installed. Add your equipment to `create_config.py` instead, then regenerate `ds_config.ini` from it (Step 5 below).

`create_config.py` provides `_add_driving_system(...)`/`_add_transducer(...)`/`_add_combination(...)` helper functions specifically so adding equipment is one function call with keyword arguments, not a hand-copied block of individual `config[section][key] = value` lines. Each of the four subsections below shows what the resulting `ds_config.ini` entry looks like -- that's what the matching helper call produces, not something you type into `ds_config.ini` yourself. The Equipment section is extensive and includes settings for:

1. Available driving systems and transducers
2. Manufacturer-specific configurations
3. Specific hardware parameters for each device
4. Compatible combinations of equipment

#### 1. Add to Equipment Section
Add your system/transducer identifier to the relevant list near the top of `create_config.py` (e.g. `IGT_DS`/`SC_DS`/`CITRUS_DS` for driving systems, `IS_TRANS`/`SC_TRAN_2CH`/etc. for transducers), which ends up in the generated `ds_config.ini` as:
```ini
[Equipment]
driving systems = 203-035
    105-010
    YOUR-SYSTEM-ID  # Add your system here
# ...
transducers = CTX-250-009
    CTX-250-014
    YOUR-TRANSDUCER-ID  # Add your transducer here
# ...
combination sign = ~
```

- **driving systems**: List of available driving system identifiers
- **transducers**: List of available transducer identifiers
- **combination sign**: Symbol used to denote system-transducer combinations

#### 2. Add Manufacturer Settings
If your manufacturer isn't one of the existing ones in `create_config.py` yet, add a new block of `config['Equipment.Manufacturer.YM'][...] = ...` assignments (copy an existing manufacturer's block as a starting point), which ends up in the generated `ds_config.ini` as:
```ini
[Equipment.Manufacturer.YM]  # Use your manufacturer's abbreviation
name = Your Manufacturer Name
config. file folder transducers = path\to\config\folder
power options = Global power [mW]  # Choose appropriate options
# Add manufacturer-specific settings
equipment - driving systems = YOUR-SYSTEM-ID
# and/or
equipment - transducers = YOUR-TRANSDUCER-ID
```

Default settings per manufacturer are:
- **name**: The manufacturer's full name
- **config. file folder transducers**: Location of additional config files if required
- **power options**: (For driving systems) Compatible power options which must be chosen from the Power section of the config
- **equipment - driving systems**: Available driving systems of this manufacturer, must be listed in the main Equipment section \
and/or
- **equipment - transducers**: Available transducers of this manufacturer, must be listed in the main Equipment section

Additional manufacturer-specific settings can be added as needed. For example, the IGT configuration contains more settings related to hardware limits.


#### 3. Add Specific Equipment Settings
In `create_config.py`, call:
```python
_add_driving_system(
    'YOUR-SYSTEM-ID',
    name='Your System Name',
    manufacturer='Your Manufacturer Name',
    available_channels=4,
    connection_info='COM7',  # or other connection info
    transducer_compatibility=['YOUR-TRANSDUCER-ID'],
    power_options=[POW_GP],
    native_power_parameters=POW_GP,
    focus_options=[FOC_WRT_EXIT],
    native_focus_parameters=FOC_WRT_EXIT,
    max_transducer_slots=1,
    max_buffers=1,
    active=True,
)
```
which ends up in the generated `ds_config.ini` as:
```ini
[Equipment.Driving system.YOUR-SYSTEM-ID]
name = Your System Name
manufacturer = Your Manufacturer Name
available channels = 4  # Number of channels
connection info = COM7  # Or other connection info
power options = Global power [mW]
focus options = Focus wrt exit plane [mm]
native power parameters = Global power [mW]
native focus parameters = Focus wrt exit plane [mm]
transducer compatibility = YOUR-TRANSDUCER-ID
max. transducer slots = 1
max. buffers = 1
active? = True
```

The driving system identifier must match one of the identifiers defined in the '[Equipment]' section under *driving systems*. Default settings for driving systems are:
- **name**: Descriptive name of the system
- **manufacturer**: Must match one of your defined manufacturers
- **available channels**: Number of channels the system provides
- **connection info**: COM port, IP address, or path to configuration file
- **power options**: Power options supported by this system at all, which must be chosen from the Power section of the config. Setting a power option this system doesn't list here exits with a clear "not available" error.
- **focus options**: Same idea, for focus, one or more of `Focus wrt exit plane [mm]`/`Focus wrt mid bowl [mm]` and their 3D (x/y/z) variants `Focus xyz wrt exit plane [mm]`/`Focus xyz wrt mid bowl [mm]` (see "3D (lateral) steering" below), whichever this system supports at all (e.g. a system that never has a focus-conversion calibration should only list its native option here).
- **native power parameters**: Which of *power options* this system's hardware accepts directly, without needing a calibration curve to convert it (e.g. amplitude for IGT, global power for Sonic Concepts, voltage for CITRUS). A native parameter never needs an active calibration to be set (subject to the separate `engineering-only options` check below, if applicable); setting any other power option (that's still listed in *power options*) always requires an active `Equipment.Combination.*` entry (see step 4) to convert it, regardless of `engineering-only options`. Usually a single value, but if your system's hardware genuinely accepts more than one power representation directly, list them all, one per line (like *power options* above).
- **native focus parameters**: Same idea, for focus, one or more of `Focus wrt exit plane [mm]`/`Focus wrt mid bowl [mm]`/their xyz variants, whichever this system's hardware accepts directly. For IGT this lists both `Focus wrt mid bowl [mm]` and `Focus xyz wrt mid bowl [mm]`, the xyz variant is native exactly when its scalar counterpart is, since it's the same reference frame with x/y added.
- **transducer compatibility**: List of compatible transducer IDs. `TUSProtocol.add_slot()`/`protocol.slots[i].update_transducer()` exit with a clear error if you try to assign a transducer that isn't listed here for this driving system.
- **max. transducer slots**: How many transducers this driving system can drive simultaneously. Defaults to `1` (single-transducer-only) when omitted -- only set this above `1` for a driving system that genuinely supports it (e.g. IGT's `_comb_2x10-ch`-style configs).
- **max. buffers**: How many hardware buffers this driving system can hold a protocol in at once -- each buffer can be pre-loaded with its own protocol ahead of time and triggered/executed independently (see the `buffer_num` parameter of `IGT.send_protocol()`/`wait_for_trigger()`/`execute_protocol()`). Defaults to `1` (no real buffer concept, `buffer_num` is then only ever `0`) when omitted -- all current IGT systems declare `2` here.
- **active?**: Whether this system is active and available for use

Similarly, call `_add_transducer(...)` for your transducer:
```python
_add_transducer(
    'YOUR-TRANSDUCER-ID',
    name='Your Transducer Name',
    manufacturer='Your Manufacturer Name',
    elements=2,
    fund_freq=250,
    min_focus=0,
    max_focus=100,
    # exit_plane_dist is the geometric fallback used to convert between exit-plane and
    # mid-bowl focus when no active calibration exists -- native-ness checks ensure it's
    # only ever used for the informational side, never the value actually sent to
    # hardware.
    steer_information='path\\to\\steer\\info',  # only if applicable
    can_3d_steer=False,  # see "3D (lateral) steering" below
    # Only meaningful when can_3d_steer=True; see "3D (lateral) steering" below.
    min_focus_x=0, max_focus_x=0, min_focus_y=0, max_focus_y=0,
    active=True,
)
```
which ends up as:
```ini
[Equipment.Transducer.YOUR-TRANSDUCER-ID]
name = Your Transducer Name
manufacturer = Your Manufacturer Name
elements = 2
fund. freq. = 250
exit plane - first element dist. = 0
min. focus = 0
max. focus = 100
steer information = path\to\steer\info
can 3d steer? = False
min. focus x = 0
max. focus x = 0
min. focus y = 0
max. focus y = 0
active? = True
```

The transducer identifier must match one of the identifiers defined in the '[Equipment]' section under *transducers*. Default settings for transducers are:
- **name**: Descriptive name of the transducer
- **manufacturer**: Must match one of your defined manufacturers
- **elements**: Number of elements in the transducer
- **fund. freq.**: Fundamental frequency in kHz
- **exit plane - first element dist.**: Distance between radiating surface and exit plane in millimeters. Used as a geometric fallback when converting between exit-plane and mid-bowl focus without an active calibration -- native-ness checks ensure it's only ever used informationally, never for the value actually sent to hardware.
- **min. focus**: Minimum allowed focus with respect to exit plane in millimeters. Only used as-is when there's no active `Equipment.Combination.*` calibration for this transducer/driving-system pair -- once one is active, this value is overwritten (not merely defaulted) with the equalization curve's own minimum break, so the configured value becomes irrelevant.
- **max. focus**: Maximum allowed focus with respect to exit plane in millimeters. Same overwrite behavior as *min. focus* above, once a calibration is active.
- **steer information**: Path to steering information file if applicable. Get this from IGT for your own transducer; reusing ours is only valid if it's the exact same transducer serial number (the file only describes physical element geometry, which doesn't change), never for a "similar" or "compatible" one.
- **can 3d steer?**: Whether this transducer's own element geometry supports lateral (x/y) steering, not just depth, see "3D (lateral) steering" below. Only valid for a `.ini`-based *steer information* (a `.xlsx` lookup table has no x/y concept). Defaults to `False`.
- **min./max. focus x**, **min./max. focus y**: Minimum/maximum allowed lateral offset in millimeters, only meaningful (and only ever enforced) for a `can_3d_steer=True` transducer, see "3D (lateral) steering" below. Unlike *min./max. focus*, these default to `0` (no lateral offset at all) when omitted, not a generous range: a transducer's real 3D steering geometry not yet being configured should fail closed, not silently allow an unvalidated offset.
- **active?**: Whether this transducer is active and available for use

#### 4. Add Equipment Combinations (advanced feature, if needed)

**⚠️ Never reuse someone else's calibration JSON files for your own equipment**, even a
driving system that looks identical to ours on paper. These curves convert a user-facing value
(e.g. "1 MPa pressure in free water") into what the hardware actually receives (e.g. amplitude):
if your unit happens to output more power than ours at the same amplitude, reusing our curve
means every protocol silently runs at a higher pressure than the value you entered, with no
warning at all. Get your own calibration data from IGT, generated for your own driving
system/transducer pair; if you believe your setup is identical to an existing one, confirm that
with IGT first, don't assume it from matching model numbers alone.

If your system's *native power parameters* and/or *native focus parameters* isn't the only power/focus option you want to offer, add a combination entry per driving-system/transducer pair to make the other options settable too. In `create_config.py`, call:
```python
_add_combination(
    'YOUR-SYSTEM-ID', 'YOUR-TRANSDUCER-ID',
    'your_equalization_curve_fit.json',
    'your_focus_curve_fit.json',
    'your_power_curve_fit.json',
    'your_voltage_curve_fit.json',
)
```
pointing at your own calibration JSON files (bare filenames -- resolved automatically relative to `CONFIG_FILE_FOLDER_CONVERSION_DATA`), which ends up as:

```ini
[Equipment.Combination.YOUR-SYSTEM-ID~YOUR-TRANSDUCER-ID]
driving system serial = YOUR-SYSTEM-ID
transducer serial = YOUR-TRANSDUCER-ID
active? = True
... conversion equations
```

- **active?**: Whether a calibration actually exists for this specific driving-system/transducer pair. `create_config.py` derives this automatically from whether the referenced calibration JSON files exist on disk. Setting a non-native power/focus parameter without an active combination for the current pair exits with a clear error, since there is no way to produce a value the hardware can actually accept.

These combinations are only required if additional equations are needed to convert user input (e.g., pressure in free water and focus with respect to exit plane) to input the driving system understands (e.g., amplitude and focus with respect to mid bowl). This is required for combinations like IGT-Imasonic.

For a `can_3d_steer=True` transducer, the same four `_add_combination(...)` filenames point at 3D calibration data instead of 1D, there's no separate set of keys for it, since the transducer's own `can_3d_steer` already determines how they're interpreted. See "3D (lateral) steering" below.

#### 3D (lateral) steering

IGT transducers with a `.ini`-based *steer information* can, in principle, be steered laterally (x/y) as well as in depth (z). `TUSProtocol.add_slot()`/`protocol.slots[i].configure()`/`update_transducer()` accept `Focus xyz wrt exit plane [mm]`/`Focus xyz wrt mid bowl [mm]` as a `focus_option`, taking an `(x, y, z)` tuple in millimeters as `focus_value` instead of a bare float. `x`/`y` are lateral offsets in the transducer's own coordinate space (the same frame `transducer_xyz.Transducer.compute_phases()`'s `point_mm` already uses); `z` is the focal depth in whichever reference frame (exit plane or mid bowl) you chose.

This only works for a transducer with `can_3d_steer=True` (see step 3). Setting an xyz option on a transducer without `can_3d_steer=True` exits with a clear error.

`x`/`y` are checked against that transducer's own *min./max. focus x*/*min./max. focus y* (see step 3), the lateral equivalent of *min./max. focus* for `z`. Unlike `z`, this check needs no exit-plane/mid-bowl conversion at all: a lateral offset is identical regardless of which depth reference frame is chosen. These default to `0` (no lateral offset allowed) when a transducer doesn't configure its own, so a `can_3d_steer=True` transducer without real steering-range data yet (e.g. one still using placeholder geometry) fails closed on any actual offset instead of silently allowing an unvalidated one.

`Focus xyz wrt mid bowl [mm]` is native for IGT (no calibration needed at all, the same reason scalar mid bowl needs none), so it works for a `can_3d_steer=True` transducer even without any 3D calibration data. `Focus xyz wrt exit plane [mm]` is not native, and converting it requires 3D calibration data: setting it without an active one exits with a clear "requires 3D calibration data" error, the same way any other non-native parameter without an active calibration does.

Of the four calibration curves (see step 4), only the equalization curve and the focus curve depend on where the target actually is: an off-axis (x/y) target changes both the achievable pressure (equalization) and the exit-plane/mid-bowl relationship (focus), so a 3D-capable transducer's combination needs 3D versions of those two. The power curve (amplitude vs. pressure) and voltage curve (amplitude vs. voltage) are purely electrical/hardware relationships that don't depend on the target's position, so they stay the same regardless of `can_3d_steer`.

The four typical conversion equations are:
- **equalization factor vs focus wrt exit plane**: Adjusts for the decreasing maximum pressure in free water that occurs with increasing focus distance. This compensates for beam attenuation at greater distances.
- **focus wrt mid bowl vs focus wrt exit plane**: Converts between different focus reference points
- **amplitude vs pressure in free water**: Maps desired pressure to system amplitude settings
- **amplitude vs voltage**: Relates amplitude settings to actual voltage levels

**Current limitation**: these conversions always target amplitude (for power) and focus wrt mid bowl (for focus) specifically -- they don't yet convert toward an arbitrary native parameter. This is correct for every driving system this package currently ships (IGT's native power/focus parameters are amplitude/mid-bowl, which is why this is the only manufacturer with real combinations today), but a future driving system whose native power parameter is something *other* than amplitude (e.g. global power) would need this generalized first -- not yet implemented.

These conversion equations allow users to specify parameters in intuitive units (like pressure) while the system handles the conversion to hardware-specific inputs.

### Step 5: Regenerate the Configuration File and Reinstall the Package

1. Run `create_config.py` from inside `fus_ds_package/fus_driving_systems/config/` (e.g. `python create_config.py`) to regenerate `ds_config.ini` from your changes.
2. Reinstall the FUS driving system package to apply your updates.

Now you are ready to use your new standalone script to drive the new equipment.

[← Back to README](../README.md)
