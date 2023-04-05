from setuptools import setup, find_packages

setup(
    name="noizu-help",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "openai",
    ],
    entry_points={
        "console_scripts": [
            "noizu-help = noizu_help.bin.noizu_help:main",
        ],
    },
    author="Keith Brings",
    author_email="keith.brings@noizu.com",
    description="A simple script to interact with GPT and execute shell commands",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers - Sandbox/Dev Setup",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3.10",
    ],
)
