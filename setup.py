"""Setup configuration for DocuCheck package."""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as f:
    long_description = f.read()

setup(
    name="docucheck",
    version="1.0.0",
    author="Aryash",
    description="Automated document fact-checking tool using AI",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/aryash45/docucheck",
    packages=find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9+",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.9",
    install_requires=[
        "google-generativeai",
        "python-dotenv",
        "PyMuPDF",
    ],
    entry_points={
        "console_scripts": [
            "docucheck=docucheck.__main__:main",
        ],
    },
)
