# Radboud FUS driving system software
<a name="readme-top"></a>

<div align="center">
  <img src="/images/Radboud-logo.jpg" alt="ru_logo" width="auto"  height="70" />

  <img src="/images/fuslogo.png" alt="fus_logo" width="auto" height="70">

  <img src="/images/igtlogo.jpeg" alt="igt_logo" width="auto" height="70">
  
</div>


<!-- TABLE OF CONTENTS -->

# 📗 Table of Contents

- [📖 About the Project](#about-project)
  - [🚀 Features](#features)
  - [⚠️ Important note](#important_note)
  - [👥 Authors](#authors)
  - [✒️ How to cite](#how-to-cite)
- [💻 Getting Started](#getting-started)
  - [🔧 Installation](#install)
  - [📋 Usage](#usage)
- [🧰 Configuration](#config)
  - [📻 How to add your own equipment](#add-equip)
  - [⚙️ Configuring System Parameters](#other-config)
- [🌟 Installation of new release](#install-new-release)
- [🔭 Future Features](#future-features)
- [🤝 Contributing](#contributing)
- [📝 License](#license)
  
<!-- PROJECT DESCRIPTION -->

# 📖 Radboud FUS driving system software <a name="about-project"></a>

(Project id: **0003496** )

The **Radboud FUS driving system software** is designed to streamline the integration of new focused ultrasound equipment into your workflow. It enables control of the equipment while limiting the need for users to familiarize themselves with new software interfaces. 

## 🚀 Features <a name="features"></a>
- **Seamless Integration**: The current version offers essential functionality that can be easily integrated into your experimental code to control the system during your experiments.
- **Compatibility**: This package is also a prerequisite for the latest version of the [SonoRover One software](https://github.com/Donders-Institute/Radboud-FUS-measurement-kit), which utilizes it to communicate with your focused ultrasound equipment. 
By adhering to a standardized communication structure, the characterization software does not need to directly handle communication protocols. Instead, it uses the same codebase for both standalone and experimental settings, ensuring consistent and centralized updates to equipment communication.

This project is facilitated by the Radboud Focused Ultrasound Initiative. For more information, please visit the [website](https://www.ru.nl/en/donders-institute/research/research-facilities/focused-ultrasound-initiative-fus).

## ⚠️ Important Note <a name="important_note"></a>

**This package is developed specifically for Windows operating systems.** While it might work in other environments with some modifications, full support is provided only for Windows.


<!-- AUTHORS -->

## 👥 Authors <a name="authors"></a>

👤 **[Margely Cornelissen](https://www.ru.nl/en/people/cornelissen-m), [FUS Initiative](https://www.ru.nl/en/donders-institute/research/research-facilities/focused-ultrasound-initiative-fus), Radboud University**
- GitHub: [@MaCuinea](https://github.com/MaCuinea)
- [LinkedIn](https://linkedin.com/in/margely-cornelissen)

👤 **Erik Dumont, [Image Guided Therapy (IGT)](http://www.imageguidedtherapy.com/)**
- GitHub: [@erikdumontigt](https://github.com/erikdumontigt)
- [LinkedIn](https://linkedin.com/in/erik-dumont-986a814)

👤 **[Stein Fekkes](https://www.ru.nl/en/people/fekkes-s), [FUS Initiative](https://www.ru.nl/en/donders-institute/research/research-facilities/focused-ultrasound-initiative-fus), Radboud University**

- GitHub: [@StefFek-GIT](https://github.com/StefFek-GIT)
- [LinkedIn](https://linkedin.com/in/sfekkes)

<p align="right">(<a href="#readme-top">back to top</a>)</p>

## ✒️ How to cite <a name="how-to-cite"></a>

If you use this package in your research or project, please cite it as follows:

Margely Cornelissen, Stein Fekkes (Radboud University, Nijmegen, The Netherlands) & Erik Dumont (Image Guided Therapy, Pessac, France) (2024), Radboud FUS driving system software (version 3.0)

<!-- GETTING STARTED -->

# 💻 Getting Started <a name="getting-started"></a>

To get a local copy up and running, follow these steps.

## 🔧 Installation <a name="install"></a>

*Step 1: Clone this repository to your desired folder*
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

*Step 2: Download Python 3.10* \
Ensure you have Python 3.10 installed and accessible from your command line. If Python is not installed, download it from the [official Python website](https://www.python.org/downloads/release/python-31011/). It is not necessary to add Python to your system's PATH during installation, as virtual environments allow you to manage and switch between Python versions without affecting other projects or code outside the environment.

<div align="center">
  <img src="/images/python_path.png" alt="python_path" width="auto"  height="auto" />
</div>


**Note**: The script assumes that Python 3.10 is installed. If you have a different version, make sure to adjust the script accordingly or install Python 3.10.

*Step 3: Create and setup a virtual environment* \
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

*Step 4: Verify the successful setup of the virtual environment* \
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

*Step 1: Activate your environment* \
With the fus_driving_systems package installed, activate your environment in your command prompt to create and execute sequences. 

```
call [VENV_PATH]\Scripts\activate
```

*Step 2: Install an IDE* \
While your virtual environment is activated, you can install any IDE of your choice. Spyder is pre-installed by default. To install another IDE, run:

```
pip install [IDE]
```

*Step 3: Launch the IDE* \
After installing your IDE, you can launch it directly from the command line while the virtual environment is activated. For Spyder, enter:

```
spyder
```

*Step 4: Open the main script* \
Open one of the Python scripts provided in the 'standalone_driving_system_software' directory in the cloned repository, which serve as examples of how to create and execute a sequence with a driving system from a specific manufacturer.

Follow the instructions within the code to understand how to integrate it into your own codebase. Additionally, these scripts can be utilized to explore the functionality of the package before integrating it into your project.

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
		- IDE: Specify the python interpreter. IF not provided, it defaults to spyder.
		
		**DCCN specific configuration**

		To use the DCCN-specific default values, you can soly provide the first input parameter to activate these settings.

		Example:
		```
		start_venv_and_ide.bat "" "" "DCCN"
		```

<p align="right">(<a href="#readme-top">back to top</a>)</p>

# 🌟 Installation of new release <a name="install-new-release"></a>

*(Optional) Step 1: Backup your current installation* \
To avoid losing your custom standalone scripts:
- Create a backup by copying your current installation directory to a safe location.
- Save any custom standalone scripts for reuse.

*Step 2: Clone the repository to your desired folder*
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

*Step 3: Install the new release in your virtual environment*
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

*(Optional) Step 4: Restore your custom standalone scripts*
- If you have custom standalone scripts, copy them to the following location: your_directory_with_cloned_repository\standalone_driving_system_software.
- Review the release notes to check if any modifications are needed for your scripts to remain compatible.

<p align="right">(<a href="#readme-top">back to top</a>)</p>

<!-- CONFIGURATION -->

# 🧰 Configuration <a name="config"></a>

The Radboud FUS Driving System software can be customized through its configuration file to match your specific requirements. This section explains what can be configured and how to properly modify settings.

## Configuration File Overview

The package includes a comprehensive configuration file (`fus_ds_package/fus_driving_systems/config/ds_config.ini`) that controls various aspects of the system. You can either modify this file directly or modify and regenerate it using the provided create_config.py script. Before making any changes:

1. **Create a backup** of the original configuration file
2. Edit the file using a text editor like Notepad++ or VS Code
3. Make your changes while preserving the formatting
4. Save the file with the same name
5. Restart the application for changes to take effect

The configuration file is organized into these main sections:

- **General Settings**: Basic system parameters
- **Logging**: System event recording options
- **Trigger**: Ultrasound pulse triggering configuration
- **Power**: Output power control settings
- **Focus**: Beam focusing parameters
- **Ramp**: Pulse ramping options
- **Timing**: Default timing parameters
- **Equipment**: Hardware component and compatibility settings

## 📻 Adding Your Own Equipment <a name="add-equip"></a>

You can extend the software to support new hardware by following these steps:

### Step 1: Create a New Manufacturer Module
1. Create a new folder within `fus_ds_package/fus_driving_systems/` (e.g., `your_manufacturer_name/`)
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

def send_sequence(self, sequence):
    """
    Translate and send ultrasound sequence to the driving system
    Args:
        sequence: A Sequence object containing, amongst other things, of:
				the ultrasound protocol (focus, pulse duration, pulse rep. interval and etcetera)
                used equipment (driving system and transducer)
    """
    pass

def execute_sequence(self):
    """
    Execute the previously sent sequence
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

1. Create a new script in `standalone_driving_system_software/` (e.g., `standalone_your_manufacturer.py`)
2. Use existing scripts (like `standalone_sonic_concepts.py`) as templates
3. In the first section: Define user input by setting appropriate Sequence parameters. Configure the code according to your specific equipment by adjusting timing parameters, power input levels, and other relevant settings.
4. In the second section: Import your new driving system script and initialize an instance of the class. The invocation of the implemented abstract functions (connect, send_sequence, execute_sequence, disconnect) can remain the same.

To use your new equipment with custom serial numbers for driving systems and transducers, you'll need to update the configuration file. You can either modify the `ds_config.ini` file directly or modify and regenerate it using the provided `create_config.py` script. How and what to modify is explained in the next step.

### Step 4: Update the Configuration File

Update the `ds_config.ini` file to include your new equipment. The Equipment section is extensive and includes settings for:

1. Available driving systems and transducers
2. Manufacturer-specific configurations
3. Specific hardware parameters for each device
4. Compatible combinations of equipment

#### Add to Equipment Section
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
combinations = IGT-128-ch_comb_2x10-ch~IS_PCD15287_01001
	# ...additional combinations...
inactive_combinations = 
```

- **driving systems**: List of available driving system identifiers
- **transducers**: List of available transducer identifiers
- **combination sign**: Symbol used to denote system-transducer combinations
- **combinations**: List of valid equipment combinations. Only needed when conversion equations are required to translate between user-friendly inputs and hardware-specific parameters.
- **inactive_combinations**: Combinations that exist but are disabled. Only needed when conversion equations are required to translate between user-friendly inputs and hardware-specific parameters.

#### Add Manufacturer Settings
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
- **equipment - driving systems**: Available driving systems of this manufacturer, must be listed in the main Equipment section
and/or
- **equipment - transducers**: Available transducers of this manufacturer, must be listed in the main Equipment section

Additional manufacturer-specific settings can be added as needed. For example, the IGT configuration contains more settings related to hardware limits.


#### Add Specific Equipment Settings
```ini
[Equipment.Driving system.YOUR-SYSTEM-ID]
name = Your System Name
manufacturer = Your Manufacturer Name
available channels = 4  # Number of channels
connection info = COM7  # Or other connection info
power options = Global power [mW]
requires conversion equations? = False
transducer compatibility = YOUR-TRANSDUCER-ID
active? = True
```

Default settings for driving systems are:
- **name**: Descriptive name of the system
- **manufacturer**: Must match one of your defined manufacturers
- **available channels**: Number of channels the system provides
- **connection info**: COM port, IP address, or path to configuration file
- **power options**: Power options supported by this which must be chosen from the Power section of the config
- **requires conversion equations?**: (Advanced feature) Set to True if characterization based conversion between user input and system parameters is needed. This is useful when the driving system doesn't allow "pressure in free water" as direct input, but this relationship can be defined during characterization. When enabled, users can, for example, specify pressure in free water as input, and the system will automatically calculate the required hardware-specific input values using the defined conversion equations.
- **transducer compatibility**: List of compatible transducer IDs. This parameter isn't fully implemented yet but will be used in future versions to automatically check compatibility between selected equipment.
- **active?**: Whether this system is active and available for use

```ini
[Equipment.Transducer.YOUR-TRANSDUCER-ID]
name = Your Transducer Name
manufacturer = Your Manufacturer Name
elements = 2
fund. freq. = 250
natural focus = 0
exit plane - first element dist. = 0
min. focus = 0
max. focus = 100
steer information = path\to\steer\info
active? = True
```

Default settings for transducers are:
- **name**: Descriptive name of the transducer
- **manufacturer**: Must match one of your defined manufacturers
- **elements**: Number of elements in the transducer
- **fund. freq.**: Fundamental frequency in kHz
- **natural focus**: Radius of curvature in millimeters
- **exit plane - first element dist.**: Distance between radiating surface and exit plane in millimeters
- **min. focus**: Minimum allowed focus with respect to exit plane in millimeters
- **max. focus**: Maximum allowed focus with respect to exit plane in millimeters
- **steer information**: Path to steering information file if applicable
- **active?**: Whether this transducer is active and available for use

#### Add Equipment Combinations (advanced feature, if needed)
If your system requires conversion equations:

```ini
[Equipment.Combination.YOUR-SYSTEM-ID~YOUR-TRANSDUCER-ID]
driving system serial = YOUR-SYSTEM-ID
transducer serial = YOUR-TRANSDUCER-ID
equalizationcurvefit json file = path\to\equalization\file.json
focuscurvefit json file = path\to\focus\file.json
powercurvefit json file = path\to\power\file.json
voltagecurvefit json file = path\to\voltage\file.json
```

These combinations are only required if additional equations are needed to convert user input (e.g., pressure in free water and focus with respect to exit plane) to input the driving system understands (e.g., amplitude and focus with respect to mid bowl). This is required for combinations like IGT-Imasonic.

The four typical conversion equations are:
- **equalization factor vs focus wrt exit plane**: Adjusts for the decreasing maximum pressure in free water that occurs with increasing focus distance. This compensates for beam attenuation at greater distances.
- **focus wrt mid bowl vs focus wrt exit plane**: Converts between different focus reference points
- **amplitude vs pressure in free water**: Maps desired pressure to system amplitude settings
- **amplitude vs voltage**: Relates amplitude settings to actual voltage levels

These conversion equations allow users to specify parameters in intuitive units (like pressure) while the system handles the conversion to hardware-specific inputs.

### Step 5: Reinstall the Package

After making these changes, reinstall the FUS driving system package to apply your updates. 

Now you are ready to use your new standalone script to drive the new equipment.

## ⚙️ Configuring System Parameters <a name="other-config"></a>

Each configuration section controls different aspects of the system's behavior. Here's an overview of the key parameters you might want to customize:

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

The maximum pressure setting (1.4 MPa by default) serves as a safety limit. Adjust this based on your specific requirements, but exercise caution to maintain safety.


### Trigger, Power, Focus, Ramp and Timing Parameters

The `[Trigger]`, `[Power]`, `[Focus]` and `[Ramp]` sections contain different available and implemented options. When an option is added, the corrensponding structure has to be implemented in the code.

The `[Timing]` section contains default values regarding pulse timing.

## Common Configuration Tasks

Here are some frequently adjusted settings:

- **Change equipment**: Modify `driving systems` and `transducers` in the `[Equipment]` section
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

<p align="right">(<a href="#readme-top">back to top</a>)</p>

<!-- FUTURE FEATURES -->

# 🔭 Future Features <a name="future-features"></a>

- [ ] **A GUI to display, plan and execute an US sequence**
- [ ] **Compatibility check of chosen equipment**
- [x] **Control a driving system with two transducers plugged-in**

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
