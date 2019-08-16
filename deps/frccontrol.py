#!/usr/bin/env python3

import multiprocessing as mp
import os
import subprocess
import sys

sys.path.insert(0, os.getcwd())
from deputils import fetch_git_dependency


# Create venv
if not os.path.exists("build/venv"):
    subprocess.run([sys.executable, "-m", "venv", "build/venv"])

# venv executables
root = os.getcwd()
ENV_PYTHON = os.path.join(root, "build/venv/bin/python3")
ENV_PIP = os.path.join(root, "build/venv/bin/pip3")


def run(name):
    subprocess.run([ENV_PYTHON, name, "--noninteractive"])
    base = os.path.splitext(os.path.basename(name))[0]
    for suffix in [
        "pzmap_open-loop",
        "pzmap_closed-loop",
        "pzmap_observer",
        "response",
    ]:
        subprocess.run(
            [
                "inkscape",
                "-D",
                "-z",
                "--file=" + base + "_" + suffix + ".svg",
                "--export-pdf=" + base + "_" + suffix + ".pdf",
            ]
        )


# Set up control (dep of frccontrol)
os.chdir(root)
fetch_git_dependency(
    repo="git://github.com/python-control/python-control",
    commit="129a05364aa94e35b9ea02f81292d555f27e2b69",
)
os.chdir("build/python-control")
subprocess.run([ENV_PIP, "install", "-e", "."])
os.chdir(root)

# Set up slycot (for control.StateSpace.zero())
fetch_git_dependency(
    repo="git://github.com/python-control/slycot",
    commit="2f31897759d2f7fa9909fecdefc73abfa5a5917e",
)
os.chdir("build/slycot")
subprocess.run([ENV_PIP, "install", "-e", "."])
os.chdir(root)

# Set up frccontrol
fetch_git_dependency(
    repo="git://github.com/calcmogul/frccontrol",
    commit="7fa04016bf0d7d587cc9b8c81058c9aafc71c4fa",
)
os.chdir("build/frccontrol")
subprocess.run([ENV_PIP, "install", "-e", "."])
os.chdir(root)

# Run frccontrol examples
os.chdir("build/frccontrol/examples")
files = [
    os.path.join(dp, f) for dp, dn, fn in os.walk(".") for f in fn if f.endswith(".py")
]
with mp.Pool(mp.cpu_count()) as pool:
    pool.map(run, files)
