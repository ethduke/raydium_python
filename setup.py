from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

with open("requirements.txt", "r", encoding="utf-8") as f:
    requirements = f.read().splitlines()

setup(
    name="raydium-api",
    version="0.1.0",
    author="Maksim",
    author_email="your.email@example.com",
    description="A Python client for interacting with Raydium DEX on Solana",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/raydium-api",
    packages=find_packages(include=["model", "model.*", "utils", "utils.*"]),
    include_package_data=True,
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
    python_requires=">=3.8",
    install_requires=requirements,
    entry_points={
        "console_scripts": [
            "raydium-api=model.raydium_v4:cli_entrypoint",
        ],
    },
) 