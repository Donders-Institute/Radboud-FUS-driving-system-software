[← Back to README](../README.md)

# 🧰 Configuration <a name="config"></a>

The Radboud FUS Driving System Software can be customized through its configuration file to match your specific requirements. This section explains what can be configured and how to properly modify settings.

## Common Configuration Tasks

Here are some frequently adjusted settings:

- **Change equipment**: Add/edit entries in [create_config.py](../fus_ds_package/fus_driving_systems/config/create_config.py)'s `[Equipment]`-related sections, then regenerate `ds_config.ini` from it: see [Adding Your Own Equipment](adding-equipment.md#add-equip)
- **Adjust safety limits**: Update `maximum pressure allowed in free water` directly in the generated `ds_config.ini`'s `[Power]` section, a deliberate exception to the "don't hand-edit" rule below (see [Safety Setting](#safety-setting))
- **Modify logging behavior**: Change log levels and paths in the `[Logging]` section

## Important Notes

- Some settings are interdependent: for example, changing power options may require corresponding adjustments to equipment configurations or even code modifications
- Many of the default values in the configuration file are also used by the GUI of the Radboud-FUS-measurement-kit (SonoRover). This package's own dedicated GUI ([Download the GUI](../README.md#gui)) uses these same configuration parameters directly.
- Always verify system behavior after making configuration changes
- The maximum values for many parameters are hardware-dependent

If you encounter issues after modifying the configuration:
1. Verify syntax and formatting in the configuration file
2. Check hardware connections and compatibility
3. Review logs for specific error messages
4. Revert to a known working configuration if needed

## ⚙️ Configuring System Parameters <a name="other-config"></a>

The package includes a comprehensive configuration file [ds_config.ini](../fus_ds_package/fus_driving_systems/config/ds_config.ini) that controls various aspects of the system, but it is a **generated file**, produced by running [create_config.py](../fus_ds_package/fus_driving_systems/config/create_config.py), and should not be hand-edited directly (one narrow exception: see [Safety Setting](#safety-setting) below): any direct edit is silently lost the next time `create_config.py` runs, or the moment a new package release is installed (which ships its own freshly generated copy). To change something, edit `create_config.py` instead:

1. Open [create_config.py](../fus_ds_package/fus_driving_systems/config/create_config.py) and make your changes there (see [Adding Your Own Equipment](adding-equipment.md#add-equip) for the equipment-specific case)
2. Run it from inside `fus_ds_package/fus_driving_systems/config/` (e.g. `python create_config.py`) to regenerate `ds_config.ini`
3. Reinstall and restart the application for changes to take effect

The configuration file is organized into these main sections:

- **General Settings**: Basic system parameters
- **Logging**: System event recording options
- **Trigger**: Ultrasound pulse triggering configuration
- **Power**: Output power control settings
- **Focus**: Beam focusing parameters
- **Ramp**: Pulse ramping options
- **Timing**: Default timing parameters
- **Equipment**: Hardware component and compatibility settings

### General Settings

```ini
[General]
configuration file folder = config
maximum reconnection attempts = 5
package name = fus_driving_systems
speed of sound water [m/s] = 1500
```

These parameters control basic system behavior. 
- **configuration file folder**: Location of additional configuration files
- **maximum reconnection attempts**: Number of times the system tries to reconnect to hardware
- **package name**: The software package identifier
- **speed of sound water**: The speed of sound value (1500 m/s by default) is particularly important for phase calculations in certain systems like IGT-Imasonic combinations.

### Logging Configuration

```ini
[Logging]
logger name = driving_system
temporary logging path = C:\Temp
filename faulthandler = faulthandler_output.log
timestamp format = %Y-%m-%d_%H-%M-%S
log level console = WARNING
log level file = INFO
initial part of log filename = log_
```

Adjust these settings to control what information is recorded and where. Increasing log levels (DEBUG, INFO, WARNING, ERROR, CRITICAL) provides more detailed information for troubleshooting.
- **logger name**: Identifier of logger
- **temporary logging path**: Directory where logs are stored
- **filename faulthandler**: Name of the file for recording critical errors
- **timestamp format**: How dates/times appear in logs (Year-Month-Day_Hour-Minute-Second)
- **log level console**: Minimum severity level shown on screen (WARNING shows warnings and errors)
- **log level file**: Minimum severity level saved to the `debug`/`measurements` files (see below)
- **initial part of log filename**: Shared prefix for all log files

Each session writes its FDS log files into its own timestamped session folder, alongside the faulthandler log and, for an IGT driving system specifically, its own native (non-FDS) log too: everything from one session ends up together, so when reporting a problem, share the whole session folder. The FDS log files themselves are `info` (mirrors `log level console`'s severity: the clean, researcher-facing record of what ran) and `debug` (mirrors `log level file`: everything, including validation/curve/setter detail). A third, separate `measurements` file (also at `log level file`'s severity) exists too, so a single protocol with many repetitions doesn't fill `debug` with thousands of measurement lines, but it's only created if something is actually logged to it, which today only IGT's per-pulse/per-channel hardware measurements do; other driving systems' sessions never get this file at all.

### Safety Setting

```ini
[Power]
# ...options...
maximum pressure allowed in free water [mpa] = 1.4
```

The maximum pressure setting (1.4 MPa by default) serves as a safety limit. Adjust this based on your specific requirements, but exercise caution to maintain safety. Note that this is a hand-edit to a generated file: it will be silently overwritten if `ds_config.ini` is ever regenerated via `create_config.py`, or replaced by installing a new package release. Keep a copy of your override if you rely on it long-term.

Both `[Power]` and `[Focus]` also have an `engineering-only options` key (by default `Amplitude [%]` and `Voltage [V]` for `[Power]`, and none for `[Focus]`) listing which options require `TUSProtocol(driving_sys_serial, engineering_mode=True)` to set directly. Any of six power/focus options can be listed there: `global power`, `max. pressure in free water`, `amplitude`, `voltage`, `focus wrt exit plane`, `focus wrt mid bowl`. This is purely an institutional safety-policy choice, not a hardware requirement, so none of the six is a special case exempt from it.

By default, only `amplitude` and `voltage` are gated. To change that, edit the list itself, no code changes needed: remove one of these two if your institution doesn't need it gated, or add one of the other options (or clear the list entirely) to gate fewer or more. Since `ds_config.ini` is a generated file, make that edit in `create_config.py` (the `Engineering-only options` lines) and regenerate it, as described above, so the two stay in sync. Both files ship with the package, so a new release replaces them: keep a copy of your change and re-apply it after updating.

The GUI never enables `engineering_mode`: it only offers options that are not on this list. To make an engineering-only option such as `Amplitude [%]` available in the GUI, an institution has to remove it from the list.


### Trigger, Power, Focus, Ramp and Timing Parameters

The `[Trigger]`, `[Power]`, `[Focus]` and `[Ramp]` sections define the available options that can be selected in the software. Adding new options to these sections requires implementing the corresponding functionality in the codebase to support them.

The `[Timing]` section contains the default `pulse_dur` value used when a script doesn't specify one; every other timing field cascades from it via `configure_timing()`'s own defaults instead of a separate config key.

See [Adding Your Own Equipment](adding-equipment.md) for the equipment-specific case (new
manufacturers, driving systems, transducers, and combinations).

[← Back to README](../README.md)
