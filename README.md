# Radboud FUS driving system software
<a name="readme-top"></a>

<div align="center">
  <img src="/images/donders_logo.svg" alt="donders_logo" width="auto" height="70">
  <img src="/images/logo_FUS_CENTRE.png" alt="fus_centre_logo" width="auto" height="70">
  <br>
  <img src="/images/igtlogo.jpeg" alt="igt_logo" width="auto" height="70">
  <img src="/images/Radboud-logo.jpg" alt="ru_logo" width="auto" height="70" />
</div>


<!-- TABLE OF CONTENTS -->

# 📗 Table of Contents

- [📖 About the Project](#about-project)
  - [🚀 Key Features](#features)
  - [👥 Authors](#authors)
  - [✒️ How to cite](#how-to-cite)
- [💻 Getting Started](#getting-started)
  - [🔧 Installation](#install)
  - [📋 Usage](#usage)
- [🧰 Configuration](#config)
  - [⚙️ Configuring System Parameters](#other-config)
  - [📻 How to add your own equipment](#add-equip)
- [🌟 Installation of new release](#install-new-release)
- [🔭 Future Features](#future-features)
- [🤝 Contributing](#contributing)
- [📝 License](#license)
  
<!-- PROJECT DESCRIPTION -->

# 📖 Radboud FUS driving system software <a name="about-project"></a>

(Project id: **0003496**)

The **Radboud FUS driving system software** is designed to streamline the integration of new focused ultrasound equipment into your workflow. It enables control of the equipment while limiting the need for users to familiarize themselves with new software interfaces. 

This project is facilitated by the Radboud FUS Centre. For more information, please visit the [website](https://www.ru.nl/en/donders-institute/research/research-facilities/focused-ultrasound-initiative-fus).

**⚠️ DEVELOPMENT STATUS**: This repository is currently under active development and is provided AS IS. Features may be incomplete, undergo significant changes, or contain bugs. Use at your own discretion.

## 🚀 Key Features <a name="features"></a>
- **Seamless Integration**: The current version offers essential functionality that can be easily integrated into your experimental code to control the system during your experiments.
- **Compatibility**: This package is also a prerequisite for the latest version of the [SonoRover One software](https://github.com/Donders-Institute/Radboud-FUS-measurement-kit), which utilizes it to communicate with your focused ultrasound equipment. 
By adhering to a standardized communication structure, the characterization software does not need to directly handle communication protocols. Instead, it uses the same codebase for both standalone and experimental settings, ensuring consistent and centralized updates to equipment communication.

This project is facilitated by the Radboud FUS Centre. For more information, please visit the [website](https://www.ru.nl/en/donders-institute/research/research-facilities/focused-ultrasound-initiative-fus).

<!-- AUTHORS -->

## 👥 Authors <a name="authors"></a>

👤 **[Margely Cornelissen](https://www.ru.nl/en/people/cornelissen-m), [FUS Centre](https://www.ru.nl/en/donders-institute/research/research-facilities/focused-ultrasound-initiative-fus), Radboud University**
- GitHub: [@MaCuinea](https://github.com/MaCuinea)
- [LinkedIn](https://linkedin.com/in/margely-cornelissen)

👤 **[Stein Fekkes](https://www.ru.nl/en/people/fekkes-s), [FUS Centre](https://www.ru.nl/en/donders-institute/research/research-facilities/focused-ultrasound-initiative-fus), Radboud University**

- GitHub: [@StefFek-GIT](https://github.com/StefFek-GIT)
- [LinkedIn](https://linkedin.com/in/sfekkes)

👤 **Erik Dumont, [Image Guided Therapy (IGT)](http://www.imageguidedtherapy.com/)**
- GitHub: [@erikdumontigt](https://github.com/erikdumontigt)
- [LinkedIn](https://linkedin.com/in/erik-dumont-986a814)

👤 **Lennart Verhagen, FUS Centre, Radboud University**
- GitHub: [@lennartverhagen](https://github.com/lennartverhagen)
- [LinkedIn](https://nl.linkedin.com/in/lennartverhagen)

<p align="right">(<a href="#readme-top">back to top</a>)</p>

## ✒️ How to cite <a name="how-to-cite"></a>

If you use this package in your research or project, please cite it as follows (see also `CITATION.cff`):

Margely Cornelissen, Stein Fekkes (FUS Centre, Radboud University, Nijmegen, The Netherlands), Erik Dumont (Image Guided Therapy, Pessac, France) & Lennart Verhagen (FUS Centre, Radboud University, Nijmegen, The Netherlands) (2024-2026), Radboud FUS Driving System Software (version 2.2.3)

<p align="right">(<a href="#readme-top">back to top</a>)</p>

<!-- GETTING STARTED -->

# 💻 Getting Started <a name="getting-started"></a>

**Note:** This package is developed specifically for Windows operating systems. While it might work in other environments with some modifications, full support is provided only for Windows.

To get a local copy up and running, follow these steps.

## 🔧 Installation <a name="install"></a>

### Step 1: Clone this repository to your desired folder
- Git terminal
	```
	cd my-folder
	git clone git@github.com:Donders-Institute/Radboud-FUS-driving-system-software.git
	```
	
	Once cloned, you can checkout the tag for the desired release:
	```
	git checkout [tag_name]
	```

- GitHub Desktop
	1. Click on 'Current repository'.
	2. Click on 'Add' and select 'Clone repository...'.
	3. Choose 'URL' and paste the following repository URL: [https://github.com/Donders-Institute/Radboud-FUS-driving-system-software.git](https://github.com/Donders-Institute/Radboud-FUS-driving-system-software.git)
	4. Choose your desired folder and clone the repository.

- GitHub\
	Download the source code directly for the latest release. Visit the [Latest Release](https://github.com/Donders-Institute/Radboud-FUS-driving-system-software/releases/latest), and download the Source code (zip) file. Extract it to your desired location and proceed with the installation steps.

### Step 2: Download Python 3.10
Ensure you have Python 3.10 installed and accessible from your command line. If Python is not installed, download it from the [official Python website](https://www.python.org/downloads/release/python-31011/). It is not necessary to add Python to your system's PATH during installation, as virtual environments allow you to manage and switch between Python versions without affecting other projects or code outside the environment.

<div align="center">
  <img src="/images/python_path.png" alt="python_path" width="auto"  height="auto" />
</div>

<br /> 

**Note**: The script assumes that Python 3.10 is installed. If you have a different version, make sure to adjust the script accordingly or install Python 3.10.

### Step 3: Create and setup a virtual environment
Open your command prompt and run the following batch file to set up the virtual environment and install the necessary dependencies. You can use input parameters to customize the environment name or directory, or Python interpreter location. You can use the default values or specify only the parameters you need by leaving others blank with "".

```
cd your_directory_with_cloned_repository
create_venv.bat "[PYTHON_INTERPRETER_PATH]" [VENV_NAME] "[VENV_DIR]"
```
	
- PYTHON_INTERPRETER_PATH: Specify the path to the Python 3.10 interpreter if it’s not in the default location. For example, C:\Path\To\Python310\python.exe.
- VENV_NAME: Specify the name for the virtual environment (e.g., MyEnv). If not provided, it defaults to FUS_DS_PACKAGE.
- VENV_DIR: Specify the directory for the virtual environment (e.g., C:/Users/Me/Envs). If not provided, it defaults to C:/Users/{USERPROFILE}/Envs.

Example:
```
create_venv.bat "C:\Path\To\Python310\python.exe" FUS_DS_PACKAGE "C:/Users/Me/Envs"
```
The batch file will create a virtual environment, install the required Python packages and the default IDE, Spyder.

**DCCN specific configuration**
	
To use the DCCN-specific default values, you can provide a fourth input parameter to activate these settings.

Example:
```
create_venv.bat "" "" "" "DCCN"
```

### Step 4: Verify the successful setup of the virtual environment
After running the batch file, ensure that the virtual environment and dependencies are installed. You can verify this by:

- Checking for the virtual environment folder in your VENV_DIR directory.
	<div align="center">
	  <img src="/images/verify_venv.png" alt="verify_venv" width="auto"  height="auto" />
	</div>

- Confirming that the fus_driving_systems package is installed in the virtual environment site-packages folder: VENV_DIR/VENV_NAME/Lib/site-packages/.
	<div align="center">
	  <img src="/images/verify_fus_package.png" alt="verify_fus_package" width="auto"  height="auto" />
	</div>
	

### Troubleshooting
If you encounter issues with the batch file not being recognized or errors occur during execution, ensure that:

- The batch file has the correct permissions to be executed.
- The repository has been cloned correctly and contains the necessary files.

## 📋 Usage <a name="usage"></a>

### Step 1: Activate your environment
With the fus_driving_systems package installed, activate your environment in your command prompt to create and execute TUS protocols. 

```
call [VENV_PATH]\Scripts\activate
```

### Step 2: Install an IDE
While your virtual environment is activated, you can install any IDE of your choice. Spyder is pre-installed by default. To install another IDE, run:

```
pip install [IDE]
```

### Step 3: Launch the IDE
After installing your IDE, you can launch it directly from the command line while the virtual environment is activated. For Spyder, enter:

```
spyder
```

### Step 4: Open the main script
Open one of the example scripts provided in the [example_protocols directory](example_protocols) in the cloned repository, organized by scenario (e.g. `single_transducer`, `two_transducers_simultaneous`, `alternating_single_pulse_train`, `switch_active_transducer`) and, where more than one manufacturer has a working example, by manufacturer. Each scenario folder has a `standalone_plain.py` (built directly in Python, full manual control) and, for most scenarios, a `standalone_yaml.py` plus its own `protocol.yaml` -- a simpler, declarative alternative where the protocol itself is described in a YAML file instead (see "Load a protocol from a YAML file" below).

Follow the instructions within the code to understand how to integrate it into your own codebase. Additionally, these scripts can be utilized to explore the functionality of the package before integrating it into your project.

Once you're ready to build your own experiment, copy the relevant example (script and/or `protocol.yaml`) into your **own project folder, outside this cloned repository**, rather than editing it in place inside `example_protocols/`. The package itself is `pip install`ed, so your own scripts can `import fus_driving_systems` from anywhere -- nothing requires them to live inside this repo. Keeping your own work outside the repo also means a future upgrade (see "Installation of new release" below) never touches it, even if `example_protocols/`'s own structure changes between releases.

### Activate your virtual environment and launch the IDE at once
To simplify the process of activating the virtual environment and launching your IDE, you can use the provided [batch script](start_venv_and_ide.bat).

How to use the script:
1. Ensure that start_env_and_ide.bat is located in a convenient location, such as the root directory of your project or your desktop.
2. Run the script in one of the following ways:
	- Open start_venv_and_ide.bat in a text editor and modify the VENV_PATH and IDE variables directly if you prefer not to use command-line arguments.
	  To run the .bat file, just double-click it.
	- Using the command prompt:
		```
		start_venv_and_ide.bat [VENV_PATH] [IDE]
		```
		- VENV_PATH: Specify the path to the virtual environment (e.g., C:/Users/Me/Envs/MyEnv). If not provided, it defaults to C:/Users/{USERPROFILE}/Envs/FUS_DS_PACKAGE.
		- IDE: Specify the python interpreter. If not provided, it defaults to spyder.
		
		**DCCN specific configuration**

		To use the DCCN-specific default values, you can soly provide the first input parameter to activate these settings.

		Example:
		```
		start_venv_and_ide.bat "" "" "DCCN"
		```

<p align="right">(<a href="#readme-top">back to top</a>)</p>

# 🌟 Installation of new release <a name="install-new-release"></a>

As long as your own scripts/protocol files live in your own project folder, outside this cloned
repository (see "Step 4: Open the main script" above), upgrading never touches them -- there's
nothing to back up or restore first. Just clone the new release into a fresh directory as usual.

## Step 1: Clone the repository to your desired folder
- Git terminal
	```
	cd my-folder
	git clone git@github.com:Donders-Institute/Radboud-FUS-driving-system-software.git
	```
	
	Once cloned, you can checkout the tag for the desired release:
	```
	git checkout [tag_name]
	```
- GitHub Desktop
	1. Click on 'Current repository'.
	2. Click on 'Add' and select 'Clone repository...'.
	3. Choose 'URL' and paste the following repository URL: [https://github.com/Donders-Institute/Radboud-FUS-driving-system-software.git](https://github.com/Donders-Institute/Radboud-FUS-driving-system-software.git)
	4. Choose your desired folder and clone the repository.
	
- GitHub\
	Download the source code directly for the latest release. Visit the [Latest Release](https://github.com/Donders-Institute/Radboud-FUS-driving-system-software/releases/latest), and download the Source code (zip) file. Extract it to your desired location and proceed with the installation steps.

## Step 2: Install the new release in your virtual environment
- Open your command prompt and activate your virtual environment:
	```
	call [VENV_PATH]\Scripts\activate
	```
- Navigate to the cloned repository's directory:
	```
	cd your_directory_with_cloned_repository
	```
	
- Install the package:
	```
	pip install .\fus_ds_package
	```

## Step 3: Check the release notes
Review the release notes for any breaking changes that might affect your own scripts/protocol files, and update them accordingly.

<p align="right">(<a href="#readme-top">back to top</a>)</p>

<!-- CONFIGURATION -->

# 🧰 Configuration <a name="config"></a>

The Radboud FUS Driving System software can be customized through its configuration file to match your specific requirements. This section explains what can be configured and how to properly modify settings.

## Common Configuration Tasks

Here are some frequently adjusted settings:

- **Change equipment**: Add/edit entries in [create_config.py](fus_ds_package/fus_driving_systems/config/create_config.py)'s `[Equipment]`-related sections, then regenerate `ds_config.ini` from it -- see [Adding Your Own Equipment](#add-equip)
- **Adjust safety limits**: Update `maximum pressure allowed in free water` in the `[Power]` section
- **Modify logging behavior**: Change log levels and paths in the `[Logging]` section

## Important Notes

- Some settings are interdependent - for example, changing power options may require corresponding adjustments to equipment configurations or even code modifications
- Many of the default values in the configuration file are currently used by the GUI of the Radboud-FUS-measurement-kit. In future releases, we plan to develop a dedicated GUI for the Radboud-FUS-driving-system-software that will utilize these same configuration parameters.
- Always verify system behavior after making configuration changes
- The maximum values for many parameters are hardware-dependent

If you encounter issues after modifying the configuration:
1. Verify syntax and formatting in the configuration file
2. Check hardware connections and compatibility
3. Review logs for specific error messages
4. Revert to a known working configuration if needed

## ⚙️ Configuring System Parameters <a name="other-config"></a>

The package includes a comprehensive configuration file [ds_config.ini](fus_ds_package/fus_driving_systems/config/ds_config.ini) that controls various aspects of the system -- but it is a **generated file**, produced by running [create_config.py](fus_ds_package/fus_driving_systems/config/create_config.py), and should not be hand-edited directly: any direct edit is silently lost the next time `create_config.py` runs, or the moment a new package release is installed (which ships its own freshly generated copy). To change something, edit `create_config.py` instead:

1. Open [create_config.py](fus_ds_package/fus_driving_systems/config/create_config.py) and make your changes there (see [Adding Your Own Equipment](#add-equip) for the equipment-specific case)
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
- **log level file**: Minimum severity level saved to file (INFO includes informational messages)
- **initial part of log filename**: Prefix for all log files

### Safety Setting

```ini
[Power]
# ...options...
maximum pressure allowed in free water [mpa] = 1.4
```

The maximum pressure setting (1.4 MPa by default) serves as a safety limit. Adjust this based on your specific requirements, but exercise caution to maintain safety. Note that this is a hand-edit to a generated file: it will be silently overwritten if `ds_config.ini` is ever regenerated via `create_config.py`, or replaced by installing a new package release -- keep a copy of your override if you rely on it long-term.

Both `[Power]` and `[Focus]` also have an `engineering-only options` key (e.g. `Amplitude [%]\nVoltage [V]` for `[Power]`, `Focus wrt mid bowl [mm]` for `[Focus]`) listing which options require `TUSProtocol(driving_sys_serial, engineering_mode=True)` to set directly. This check applies uniformly to every power/focus option (`global power`, `max. pressure in free water`, `amplitude`, `voltage`, `focus wrt exit plane`, `focus wrt mid bowl`) -- it's an institutional safety policy choice, not a hardware requirement, and none of these six are hardcoded as exempt. By default only amplitude/voltage/mid-bowl-focus are listed (matching this package's original behavior); remove any of them if your institution doesn't need that gate, or add any of the other three (or clear the list entirely) if you want to gate additional options -- all without touching code.


### Trigger, Power, Focus, Ramp and Timing Parameters

The `[Trigger]`, `[Power]`, `[Focus]` and `[Ramp]` sections define the available options that can be selected in the software. Adding new options to these sections requires implementing the corresponding functionality in the codebase to support them.

The `[Timing]` section contains default values regarding pulse timing.


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
1. Create a new folder within [fus_ds_package/fus_driving_systems/](fus_ds_package/fus_driving_systems) (e.g., `your_manufacturer_name/`)
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

### Step 3: Create a Standalone Script

1. Create a new scenario folder under [example_protocols/](example_protocols) (e.g., `example_protocols/your_manufacturer/`), or add a manufacturer subfolder to an existing scenario if it fits one already.
2. Use existing scripts (like [standalone_plain.py](example_protocols/single_transducer/sonic_concepts/standalone_plain.py)) as templates.
3. In the first section: Define user input by setting appropriate TUSProtocol parameters. Configure the code according to your specific equipment by adjusting timing parameters, power input levels, and other relevant settings.
4. In the second section: Import your new driving system script and initialize an instance of the class. The invocation of the implemented abstract functions (connect, send_protocol, execute_protocol, disconnect) can remain the same.

A `TUSProtocol` is created with its driving system serial as a required argument (e.g. `TUSProtocol('YOUR-SYSTEM-ID')`). `protocol.get_power_options()`/`get_focus_options()` are available right away, before any slot has been added, since `add_slot()` itself needs a valid option string to call. It starts with zero transducer slots; call `add_slot(transducer_serial, focus_option, focus_value, power_option, power_value)` once per transducer before using the protocol (all five arguments are required -- a slot is never half-configured; `oper_freq`/`dephasing_degree` can optionally be given too, as keyword arguments, though neither has the same ordering hazard so setting them on the returned slot afterward works just as well). There is no single-slot delegation on `TUSProtocol` itself (no `protocol.press`/`protocol.transducer`/etc.) -- every per-transducer attribute is always addressed via `protocol.slots[i].<attribute>`, whether there's one transducer or several, so a script is never in doubt about which access style applies. `add_slot()` returns the newly added slot, so scripts typically just keep that reference (`slot = protocol.add_slot(...)`) rather than indexing back into `protocol.slots` afterward. For a driving system with `max. transducer slots > 1`, call `add_slot()` again for each additional transducer (each transducer's element count must fit within `available channels / max. transducer slots`); `IGT.send_protocol()`/`wait_for_trigger()`/`execute_protocol()` also accept a *list* of `TUSProtocol` objects to interleave them as one alternating group. When interleaving, each protocol contributes exactly one pulse per round of the alternating group, not a repeated pulse train of its own -- `pulse_dur`/`pulse_rep_int` still apply per protocol (`pulse_rep_int` decides how much of the shared round this protocol's own pulse occupies), but `pulse_train_dur`/`pulse_train_rep_int`/`pulse_train_rep_dur` currently have no effect in that case.

To change an already-added slot's focus/power later (e.g. mid-experiment, then re-send the same protocol) without constructing an entirely new `TUSProtocol`, call `protocol.slots[i].configure(focus_option, focus_value, power_option, power_value)` -- it applies focus before power internally, same as `add_slot()`, regardless of the order the arguments are given in. `focus_wrt_exit_plane`/`focus_wrt_mid_bowl`/`global_power`/`press`/`volt`/`ampl` are read-only -- `configure()` is the only way to set any of them, since setting one directly, without an already-correct focus, can silently compute a wrong value on driving systems that need a calibration curve to convert between them.

To swap an already-added slot's transducer for a different one, call `protocol.slots[i].update_transducer(transducer_serial, focus_option, focus_value, power_option, power_value)` directly on that slot -- like `add_slot()`, all five of these are required (the new transducer's calibration curve/geometric range differ from the old one's, so old focus/power numbers can't just be assumed to still be correct). `oper_freq`/`dephasing_degree` are optional here too, but `dephasing_degree` always resets to `None` (no dephasing) when not given, rather than carrying over from the old transducer -- a dephasing list is sized to a specific transducer's element count, so one built for the old transducer isn't safe to assume for the new one. `add_slot()` itself is a thin wrapper around this same method (it constructs a bare slot, then calls `update_transducer()` on it) -- so this per-slot element-count check always runs, whether a slot is being configured for the first time or swapped later; `TUSProtocol`'s own aggregate channel-count check only runs from `add_slot()`, since (per the per-slot ceiling `available channels / max. transducer slots`) a swap that keeps every slot within its own ceiling can never push the total over `available channels` either.

`TUSProtocol.configure_timing(pulse_dur, pulse_rep_int=None, pulse_train_dur=None, trigger_option=None, pulse_ramp_shape=None, pulse_ramp_dur=None, n_triggers=None, pulse_train_rep_int=None, pulse_train_rep_dur=None)` is the only way to set any timing/trigger parameter -- `pulse_dur`, `pulse_rep_int`, `pulse_train_dur`, `pulse_train_rep_int`, `pulse_train_rep_dur`, `pulse_ramp_shape`, `pulse_ramp_dur`, `trigger_option` and `n_triggers` all have getters only, precisely because they cascade/interact with each other and are prone to ordering hazards if set individually and out of order (e.g. `pulse_train_dur` before `pulse_dur`, or `trigger_option` before `pulse_train_rep_dur`). `pulse_dur` is the only required argument -- every level above it defaults to the level directly below it when not given, so a single pulse train, repeated once, is already a complete, self-consistent result. `trigger_option`/`pulse_ramp_shape`/`pulse_ramp_dur` left as `None` do **not** inherit whatever was configured before -- they reset to their own safe/off default every single call (the config's "no trigger" option; "no ramping"; `0`), the same way `pulse_dur`'s own family resets to "repeat once" rather than reusing a stale value. This matters most for `trigger_option`, since it decides whether the driving system waits for an external trigger at all: pass it explicitly every time a trigger is actually wanted.

`'TriggerOnePulseTrain'` fires exactly one pulse train per external trigger received, so the driving system needs to know in advance how many to expect: `n_triggers` is *required* (not optional) specifically for this trigger option, and `pulse_train_rep_int`/`pulse_train_rep_dur` don't apply at all. Every other `trigger_option` -- `'None'` (no trigger) or `'TriggerWholeProtocol'` (one trigger fires the entire, already fully-timed protocol at once, equivalent to executing it directly but gated behind a single external trigger) alike -- uses `pulse_train_rep_int`/`pulse_train_rep_dur` instead, and `n_triggers` isn't valid there. `pulse_train_rep_int`/`pulse_train_rep_dur` may be given together, or just one of the two, or neither: `pulse_train_rep_int` defaults to `pulse_train_dur` (back-to-back repetition) when not given; only *then* does `pulse_train_rep_dur` default to that interval (i.e. "repeat exactly once") when not given -- so giving only `pulse_train_rep_dur` (a total span) fills it back-to-back, while giving only `pulse_train_rep_int` (or neither) collapses to a single repetition.

There is no `wait_for_trigger` parameter to set, on `configure_timing()` or on `TUSProtocol` directly -- `protocol.wait_for_trigger` is a read-only property, derived from `trigger_option`: `True` whenever `trigger_option` is anything other than the config's designated "no trigger" option (`'None'` by default), mirroring how there is no separate "is ramping enabled" flag either (see `pulse_ramp_shape`). To stop waiting for a trigger, set `trigger_option` to that "no trigger" option instead of a boolean.

#### Load a protocol from a YAML file

Instead of building a `TUSProtocol` directly in Python, `fus_driving_systems.protocol_loader.load_protocol(yaml_path, engineering_mode=False)` parses a YAML file into ready-to-use `TUSProtocol` object(s) -- a simpler alternative aimed specifically at researchers who need to adjust a protocol's parameters without writing or editing Python. It returns `(protocols, total_alternating_duration_ms)`: `protocols` is always a list (even for a single protocol), and `total_alternating_duration_ms` is `None` unless the file describes more than one protocol to interleave -- both are meant to be forwarded straight into `send_protocol()`/`wait_for_trigger()`/`execute_protocol()`.

```yaml
driving_sys_serial: IGT-32-ch_comb_2x10-ch

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
      trigger_option: TriggerWholeProtocol  # optional

total_alternating_duration_ms: null  # only needed when protocols above has more than one entry
```

Every field mirrors a Python parameter name 1:1 (`slots[i]` -> `add_slot()`'s arguments, `timing` -> `configure_timing()`'s keyword arguments) -- an omitted or `null` optional field falls back to exactly the same default `add_slot()`/`configure_timing()` would already use. Semantic mistakes (an unknown driving-system/transducer serial, an invalid focus/power/trigger option, an out-of-range timing value) are not re-validated by the loader -- they surface via `TUSProtocol`/`add_slot()`/`configure_timing()`'s own existing, clear error messages, exactly as if you'd written the equivalent Python yourself. The loader does check the file's own structure: every required key must be present, and an unrecognized/typo'd key (anywhere in the file) is rejected immediately rather than silently doing nothing.

When a file's `protocols` list has more than one entry (interleaving several protocols as one alternating group), every entry's `timing.pulse_ramp_shape`/`pulse_ramp_dur`/`trigger_option`/`n_triggers` must be identical (the same requirement `send_protocol()`/`wait_for_trigger()` already enforce for Python-built protocols) -- there is no way in YAML to share these values automatically between entries, so double-check they stay in sync if you ever change one.

See [example_protocols/](example_protocols) for a `protocol.yaml`/`standalone_yaml.py` pair in most scenario folders, alongside that scenario's `standalone_plain.py` (the full, manually-written Python equivalent).

**Optional: protect a protocol file against accidental edits.** Once you're happy with a `protocol.yaml`, you can run `python -m fus_driving_systems.approve_protocol path/to/protocol.yaml` to write a sidecar `path/to/protocol.yaml.sha256` file next to it, recording its current SHA-256 hash. From then on, `load_protocol()` will refuse to load that file (with a clear `sys.exit()`) if its content ever changes without also re-running `approve_protocol` on it -- catching an accidental edit before it silently changes what gets sent to a driving system. This is opt-in by default: a protocol file with no `.sha256` sidecar is loaded without any check at all, and `load_protocol()` itself never creates or updates one -- `approve_protocol()` is the only way to do that, so it always reflects a deliberate decision that the current content is correct.

If you want a specific script to refuse to run against an unapproved protocol at all (rather than silently loading it unchecked whenever no sidecar happens to exist), pass `require_hash=True` to `load_protocol()`. This is a Python-level parameter, set directly in your own script, next to `engineering_mode`.

```python
protocols, total_alternating_duration_ms = load_protocol(
    'protocol.yaml',
    require_hash=True,  # exits if protocol.yaml.sha256 is missing or doesn't match
)
```

To use your new equipment with custom serial numbers for driving systems and transducers, you'll need to update the configuration file. You can either modify the [ds_config.ini](fus_ds_package/fus_driving_systems/config/ds_config.ini) file directly or modify and regenerate it using the provided [create_config.py](fus_ds_package/fus_driving_systems/config/create_config.py) script. How and what to modify is explained in the next step.

### Step 4: Update the Configuration File

`ds_config.ini` is a **generated file** -- never add your equipment there directly, since any hand-edit is silently lost the next time [create_config.py](fus_ds_package/fus_driving_systems/config/create_config.py) runs, or the moment a new package release is installed. Add your equipment to `create_config.py` instead, then regenerate `ds_config.ini` from it (Step 5 below).

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
- **focus options**: Same idea, for focus -- one or both of `Focus wrt exit plane [mm]`/`Focus wrt mid bowl [mm]`, whichever this system supports at all (e.g. a system that never has a focus-conversion calibration should only list its native option here).
- **native power parameters**: Which of *power options* this system's hardware accepts directly, without needing a calibration curve to convert it (e.g. amplitude for IGT, global power for Sonic Concepts, voltage for CITRUS). A native parameter never needs an active calibration to be set (subject to the separate `engineering-only options` check below, if applicable); setting any other power option (that's still listed in *power options*) always requires an active `Equipment.Combination.*` entry (see step 4) to convert it, regardless of `engineering-only options`. Usually a single value, but if your system's hardware genuinely accepts more than one power representation directly, list them all, one per line (like *power options* above).
- **native focus parameters**: Same idea, for focus -- one or more of `Focus wrt exit plane [mm]`/`Focus wrt mid bowl [mm]`, whichever this system's hardware accepts directly.
- **transducer compatibility**: List of compatible transducer IDs. `TUSProtocol.add_slot()`/`protocol.slots[i].update_transducer()` exit with a clear error if you try to assign a transducer that isn't listed here for this driving system.
- **max. transducer slots**: How many transducers this driving system can drive simultaneously. Defaults to `1` (single-transducer-only) when omitted -- only set this above `1` for a driving system that genuinely supports it (e.g. IGT's `_comb_2x10-ch`-style configs).
- **max. buffers**: How many hardware buffers this driving system can hold a protocol in at once -- each buffer can be pre-loaded with its own protocol ahead of time and triggered/executed independently (see `TUSProtocol.buffer_num`). Defaults to `1` (no real buffer concept, `buffer_num` is then only ever `0`) when omitted -- all current IGT systems declare `2` here.
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
- **steer information**: Path to steering information file if applicable
- **active?**: Whether this transducer is active and available for use

#### 4. Add Equipment Combinations (advanced feature, if needed)
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

<p align="right">(<a href="#readme-top">back to top</a>)</p>

<!-- FUTURE FEATURES -->

# 🔭 Future Features <a name="future-features"></a>

- [ ] Interactive GUI for visualization, planning, and execution of ultrasound protocols

<p align="right">(<a href="#readme-top">back to top</a>)</p>

<!-- CONTRIBUTING -->

# 🤝 Contributing <a name="contributing"></a>

Contributions, issues, and feature requests are welcome!

Feel free to check the [issues page](../../issues/).

If you have any questions, please feel free to reach out to us via email at fus@ru.nl.
We'd love to hear from you.

<p align="right">(<a href="#readme-top">back to top</a>)</p>

# 📝 License <a name="license"></a>

This project is [MIT](./LICENSE) licensed.

<p align="right">(<a href="#readme-top">back to top</a>)</p>
