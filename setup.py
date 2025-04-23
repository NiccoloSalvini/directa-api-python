from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="directa-api",
    version="0.1.0",
    author="Your Name",
    author_email="your.email@example.com",
    description="Python wrapper for Directa Trading API",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/directa-api-python",
    packages=find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Financial and Insurance Industry",
        "Topic :: Office/Business :: Financial :: Investment",
    ],
    python_requires=">=3.7",
    install_requires=[],
    keywords="finance, trading, api, directa, stocks, investing",
) 