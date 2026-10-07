[← Back to README](../README.md)

# 🐍 Install and Run the Python Package

> **Note:** This package is developed specifically for Windows operating systems. While it might work in other environments with some modifications, full support is provided only for Windows.

## 🔧 Installation <a name="install"></a>

To get a local copy up and running, follow these steps.

### Step 1: Clone This Repository to Your Desired Folder

Whichever option below you use, pick the release/tag you want as you go: it determines which
Python version you'll need.

| GUI version | FDS (`fus_driving_systems`) version | Required Python version |
|---|---|---|
| - | 2.2.x and earlier (no GUI yet) | [3.10](https://www.python.org/downloads/release/python-31021/) |
| 0.1.x | 3.0.x | [3.10](https://www.python.org/downloads/release/python-31021/) |

The required Python version is tied to each release, not something you can mix and match freely:
upgrading Python on your own requires a matching `unifus` build from IGT first.

Clone it wherever's convenient; this folder doesn't need to live inside, or anywhere near, your
own project folder. Nothing later depends on its location relative to your own work.

- **Git terminal**
	```
	cd my-folder
	git clone git@github.com:Donders-Institute/Radboud-FUS-driving-system-software.git
	```

	Once cloned, you can checkout the tag for the desired release:
	```
	git checkout [tag_name]
	```

- **GitHub Desktop**
	1. Click on 'Current repository'.
	2. Click on 'Add' and select 'Clone repository...'.
	3. Choose 'URL' and paste the following repository URL: [https://github.com/Donders-Institute/Radboud-FUS-driving-system-software.git](https://github.com/Donders-Institute/Radboud-FUS-driving-system-software.git)
	4. Choose your desired folder and clone the repository. GitHub Desktop clones the default branch;
	   to get a specific release's tag instead, switch to it from the branch/tag selector after
	   cloning.

- **GitHub Website**\
	Download the source code directly for a release. Visit the [Latest Release](https://github.com/Donders-Institute/Radboud-FUS-driving-system-software/releases/latest), or the [full releases list](https://github.com/Donders-Institute/Radboud-FUS-driving-system-software/releases) for an older one, and download that release's Source code (zip) file. Extract it to your desired location and proceed with the installation steps.

### Step 2: Create and Setup a Virtual Environment

#### Already Have a Virtual Environment or Experiment Script?

You don't need a new environment made by this repo's own tooling, as long as it's already on the
Python version from the table in Step 1: `unifus.pyd` is a compiled native extension tied to one
specific Python version, so installing into a mismatched environment fails, or worse, imports but
then fails confusingly later. Activate your existing one and install from the root folder of
your clone of this repository. Choose what you need:

- **Option 1: only the package** (scripts and protocol files, no GUI):
  ```
  call [YOUR_EXISTING_VENV_PATH]\Scripts\activate
  cd [PATH_TO_CLONED_REPO]
  pip install -r requirements.txt
  ```
  This installs `fus_ds_package` and its dependencies, each at the exact version this release
  was tested with. Afterwards, `import fus_driving_systems` works from your existing script
  regardless of where either one lives.

- **Option 2: the package and the GUI**:
  ```
  call [YOUR_EXISTING_VENV_PATH]\Scripts\activate
  cd [PATH_TO_CLONED_REPO]
  pip install -r fus_ds_gui\requirements-gui.txt
  ```
  The GUI is a separate package that needs PySide6, a large download that scripts don't use,
  so it is optional. This installs it together with `fus_ds_package`. Start it from that
  environment with `python -m fus_ds_gui.app`.

Run either command from the root folder: the paths inside the requirements files are relative.
Then skip ahead to [Usage](#usage).

#### Setting Up a New Virtual Environment

Ensure you have the Python version from the table in Step 1 installed and accessible from your command line; download it via the link in that table if you don't have it yet. It is not necessary to add Python to your system's PATH during installation, as virtual environments allow you to manage and switch between Python versions without affecting other projects or code outside the environment.

<div align="center">
  <img src="/images/python_path.png" alt="python_path" width="auto"  height="auto" />
</div>

<br />

Open your command prompt and run the following batch file to set up the virtual environment and install the necessary dependencies. You can use input parameters to customize the environment name, directory, or Python interpreter location. You can use the default values or specify only the parameters you need by leaving others blank with "".

```
cd your_directory_with_cloned_repository
create_venv.bat "[PYTHON_INTERPRETER_PATH]" [VENV_NAME] "[VENV_DIR]" [INSTALL_GUI]
```

- PYTHON_INTERPRETER_PATH: Specify the path to the Python interpreter required for your release (see the table in Step 1 above) if it's not in the default location. For example, C:\Path\To\Python310\python.exe.
- VENV_NAME: Specify the name for the virtual environment (e.g., MyEnv). If not provided, it defaults to FUS_DS_PACKAGE.
- VENV_DIR: Specify the directory for the virtual environment (e.g., C:/Users/Me/Envs). If not provided, it defaults to C:/Users/{USERPROFILE}/Envs.
- INSTALL_GUI: `y` or `n` to install the GUI (`fus_ds_gui`) without being asked. If not provided, the batch file asks. The GUI is optional because it needs PySide6, a large download that scripts don't use.

Example:
```
create_venv.bat "C:\Path\To\Python310\python.exe" FUS_DS_PACKAGE "C:/Users/Me/Envs" y
```
The batch file will create a virtual environment and install the required Python packages; no
IDE is included, see "Step 2: Install an IDE" under Usage below.

If you installed the GUI this way, start it from your activated virtual environment with:
```
python -m fus_ds_gui.app
```

**Troubleshooting**: If you encounter issues with the batch file not being recognized or errors
occur during execution, ensure that the batch file has the correct permissions to be executed,
and that the repository has been cloned correctly and contains the necessary files.

### Step 3: Verify the Successful Setup of the Virtual Environment
Ensure that the virtual environment and dependencies are installed. You can verify this by:

- If you used "Setting Up a New Virtual Environment" above: checking for the virtual environment folder in your VENV_DIR directory.
	<div align="center">
	  <img src="/images/verify_venv.png" alt="verify_venv" width="auto"  height="auto" />
	</div>

- Whichever option under Step 2 you used: confirming that the fus_driving_systems package is installed in the virtual environment's site-packages folder (e.g. VENV_DIR/VENV_NAME/Lib/site-packages/ for a new environment).
	<div align="center">
	  <img src="/images/verify_fus_package.png" alt="verify_fus_package" width="auto"  height="auto" />
	</div>


## 📋 Usage <a name="usage"></a>

### Step 1: Activate Your Environment
With the fus_driving_systems package installed, activate your environment in your command prompt to create and execute TUS protocols.

```
call [VENV_PATH]\Scripts\activate
```

### Step 2: Install an IDE
While your virtual environment is activated, you can install any IDE of your choice. To install
Spyder, this repo's suggested default:

```
pip install spyder==6.0.3
```

To install another IDE instead, run:

```
pip install [IDE]
```

The same `pip install [PACKAGE]` (with the environment activated) also works for anything else
your own experiment script needs, e.g. a stimulus-presentation package like PsychoPy: it installs
alongside `fus_driving_systems` in this same virtual environment, no separate setup required.

### Step 3: Launch the IDE
After installing your IDE, you can launch it directly from the command line while the virtual environment is activated. For Spyder, enter:

```
spyder
```

### Step 4: Open an Example Script
Open one of the example scripts provided in the [example_protocols directory](../example_protocols) in the cloned repository, organized by scenario (e.g. `single_transducer`, `two_transducers_simultaneous`, `alternating_single_pulse_train`, `switch_active_transducer`) and, where more than one manufacturer has a working example, by manufacturer. Each scenario folder has a `standalone_yaml.py` plus its own `protocol.yaml` for most scenarios (a simpler, declarative alternative where the protocol itself is described in a YAML file, see [Loading a Protocol from a YAML File](building-protocols.md#load-yaml)), and a `standalone_plain.py` built directly in Python for full manual control. As a rule of thumb: start from `standalone_yaml.py` if you'd rather keep the protocol's parameters in a plain text file, separate from your code (you still run a short Python script, already provided, to load and use that file); keeping the protocol separate also makes it easier to review, share, or lock against accidental edits (see [Building and Loading Protocols](building-protocols.md#load-yaml)). Use `standalone_plain.py` instead if you're comfortable writing Python and want full control.

These scripts can also be used to explore the functionality of the package before integrating it into your own project.

Once you're ready to build your own experiment, copy the relevant example (script and/or `protocol.yaml`) into your **own project folder, outside this cloned repository**, rather than editing it in place inside `example_protocols/`. The package itself is `pip install`ed, so your own scripts can `import fus_driving_systems` from anywhere; nothing requires them to live inside this repo. Keeping your own work outside the repo also means a future upgrade (see "Installation of New Release" below) never touches it, even if `example_protocols/`'s own structure changes between releases.

Building a `TUSProtocol` in Python, loading one from a YAML file, and wiring FDS calls into a
script you already have (e.g. one that already presents stimuli and needs to trigger ultrasound
alongside that) are covered in
[Building and Loading Protocols](building-protocols.md).

### Activate Your Virtual Environment and Launch the IDE at Once
To simplify the process of activating the virtual environment and launching your IDE, you can use the provided [batch script](../start_venv_and_ide.bat).

How to use the script:
1. Ensure that start_env_and_ide.bat is located in a convenient location, such as the root directory of your project or your desktop. To launch it from your desktop without moving the file itself, right-click `start_venv_and_ide.bat` and choose "Send to > Desktop (create shortcut)".
2. Run the script in one of the following ways:
	- Open start_venv_and_ide.bat in a text editor and modify the VENV_PATH and IDE variables directly if you prefer not to use command-line arguments.
	  To run the .bat file, just double-click it.
	- Using the command prompt:
		```
		start_venv_and_ide.bat [VENV_PATH] [IDE]
		```
		- VENV_PATH: Specify the path to the virtual environment (e.g., C:/Users/Me/Envs/MyEnv). If not provided, it defaults to C:/Users/{USERPROFILE}/Envs/FUS_DS_PACKAGE.
		- IDE: Specify the python interpreter. If not provided, it defaults to spyder.

## 🌟 Installation of New Release <a name="install-new-release"></a>

As long as your own scripts/protocol files live in your own project folder, outside this cloned
repository (see "Step 4: Open an Example Script" above), upgrading never touches them; there's
nothing to back up or restore first. Just clone the new release into a fresh directory as usual.

### Step 1: Clone the Repository to Your Desired Folder
Same as [Step 1 under Installation](#install) above (into a fresh directory, not over your
existing checkout), including checking out the release tag you want.

### Step 2: Install the New Release in Your Virtual Environment
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

### Step 3: Check the Release Notes
Review the release notes for any breaking changes that might affect your own scripts/protocol files, and update them accordingly.

If you'd customized `ds_config.ini` (e.g. a raised safety limit, either by hand-editing it
directly or via your own `create_config.py` change, see [Configuration](configuration.md#config)),
reapply that customization too: installing a new release always ships its own freshly regenerated
copy, silently overwriting any override from before.

[← Back to README](../README.md)

## 🛠️ For Developers <a name="developers"></a>

For anyone working on the package or the GUI itself; regular script and GUI usage don't need any of this.

### Development environment

`requirements-dev.txt` installs everything to work on both packages: the test tools, the pinned
dependencies, and `fus_ds_package` and `fus_ds_gui` themselves in editable mode, so your local
edits are picked up without reinstalling after every change. It is also what the CI workflow
installs: pytest and coverage must see your checked-out source, not a copy in `site-packages`.
From the repository root, with your virtual environment activated:
```
pip install -r requirements-dev.txt
```
Only working on the package, without the GUI? `requirements-ci.txt` is the same without it
(and without PySide6).

### Running the tests

Package tests, from the repository root:
```
cd fus_ds_package
pytest -m "not hardware"
```
`-m "not hardware"` skips the tests that need a real driving system.

GUI tests, with the same environment:
```
cd fus_ds_gui
pytest
```

### Hardware tests

The tests that need a real driving system live in `fus_driving_systems/tests/hardware/`, for IGT
and Sonic Concepts.
Both are meant for a driving system with a dummy load attached, never a real transducer. A dummy
load cannot be selected as a transducer on a TPO, so for Sonic Concepts leave whichever
transducer is selected and tell the tests which one it is: the TPO rejects focus values outside
that transducer's range. They only run when you opt in with two separate things: select them with `pytest -m hardware --no-cov`, and set the
environment variable `FDS_HARDWARE_TESTS=1`. With your virtual environment activated, run this
from the `fus_ds_package` folder of the repository (not the virtual environment), in the Command
Prompt:
```
set FDS_HARDWARE_TESTS=1&& python -m pytest -m hardware --no-cov fus_driving_systems/tests/hardware
```
Or in PowerShell:
```
$env:FDS_HARDWARE_TESTS = "1"; python -m pytest -m hardware --no-cov fus_driving_systems/tests/hardware
```
Which driving system and transducer the tests use is set with environment variables, so there
is nothing to edit in the test files. For IGT you need none if the `IGT 256 ch. - 1 x 10 ch.
(TEST)` setup is active in `ds_config.ini`. For Sonic Concepts you need two: the driving system,
and the transducer that is currently selected on the TPO. A variable stays set for as long as
that terminal window is open, so you can enter them one line at a time and run the tests
again afterwards with just the last line. In the Command Prompt:
```
set FDS_HARDWARE_TESTS=1
set FDS_HW_SC_DRIVING_SYSTEM=105-010
set FDS_HW_SC_TRANSDUCER=[TRANSDUCER_SERIAL]
python -m pytest -m hardware --no-cov fus_driving_systems/tests/hardware
```
Or in PowerShell:
```
$env:FDS_HARDWARE_TESTS = "1"
$env:FDS_HW_SC_DRIVING_SYSTEM = "105-010"
$env:FDS_HW_SC_TRANSDUCER = "[TRANSDUCER_SERIAL]"
python -m pytest -m hardware --no-cov fus_driving_systems/tests/hardware
```
You can set more of them the same way:
- IGT: `FDS_HW_DRIVING_SYSTEM`, `FDS_HW_TRANSDUCER` (the "pretend" transducer), `FDS_HW_FOCUS_MM`,
  `FDS_HW_AMPLITUDE_PERCENT` and `FDS_HW_VOLTAGE_TOLERANCE_PERCENT`.
- Sonic Concepts: `FDS_HW_SC_PORT` and `FDS_HW_SC_POWER_W`.

Their defaults and the safety limits are described at the top of `tests/hardware/conftest.py`.

Prefer not to type them? Fill in the settings at the top of `fus_ds_package\run_hardware_tests.bat`,
choose `igt` or `sc` for the equipment that is connected, and double-click it, or run it from a
Command Prompt. Extra arguments go to pytest, for example `run_hardware_tests.bat -k abort` to run only
the abort tests.
