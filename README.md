<a name="readme-top"></a>

<div align="center">
  <img src="/images/donders_logo.svg" alt="donders_logo" width="auto" height="70">
  <img src="/images/logo_FUS_CENTRE.png" alt="fus_centre_logo" width="auto" height="70">
  <br>
  <img src="/images/igtlogo.jpeg" alt="igt_logo" width="auto" height="70">
  <img src="/images/Radboud-logo.jpg" alt="ru_logo" width="auto" height="70" />
</div>

# Radboud FUS Driving System Software

(Project id: **0003496**)

The **Radboud FUS Driving System Software** is designed to streamline the integration of focused ultrasound equipment into your workflow, either via a standalone GUI or directly from your own Python scripts. It enables control of the equipment while limiting the need for users to familiarize themselves with new software interfaces. 

This project is facilitated by the Radboud FUS Centre. For more information, please visit the [website](https://www.ru.nl/en/donders-institute/research/research-facilities/focused-ultrasound-initiative-fus).

> **⚠️ Development status:** This repository is currently under active development and is provided AS IS. Features may be incomplete, undergo significant changes, or contain bugs. Use at your own discretion.
>
> **Note:** Both the GUI and the Python package are developed specifically for Windows. While they might work elsewhere with modifications, full support is only provided for Windows.

## 🚀 Key Features <a name="features"></a>
- **GUI, no coding required**: Build, load, and run protocols through a standalone Windows application (Planning and Executing tabs), for anyone who doesn't want to write scripts. See [Download the GUI](#gui) below for details.
- **Seamless Integration**: Control the equipment directly from your own Python scripts, with a small, explicit API that drops into your existing experimental code. See [Integrating into an Existing Experimental Script](docs/building-protocols.md#integrating) below for details.
- **Compatibility**: This package is also a prerequisite for the latest version of the [SonoRover software](https://github.com/Donders-Institute/Radboud-FUS-measurement-kit), which utilizes it to communicate with your focused ultrasound equipment. By adhering to a standardized communication structure, the characterization software does not need to directly handle communication protocols. Instead, it uses the same codebase across standalone, experimental, and embedded settings alike, ensuring consistent and centralized updates to equipment communication.

<!-- TABLE OF CONTENTS -->

# 📗 Table of Contents

- [👥 Authors](#authors)
- [✒️ How to Cite](#how-to-cite)
- [💻 Getting Started](#getting-started)
  - [🖱️ Download the GUI](#gui)
  - [🐍 Install and Run the Python Package](docs/python-usage.md)
    - [🔧 Installation](docs/python-usage.md#install)
    - [📋 Usage](docs/python-usage.md#usage)
    - [🌟 Installation of New Release](docs/python-usage.md#install-new-release)
  - [🔊 Building and Loading Protocols](docs/building-protocols.md)
    - [🔗 Integrating into an Existing Experimental Script](docs/building-protocols.md#integrating)
- [🧰 Configuration](docs/configuration.md#config)
  - [⚙️ Configuring System Parameters](docs/configuration.md#other-config)
  - [📻 Adding Your Own Equipment](docs/adding-equipment.md)
- [🔭 Future Features](#future-features)
- [🤝 Contributing](#contributing)
- [📝 License](#license)

<!-- AUTHORS -->

## 👥 Authors <a name="authors"></a>

| Name | Affiliation | Links |
|---|---|---|
| [Margely Cornelissen](https://www.ru.nl/en/people/cornelissen-m) | [FUS Centre](https://www.ru.nl/en/donders-institute/research/research-facilities/focused-ultrasound-initiative-fus), Radboud University | [GitHub](https://github.com/MaCuinea) &#183; [LinkedIn](https://linkedin.com/in/margely-cornelissen) &#183; [ORCID](https://orcid.org/0009-0002-1330-4401) |
| Stein Fekkes | [FUS Centre](https://www.ru.nl/en/donders-institute/research/research-facilities/focused-ultrasound-initiative-fus), Radboud University | [GitHub](https://github.com/StefFek-GIT) &#183; [LinkedIn](https://linkedin.com/in/sfekkes) &#183; [ORCID](https://orcid.org/0000-0002-9955-0795) |
| Erik Dumont | [Image Guided Therapy (IGT)](http://www.imageguidedtherapy.com/) | [GitHub](https://github.com/erikdumontigt) &#183; [LinkedIn](https://linkedin.com/in/erik-dumont-986a814) &#183; [ORCID](https://orcid.org/0000-0003-1002-8667) |
| [Lennart Verhagen](https://www.ru.nl/en/people/verhagen-l) | [FUS Centre](https://www.ru.nl/en/donders-institute/research/research-facilities/focused-ultrasound-initiative-fus), Radboud University | [GitHub](https://github.com/lennartverhagen) &#183; [LinkedIn](https://nl.linkedin.com/in/lennartverhagen) &#183; [ORCID](https://orcid.org/0000-0003-3207-7929) |

<p align="right">(<a href="#readme-top">back to top</a>)</p>

## ✒️ How to Cite <a name="how-to-cite"></a>

If you use this package in your research or project, please cite it as follows (see also [`CITATION.cff`](CITATION.cff)):

```
Cornelissen, M., Fekkes, S., Dumont, E., & Verhagen, L. (2024–2026). Radboud FUS Driving System Software (version 2.2.3) [Computer software]. https://github.com/Donders-Institute/Radboud-FUS-driving-system-software
```

If you used a different version than the one currently listed above, replace the version number with the one you actually used (see the [releases page](https://github.com/Donders-Institute/Radboud-FUS-driving-system-software/releases) for the full list). There is no DOI for this software yet; the repository URL above is the citable reference in the meantime.

<p align="right">(<a href="#readme-top">back to top</a>)</p>

<!-- GETTING STARTED -->

# 💻 Getting Started <a name="getting-started"></a>

There are two ways to use this software: through the standalone GUI (no Python needed), or
directly from your own Python scripts.

## 🖱️ Download the GUI <a name="gui"></a>

A standalone Windows application for building, loading, and running protocols through a GUI
(Planning and Executing tabs), for anyone who doesn't want to write their own scripts.

**Option 1: Download the ready-to-use executable (recommended for most users)**

1. Visit the [Latest Release](https://github.com/Donders-Institute/Radboud-FUS-driving-system-software/releases/latest).
2. Download `FDS_GUI-*-windows.zip`.
3. Extract it anywhere, then double-click `FDS_GUI.exe` inside the extracted folder.

To launch it from your desktop instead of digging into the extracted folder each time,
right-click `FDS_GUI.exe` and choose "Send to > Desktop (create shortcut)". Don't move or copy
the `.exe` on its own; it needs the `_internal` folder
that sits next to it.

<details>
<summary><b>Option 2: Build it yourself</b></summary>

Useful if you're developing the GUI itself, or want a build from an unreleased commit. Clone this
repository (see [Step 1 under Installation](docs/python-usage.md#install) for other ways to get a
copy, e.g. GitHub Desktop or a source zip):
```
git clone git@github.com:Donders-Institute/Radboud-FUS-driving-system-software.git
cd Radboud-FUS-driving-system-software
```
Then, from its root, activate a virtual environment (see [Step 3 under
Installation](docs/python-usage.md#install) if you don't have one yet):
```
call [VENV_PATH]\Scripts\activate
```
The two `pip install` commands below only resolve correctly from the repository root, not from
inside `fus_ds_gui/`:
```
pip install -r fus_ds_gui/requirements-gui.txt
pip install -r fus_ds_gui/requirements-build.txt
cd fus_ds_gui
pyinstaller fus_ds_gui.spec --noconfirm
```
The build appears in `fus_ds_gui/dist/FDS_GUI/` (run `FDS_GUI.exe` inside it).

</details>

### Configuring the GUI or installing a new release

The GUI reads the same `ds_config.ini` as the Python package (see
[Configuration](docs/configuration.md#config)): inside the extracted
`FDS_GUI-*-windows.zip`, it lives at `_internal/fus_driving_systems/config/ds_config.ini`, next
to `FDS_GUI.exe`, and can be hand-edited directly. It's still a **generated file** though, so any
edit is lost the moment you install a new release; keep a copy of your override if you rely on
one long-term.

Installing a new release is the same three steps as Option 1 above: download the new
`FDS_GUI-*-windows.zip`, extract it into a fresh folder, and use `FDS_GUI.exe` from there. If you
kept a copy of a hand-edited `ds_config.ini` (see above), reapply it to the new folder; there's
nothing else to migrate.

## 🐍 Install and Run the Python Package

Want to use `fus_driving_systems` from your own Python scripts instead, e.g. embedded in an existing experiment script alongside stimulus presentation or triggering code? See **[docs/python-usage.md](docs/python-usage.md)** for cloning the repository, setting up a virtual environment (or integrating into one you already have), and running the example scripts. Upgrading to a new release is also covered there.

<p align="right">(<a href="#readme-top">back to top</a>)</p>

<!-- CONFIGURATION -->

# 🧰 Configuration

Customizing safety limits or logging behavior? See **[docs/configuration.md](docs/configuration.md)**.

## 📻 Adding Your Own Equipment

Want to add support for a new driving system or transducer? See
**[docs/adding-equipment.md](docs/adding-equipment.md)** for the full step-by-step guide,
including 3D (lateral) steering and a safety note on calibration data.

<p align="right">(<a href="#readme-top">back to top</a>)</p>

<!-- FUTURE FEATURES -->

# 🔭 Future Features <a name="future-features"></a>

- [ ] Generic conversion equations for a broader range of driving systems, instead of always
  targeting amplitude (power) and mid bowl (focus) specifically (see the "Current limitation"
  note in [Adding Your Own Equipment](docs/adding-equipment.md#add-equip))
- [ ] 3D calibration curve support for `can_3d_steer` transducers (see "3D (lateral) steering" in
  [Adding Your Own Equipment](docs/adding-equipment.md#add-equip)); the calibration data format
  for this isn't decided yet
- [ ] Embed the [TUS Calculator](https://www.itrusst.com/tus-calculator) directly in the GUI for
  visualizing timing parameters, instead of only linking out to it

<p align="right">(<a href="#readme-top">back to top</a>)</p>

<!-- CONTRIBUTING -->

# 🤝 Contributing <a name="contributing"></a>

Contributions, issues, and feature requests are welcome!

Feel free to check the [issues page](issues/).

If you have any questions, please feel free to reach out to us via email at fus@ru.nl.
We'd love to hear from you.

<p align="right">(<a href="#readme-top">back to top</a>)</p>

# 📝 License <a name="license"></a>

This project is [MIT](./LICENSE) licensed.

<p align="right">(<a href="#readme-top">back to top</a>)</p>
