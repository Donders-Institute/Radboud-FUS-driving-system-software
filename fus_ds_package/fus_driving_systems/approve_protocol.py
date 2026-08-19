# -*- coding: utf-8 -*-
"""
Copyright (c) 2024 Radboud University

SPDX-License-Identifier: MIT
See the LICENSE file for full license text.

If you use this kit in your research or project, please cite it -- see CITATION.cff or the
'How to Cite' section of README.md at
https://github.com/Donders-Institute/Radboud-FUS-driving-system-software.
"""

# Approves a protocol YAML file for load_protocol()'s optional hash-protection mechanism --
# computes its current SHA-256 hash and writes it to a sidecar <path>.sha256 file, so
# load_protocol() will detect any future edit to the file.
#
# Usage: python -m fus_driving_systems.approve_protocol path/to/protocol.yaml

import sys

from fus_driving_systems.protocol_loader import approve_protocol

if __name__ == '__main__':
    if len(sys.argv) != 2:
        sys.exit('Usage: python -m fus_driving_systems.approve_protocol <path/to/protocol.yaml>')
    approve_protocol(sys.argv[1])
