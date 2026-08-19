# Third-Party Notices

This repository is copyright Radboud University (see `LICENSE`), except for the files listed
below, which are additionally copyright Image Guided Therapy (IGT). They are included here
under the same MIT license as the rest of the repository.

**Provided by IGT and used as-is (unmodified):**
- `fus_ds_package/fus_driving_systems/igt/unifus.pyd` -- compiled Python extension module
  provided by IGT for communicating with their driving systems.
- `fus_ds_package/fus_driving_systems/igt/config/gen_*.json` and
  `fus_ds_package/fus_driving_systems/igt/config/deprecated/gen_*.json` -- generator
  configuration files.
- `fus_ds_package/fus_driving_systems/igt/config/imasonic_transducers/*.ini` -- transducer steer
  files.

(Calibration curve-fit data under `igt/config/conversion_data/` was acquired by Radboud
University itself.)

**Originally written by IGT, since modified by Radboud University:**
- `fus_ds_package/fus_driving_systems/igt/transducer_xyz.py` -- originally written by Frederic
  Salabartan (IGT); see the file's own header for details.
- `fus_ds_package/fus_driving_systems/igt/utils.py`
