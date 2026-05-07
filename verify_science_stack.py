"""Verify the third-party scientific computing stack for the contest repo."""

from __future__ import annotations

import importlib


PACKAGES = [
    ("numpy", "numpy"),
    ("scipy", "scipy"),
    ("pandas", "pandas"),
    ("matplotlib", "matplotlib"),
    ("seaborn", "seaborn"),
    ("scikit-learn", "sklearn"),
    ("statsmodels", "statsmodels"),
    ("sympy", "sympy"),
    ("networkx", "networkx"),
    ("openpyxl", "openpyxl"),
    ("jupyterlab", "jupyterlab"),
    ("notebook", "notebook"),
]


def main() -> None:
    missing: list[str] = []

    print("Scientific computing stack check")
    print("-" * 40)

    for display_name, import_name in PACKAGES:
        try:
            module = importlib.import_module(import_name)
        except ModuleNotFoundError:
            missing.append(display_name)
            print(f"[missing] {display_name}")
            continue

        version = getattr(module, "__version__", "version unknown")
        print(f"[ok]      {display_name}: {version}")

    print("-" * 40)
    if missing:
        package_list = ", ".join(missing)
        raise SystemExit(f"Missing packages: {package_list}")

    print("All scientific computing packages are available.")


if __name__ == "__main__":
    main()
