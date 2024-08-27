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
  - [Setup](#setup)
  - [Install](#install)
  - [Usage](#usage)
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

## Setup <a name="setup"></a>

Clone this repository to your desired folder:

- Git terminal

	``` sh
	cd my-folder
	git clone ggit@github.com:Donders-Institute/Radboud-FUS-driving-system-software.git
	```
	
- GitHub Desktop
	1. Click on 'Current repository'.
	2. Click on 'Add' and select 'Clone repository...'.
	3. Choose 'URL' and paste the following repository URL: [https://github.com/Donders-Institute/Radboud-FUS-driving-system-software.git](https://github.com/Donders-Institute/Radboud-FUS-driving-system-software.git)
	4. Choose your desired folder and clone the repository.

## Install <a name="install"></a>

Open your command prompt and run the following batch file to set up the virtual environment and install the necessary dependencies. You can use input parameters to customize the environment name or Python interpreter location.

```
cd your_directory_with_cloned_repository
install_dependencies.bat [VENV_NAME] [PYTHON_INTERPRETER_PATH]
```
	
- VENV_NAME: Specify the name for the virtual environment (e.g., MyEnv). If not provided, it defaults to FUS_DS_PACKAGE.
- PYTHON_INTERPRETER_PATH: Specify the path to the Python 3.10 interpreter if it’s not in the default location. For example, C:\Path\To\Python310\python.exe.

The batch file will:

- Create a virtual environment.
- Install the required Python packages.
- Set up necessary environment variables.

After running the batch file, ensure that the virtual environment is activated and dependencies are installed. You can verify this by:

- Checking for the virtual environment in your WORKON_HOME directory.
- Confirming that the required packages are installed.

### Notes
- **Python Version**: The script assumes that Python 3.10 is installed. If you have a different version, make sure to adjust the script accordingly or install Python 3.10.
- **Environment Variables**: The batch file sets environment variables temporarily for the session and permanently if they are not already set. Ensure that WORKON_HOME is correctly configured as needed.

### Troubleshooting
If you encounter issues with the batch file not being recognized or errors during execution, ensure that:

- The batch file has the correct permissions to execute.
- The repository has been cloned correctly and contains the necessary files.

## Usage <a name="usage"></a>

With the fus_driving_systems package installed, activate your environment in your command prompt to create and execute sequences. 

```
workon [VENV_NAME]
```

While the virtual environment is activated, you can install Spyder or any other IDE of your choice. To install Spyder, run:

```
pip install spyder
```

After installing Spyder, you can launch it directly from the command line within the activated virtual environment by running:

```
spyder
```

Open one of the Python scripts provided in the 'standalone_driving_system_software' directory, which serve as examples of how to create and execute a sequence with a driving system from a specific manufacturer.

Follow the instructions within the code to understand how to integrate it into your own codebase. Additionally, these scripts can be utilized to explore the functionality of the package before integrating it into your project.

### Activate your virtual environment and launch the IDE at once
To simplify the process of activating the virtual environment and launching your IDE, you can use the provided [batch script](start_venv_and_ide.bat).

How to use the script:
1. Ensure that start_env_and_ide.bat is located in a convenient location, such as the root directory of your project or your desktop.
2. Run the script in one of the following ways:
	- Open start_venv_and_ide.bat in a text editor and modify the VENV_NAME and IDE variables directly if you prefer not to use command-line arguments. To run the .bat file, just double-click it.
	- Using the command prompt:
		```
		start_venv_and_ide.bat [VENV_NAME] [IDE]
		```
		- VENV_NAME: Specify the name for the virtual environment (e.g., MyEnv). If not provided, it defaults to FUS_DS_PACKAGE.
		- IDE: Specify the python interpreter. IF not provided, it defaults to spyder.

<p align="right">(<a href="#readme-top">back to top</a>)</p>

<!-- FUTURE FEATURES -->

# 🔭 Future Features <a name="future-features"></a>

- [ ] **A GUI to display, plan and execute an US sequence**
- [ ] **Compatibility check of chosen equipment**
- [ ] **Control a driving system with two transducers plugged-in**

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