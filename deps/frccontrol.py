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
    subprocess.run([ENV_PYTHON, name, "--save-plots", "--noninteractive"])
    base = os.path.splitext(os.path.basename(name))[0]
    for suffix in ["pzmaps", "response"]:
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

# Set up frccontrol
fetch_git_dependency(
    repo="git://github.com/calcmogul/frccontrol",
    commit="2762add026e1f7018e9731edef97ee3d7ac3fa9d",
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
