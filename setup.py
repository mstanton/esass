"""
Setup configuration for ESASS prototype.
"""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="esass-prototype",
    version="0.1.0",
    author="ESASS Project",
    description="Emergent Self-Adaptive Skill System - Prototype",
    long_description=long_description,
    long_description_content_type="text/markdown",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Libraries :: AI",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    python_requires=">=3.8",
    install_requires=[
        "click>=8.0",
        "python-dateutil>=2.8",
    ],
    entry_points={
        "console_scripts": [
            "esass=esass_prototype.cli:esass",
        ],
    },
)
