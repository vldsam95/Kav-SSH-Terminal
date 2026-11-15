# Third-party notices

This file documents dependencies and palettes used or conservatively credited by Kav SSH Terminal. Original project code is licensed under MIT (see LICENSE); that license does not replace third-party terms. No affiliation or endorsement is implied.

## Python dependencies

The versions below were observed in the local environment on 2026-11-15. Project requirements use minimum versions, so fresh installs can resolve differently. This is not a lockfile or an exhaustive binary-release inventory. See third_party_licenses/inventory.json for source links and copied license paths.

| Package | Observed version | Upstream license metadata |
| --- | --- | --- |
| annotated-types | 0.8.0 | MIT |
| asyncssh | 2.24.1 | EPL-2.0 OR GPL-2.0-or-later |
| cffi | 2.1.1 | MIT-0 |
| cryptography | 50.0.2 | Apache-2.0 OR BSD-3-Clause |
| jaraco.classes | 3.4.0 | MIT License |
| jaraco.context | 6.1.2 | MIT |
| jaraco.functools | 4.6.0 | MIT |
| keyring | 25.7.0 | MIT |
| more-itertools | 11.2.1 | MIT |
| platformdirs | 4.14.5 | MIT |
| pycparser | 3.12 | BSD-3-Clause |
| pydantic | 2.14.3 | MIT |
| pydantic_core | 2.50.4 | MIT |
| PySide6_Essentials | 6.12.0 | LGPL-3.0-only OR GPL-2.0-only OR GPL-3.0-only |
| pyte | 0.8.2 | GNU Lesser General Public License v3 (LGPLv3) |
| python-bidi | 0.6.12 | GNU Library or Lesser General Public License (LGPL) |
| pywin32-ctypes | 0.2.3 | BSD-3-Clause |
| shiboken6 | 6.12.0 | LGPL-3.0-only OR GPL-2.0-only OR GPL-3.0-only |
| typing-inspection | 0.4.5 | MIT |
| typing_extensions | 4.16.0 | PSF-2.0 |
| wcwidth | 0.9.4 | MIT License |

License and notice files available in installed distribution metadata have been preserved under third_party_licenses/dependencies/. Some packages include further third-party components. Consult their complete sources and notices before redistributing binaries.

### LGPL components

PySide6_Essentials and shiboken6 offer LGPL-3.0-only / GPL alternatives according to the installed metadata. The LGPL route is documented here; no commercial Qt license is claimed. pyte and python-bidi also contain LGPLv3 terms. Copies of LGPLv3 and GPLv3 are in third_party_licenses/common/. These generic texts do not replace package-specific copyright and bundled-component notices. Qt documentation: https://doc.qt.io/qtforpython-6/licenses.html and https://www.qt.io/development/open-source-lgpl-obligations.

Using these dependencies through their APIs does not by itself relicense all original Kav SSH Terminal code. If libraries or a ready-to-run environment are redistributed, comply with their applicable notice, corresponding-source and replacement/relinking requirements. Modified library code must retain its applicable license.

### AsyncSSH

AsyncSSH 2.24.1 states EPL-2.0 OR GPL-2.0-or-later. Its EPL license text is preserved under third_party_licenses/dependencies/asyncssh/. See https://asyncssh.readthedocs.io/en/latest/#license and https://www.eclipse.org/legal/epl-2.0/faq/. Preserve its notices and meet source-availability requirements when redistributing the library.

## Theme palettes

Palette attribution is based on matching names and color values, not verified development history. It does not assert that upstream implementation code was copied.

| Palette | Credit / upstream | Terms and local reference |
| --- | --- | --- |
| Solarized Dark | Ethan Schoonover — https://github.com/altercation/solarized | MIT; third_party_licenses/palettes/Solarized-LICENSE.txt |
| Dracula | Dracula Theme; terminal port credited to Zeno Rocha — https://github.com/dracula/dracula-theme and https://github.com/dracula/terminal-app | MIT; Dracula-LICENSE.txt and Dracula-terminal-LICENSE.txt in third_party_licenses/palettes/ |
| Nord | Sven Greb — https://github.com/nordtheme/nord | MIT; third_party_licenses/palettes/Nord-LICENSE.txt |
| Gruvbox Dark | morhetz — https://github.com/morhetz/gruvbox | Upstream README declares MIT/X11; preserved in third_party_licenses/palettes/Gruvbox-upstream-README.md |
| ANSI palette overlap with Snazzy | Sindre Sorhus — https://github.com/sindresorhus/iterm2-snazzy | MIT; third_party_licenses/palettes/Snazzy-LICENSE.txt |

The ANSI color table in src/terminal/style.py shares several values with Snazzy and historical Dracula variants. Both are conservatively acknowledged; exact provenance cannot be established from this folder.

Gruvbox upstream declares MIT/X11 in its README but no standalone license file was retrieved. Its declaration is preserved rather than inventing a copyright year or attributing a license from an unrelated fork. The common MIT permission text below is included as a reference to the license named upstream, not presented as a verbatim Gruvbox notice. Credit remains with morhetz and the upstream contributors.

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

## Names, fonts and comparisons

PuTTY Classic and PowerShell are descriptive preset names; Electerm and xterm.js appear as comparisons in documentation. These mentions do not claim affiliation or establish use of those projects' source code. Font family names refer to fonts installed on the user's system; no font files were found in the project source. If fonts, icons or other assets are bundled later, review their licenses separately.

## Build and executable distribution

PyInstaller is a build dependency with a GPL exception for generated applications: https://pyinstaller.org/en/stable/license.html. Its exception does not waive the licenses of libraries packaged into the executable.

This notice bundle prepares source sharing; it does not certify a bundled executable. Before publishing binaries, inventory the actual build (including Qt plugins, cryptography/OpenSSL and Rust dependencies), preserve all applicable notices, provide corresponding source by a valid license-compliant mechanism, and verify replacement/relinking rights where required. Update this document and the notice bundle when dependencies or assets change.
