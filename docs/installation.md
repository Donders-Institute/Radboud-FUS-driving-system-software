[← Back to README](../README.md)

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

#### Version compatibility

The required Python version is tied to `fus_driving_systems`/`fus_ds_gui`, not something you can
mix and match freely: IGT's `unifus.pyd` is a compiled native extension built against one
specific Python version, so upgrading Python requires a matching `unifus` build from IGT first.

| GUI version | FDS (`fus_driving_systems`) version | Required Python version |
|---|---|---|
| 0.1.x | 2.2.x | 3.10 |

Add a row here whenever either version requires a different Python version than the row above it.

### Step 3: Create and setup a virtual environment

**Already have your own virtual environment and experiment script?** You don't need a new
environment made by this repo's own tooling. Activate your existing one and install the package
directly from your clone of this repository:
```
call [YOUR_EXISTING_VENV_PATH]\Scripts\activate
pip install [PATH_TO_CLONED_REPO]\fus_ds_package
```
The cloned repository doesn't need to live inside (or anywhere near) your own project folder;
once installed, `import fus_driving_systems` works from your existing script regardless of where
either one lives. Skip ahead to [Usage](#usage) from here.

Otherwise, open your command prompt and run the following batch file to set up the virtual environment and install the necessary dependencies. You can use input parameters to customize the environment name or directory, or Python interpreter location. You can use the default values or specify only the parameters you need by leaving others blank with "".

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
Open one of the example scripts provided in the [example_protocols directory](../example_protocols) in the cloned repository, organized by scenario (e.g. `single_transducer`, `two_transducers_simultaneous`, `alternating_single_pulse_train`, `switch_active_transducer`) and, where more than one manufacturer has a working example, by manufacturer. Each scenario folder has a `standalone_plain.py` (built directly in Python, full manual control) and, for most scenarios, a `standalone_yaml.py` plus its own `protocol.yaml` -- a simpler, declarative alternative where the protocol itself is described in a YAML file instead (see "Load a protocol from a YAML file" in [Adding Your Own Equipment](adding-equipment.md)).

Follow the instructions within the code to understand how to integrate it into your own codebase. Additionally, these scripts can be utilized to explore the functionality of the package before integrating it into your project.

Once you're ready to build your own experiment, copy the relevant example (script and/or `protocol.yaml`) into your **own project folder, outside this cloned repository**, rather than editing it in place inside `example_protocols/`. The package itself is `pip install`ed, so your own scripts can `import fus_driving_systems` from anywhere -- nothing requires them to live inside this repo. Keeping your own work outside the repo also means a future upgrade (see "Installation of new release" below) never touches it, even if `example_protocols/`'s own structure changes between releases.

### Integrating into an existing experimental script

The example scripts are self-contained (their own logging setup, their own `try`/`finally`), but
adding FDS to a script you already have only needs the calls inside that structure, not the
structure itself:

```python
from fus_driving_systems import driving_system, tus_protocol
from fus_driving_systems.sonic_concepts import sonic_concepts_ds  # or fus_driving_systems.igt.igt_ds

ds_info = driving_system.DrivingSystem()
ds_info.set_ds_info('YOUR-SYSTEM-ID')
ds_info.connect_info = 'COM5'  # the COM port/IP this system is actually connected to

ds = sonic_concepts_ds.SonicConcepts()
ds.connect(ds_info.connect_info)

protocol = tus_protocol.TUSProtocol(ds_info.serial)
protocol.driving_sys.connect_info = ds_info.connect_info
protocol.add_slot('YOUR-TRANSDUCER-ID', 'Focus wrt exit plane [mm]', 40,
                  'Global power [mW]', 2.5)
protocol.configure_timing(pulse_dur=10, pulse_rep_int=50)

try:
    ds.send_protocol(protocol)
    ds.execute_protocol(protocol)  # call again with a new/adjusted protocol whenever needed
finally:
    ds.disconnect()  # always, so an abruptly stopped script doesn't leave it firing
```

If your own script already has its own logging set up, don't call `initialize_logger()` too (it
would reconfigure logging globally); call `sync_logger(your_own_logger)` instead, from
`fus_driving_systems.config.logging_config`, so FDS's own log messages go through your existing
logger rather than setting up a second, separate one.

### Activate your virtual environment and launch the IDE at once
To simplify the process of activating the virtual environment and launching your IDE, you can use the provided [batch script](../start_venv_and_ide.bat).

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

[← Back to README](../README.md)
