#!/usr/bin/env python3
"""Copy the public ODE Explorer runtime from a local course repository checkout."""
from pathlib import Path
import argparse
import shutil

RUNTIME = ('index.html', 'style.css', 'engine.js', 'examples.js', 'app.js', 'solver-worker.js')
ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('course_checkout', type=Path)
    args = parser.parse_args()
    source = args.course_checkout.resolve()
    for name in RUNTIME:
        if not (source / 'simulator' / name).is_file():
            parser.error(f'Missing source file: simulator/{name}')
    if not (source / 'LICENSE').is_file():
        parser.error('The course repository LICENSE is required.')
    destination = ROOT / 'ode-explorer'
    destination.mkdir(exist_ok=True)
    for name in RUNTIME:
        shutil.copyfile(source / 'simulator' / name, destination / name)
    shutil.copyfile(source / 'LICENSE', destination / 'LICENSE')
    (destination / 'README.md').write_text('''# ODE Explorer

[Open the applet](https://thomaswoolley.co.uk/ode-explorer/) · [Embedded website page](https://thomaswoolley.co.uk/ode-explorer.html)

Interactive autonomous 1D and 2D ODE simulator, with phase plots, nullclines, parameter sliders, equilibrium eigenvalues and linked time solutions. Thirteen examples and blank user-defined models are included. PNG and CSV exports are available.

The [full user guide and canonical source](https://github.com/ThomasEWoolley/Modelling_with_Differential_Equations/tree/main/simulator) explain the controls, equation syntax, examples, numerical methods, limitations and embedding.

This directory is the GitHub Pages deployment copy. Update it with `python3 scripts/sync_ode_explorer.py /path/to/Modelling_with_Differential_Equations`, then run the site checks. Keep the six runtime files together. The application is distributed under the included MIT licence.
''', encoding='utf-8')
    print(f'Synchronised {len(RUNTIME)} runtime files and the licence to {destination}.')


if __name__ == '__main__':
    main()
