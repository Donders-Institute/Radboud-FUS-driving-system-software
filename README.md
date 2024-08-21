# Radboud FUS driving system software
<a name="readme-top"></a>

<div align="center">
  <img src="/images/Radboud-logo.jpg" alt="ru_logo" width="auto"  height="100" />

  <img src="/images/fuslogo.png" alt="fus_logo" width="auto" height="100">
  
</div>

<!-- TABLE OF CONTENTS -->

# 📗 Table of Contents

- [📖 About the Project](#about-project)
  - [👥 Authors](#authors)
- [💻 Getting Started](#getting-started)
  - [Setup](#setup)
  - [Install](#install)
  - [Usage](#usage)
  
<!-- PROJECT DESCRIPTION -->

# 📖 Radboud FUS driving system software <a name="about-project"></a>

(Project id: **0003496** )

The **Radboud FUS driving system software** is an application designed to facilitate the seamless integration of new FUS equipment. It allows for equipment control without the need to learn new software interfaces. 

The current version provides basic functionality that can be easily integrated into your experimental code to drive the system during your experiments. We welcome feedback, suggestions, and bug reporst; please submit them under 'Issues' in this repository. 

This project is facilitated by the Radboud Focused Ultrasound Initiative. For more information, please visit the [website](https://www.ru.nl/en/donders-institute/research/research-facilities/focused-ultrasound-initiative-fus).

<!-- AUTHORS -->

## 👥 Authors <a name="authors"></a>

👤 **[Margely Cornelissen](https://www.ru.nl/en/people/cornelissen-m), [FUS Initiative](https://www.ru.nl/en/donders-institute/research/research-facilities/focused-ultrasound-initiative-fus), Radboud University**

- GitHub: [@MaCuinea](https://github.com/MaCuinea)
- LinkedIn: [LinkedIn](https://linkedin.com/in/margely-cornelissen)

<p align="right">(<a href="#readme-top">back to top</a>)</p>

<!-- GETTING STARTED -->

## 💻 Getting Started <a name="getting-started"></a>

To get a local copy up and running, follow these steps.

### Setup

Clone this repository to your desired folder:

- Git terminal

	``` sh
		cd my-folder
		git clone git@gitlab.socsci.ru.nl:fus-initiative/fus-driving-system-software.git
	```

- GitHub Desktop
	1. Click on 'Current repository'.
	2. Click on 'Add' and select 'Clone repository...'.
	3. Choose 'URL' and paste the following repository URL: https://gitlab.socsci.ru.nl/fus-initiative/fus-driving-system-software
	4. Choose your desired folder and clone the repository.

### Install

1. Install the 'fus_driving_systems' package in a location where you plan to implement the driving system software, such as your virtual environment.

2. Open your command prompt and, optionally, activate your virtual environment. 

	```
	cd your_directory_with_cloned_repository/fus_ds_package
	pip install .
	```

### Usage

With the fus_driving_systems package installed, your environment is now ready to create and execute sequences. The Python scripts provided in the 'standalone_driving_system_software' directory serve as examples of how to create and execute a sequence with a driving system from a specific manufacturer.

Follow the instructions within the code to understand how to integrate it into your own codebase. Additionally, these scripts can be utilized to explore the functionality of the package before integrating it into your project.
<p align="right">(<a href="#readme-top">back to top</a>)</p>
