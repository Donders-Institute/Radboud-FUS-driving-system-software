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
  - [Features](#features)
  - [Important note](#important_note)
  - [👥 Authors](#authors)
  - [✒️ How to cite](#how-to-cite)
- [💻 Getting Started](#getting-started)
  - [Installation](#install)
  - [Usage](#usage)
- [🌟 Installation of new release](#install-new-release)
- [🔭 Future Features](#future-features)
- [🤝 Contributing](#contributing)
- [📝 License](#license)
  
<!-- PROJECT DESCRIPTION -->

# 📖 Radboud FUS driving system software <a name="about-project"></a>

(Project id: **0003496** )

The **Radboud FUS driving system software** is designed to streamline the integration of new focused ultrasound equipment into your workflow. It enables control of the equipment while limiting the need for users to familiarize themselves with new software interfaces. 

## Features <a name="features"></a>
- **Seamless Integration**: The current version offers essential functionality that can be easily integrated into your experimental code to control the system during your experiments.
- **Compatibility**: This package is also a prerequisite for the latest version of the [SonoRover One software](https://github.com/Donders-Institute/Radboud-FUS-measurement-kit), which utilizes it to communicate with your focused ultrasound equipment. 
By adhering to a standardized communication structure, the characterization software does not need to directly handle communication protocols. Instead, it uses the same codebase for both standalone and experimental settings, ensuring consistent and centralized updates to equipment communication.

This project is facilitated by the Radboud Focused Ultrasound Initiative. For more information, please visit the [website](https://www.ru.nl/en/donders-institute/research/research-facilities/focused-ultrasound-initiative-fus).

## Important Note <a name="important_note"></a>

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

Margely Cornelissen, Stein Fekkes (Radboud University, Nijmegen, The Netherlands) & Erik Dumont (Image Guided Therapy, Pessac, France) (2024), Radboud FUS driving system software (version 1.0)

<!-- GETTING STARTED -->

# 💻 Getting Started <a name="getting-started"></a>

To get a local copy up and running, follow these steps.

## Installation <a name="install"></a>

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

## Usage <a name="usage"></a>

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
