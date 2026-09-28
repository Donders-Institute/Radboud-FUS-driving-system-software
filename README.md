# Radboud FUS driving system software
<a name="readme-top"></a>

<div align="center">
  <img src="/images/donders_logo.svg" alt="donders_logo" width="auto" height="70">
  <img src="/images/logo_FUS_CENTRE.png" alt="fus_centre_logo" width="auto" height="70">
  <br>
  <img src="/images/igtlogo.jpeg" alt="igt_logo" width="auto" height="70">
  <img src="/images/Radboud-logo.jpg" alt="ru_logo" width="auto" height="70" />
</div>

> 🖥️ **Just want to use the GUI?** No Python or installation needed: download the ready-to-run
> Windows application from the [Latest Release](https://github.com/Donders-Institute/Radboud-FUS-driving-system-software/releases/latest)
> (look for `FDS_GUI-*-windows.zip`), extract it, and double-click `FDS_GUI.exe`. See
> [Download the GUI](#gui) below for details.

<!-- TABLE OF CONTENTS -->

# 📗 Table of Contents

- [📖 About the Project](#about-project)
  - [🚀 Key Features](#features)
  - [👥 Authors](#authors)
  - [✒️ How to cite](#how-to-cite)
- [💻 Getting Started](docs/installation.md#getting-started)
  - [🔧 Installation](docs/installation.md#install)
  - [📋 Usage](docs/installation.md#usage)
- [🖥️ Download the GUI](#gui)
- [🌟 Installation of new release](docs/installation.md#install-new-release)
- [🧰 Configuration](docs/configuration.md#config)
  - [⚙️ Configuring System Parameters](docs/configuration.md#other-config)
- [📻 Adding Your Own Equipment](docs/adding-equipment.md#add-equip)
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
- [GitHub](https://github.com/MaCuinea) (@MaCuinea)
- [LinkedIn](https://linkedin.com/in/margely-cornelissen)
- [ORCID](https://orcid.org/0009-0002-1330-4401)

👤 **[Stein Fekkes](https://www.ru.nl/en/people/fekkes-s), [FUS Centre](https://www.ru.nl/en/donders-institute/research/research-facilities/focused-ultrasound-initiative-fus), Radboud University**

- [GitHub](https://github.com/StefFek-GIT) (@StefFek-GIT)
- [LinkedIn](https://linkedin.com/in/sfekkes)
- [ORCID](https://orcid.org/0000-0002-9955-0795)

👤 **Erik Dumont, [Image Guided Therapy (IGT)](http://www.imageguidedtherapy.com/)**
- [GitHub](https://github.com/erikdumontigt) (@erikdumontigt)
- [LinkedIn](https://linkedin.com/in/erik-dumont-986a814)
- [ORCID](https://orcid.org/0000-0003-1002-8667)

👤 **Lennart Verhagen, [FUS Centre](https://www.ru.nl/en/donders-institute/research/research-facilities/focused-ultrasound-initiative-fus), Radboud University**
- [GitHub](https://github.com/lennartverhagen) (@lennartverhagen)
- [LinkedIn](https://nl.linkedin.com/in/lennartverhagen)
- [ORCID](https://orcid.org/0000-0003-3207-7929)

<p align="right">(<a href="#readme-top">back to top</a>)</p>

## ✒️ How to cite <a name="how-to-cite"></a>

If you use this package in your research or project, please cite it as follows (see also [`CITATION.cff`](CITATION.cff)):

Cornelissen, M., Fekkes, S., Dumont, E., & Verhagen, L. (2024–2026). Radboud FUS Driving System Software (version 2.2.3) [Computer software]. https://github.com/Donders-Institute/Radboud-FUS-driving-system-software

If you used a different version than the one currently listed above, replace the version number with the one you actually used (see the [releases page](https://github.com/Donders-Institute/Radboud-FUS-driving-system-software/releases) for the full list), since reproducing a result later needs to know exactly which version produced it. There is no DOI for this software yet; the repository URL above is the citable reference in the meantime.

<p align="right">(<a href="#readme-top">back to top</a>)</p>

<!-- GETTING STARTED -->

# 💻 Getting Started

Want to use `fus_driving_systems` from your own Python scripts? See **[docs/installation.md](docs/installation.md)** for cloning the repository, setting up a virtual environment (or integrating into one you already have), and running the example scripts. Upgrading to a new release is also covered there.

<!-- GUI -->

# 🖥️ Download the GUI <a name="gui"></a>

A standalone Windows application for building, loading, and running protocols through a GUI
(Planning and Executing tabs), for anyone who doesn't want to write their own scripts.

## Option 1: Download the ready-to-use executable (recommended for most users)

1. Visit the [Latest Release](https://github.com/Donders-Institute/Radboud-FUS-driving-system-software/releases/latest).
2. Download `FDS_GUI-*-windows.zip`.
3. Extract it anywhere, then double-click `FDS_GUI.exe` inside the extracted folder.

No Python installation is required for this. To launch it from your desktop instead of digging
into the extracted folder each time, right-click `FDS_GUI.exe` and choose "Send to > Desktop
(create shortcut)". Don't move or copy the `.exe` on its own; it needs the `_internal` folder
that sits next to it.

## Option 2: Build it yourself

Useful if you're developing the GUI itself, or want a build from an unreleased commit. From the
root of a cloned repository (see "Step 1" under [Installation](docs/installation.md#install) above;
the two `pip install` commands below only resolve correctly from there, not from inside
`fus_ds_gui/`), with your virtual environment active:
```
pip install -r fus_ds_gui/requirements-gui.txt
pip install -r fus_ds_gui/requirements-build.txt
cd fus_ds_gui
pyinstaller fus_ds_gui.spec --noconfirm
```
The build appears in `fus_ds_gui/dist/FDS_GUI/` (run `FDS_GUI.exe` inside it).

<p align="right">(<a href="#readme-top">back to top</a>)</p>

<!-- CONFIGURATION -->

# 🧰 Configuration

Customizing equipment, safety limits, or logging behavior? See
**[docs/configuration.md](docs/configuration.md)**.

# 📻 Adding Your Own Equipment

Want to add support for a new driving system or transducer? See
**[docs/adding-equipment.md](docs/adding-equipment.md)** for the full step-by-step guide,
including 3D (lateral) steering and a safety note on calibration data.

<p align="right">(<a href="#readme-top">back to top</a>)</p>

<!-- FUTURE FEATURES -->

# 🔭 Future Features <a name="future-features"></a>

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
