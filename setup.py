from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="perplexity-local",
    version="0.1.0",
    author="Sarvajeethuk",
    description="A local web search and AI response generation tool",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/sarvajeethuk/perplexity-local",
    packages=find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.9",
    install_requires=[
        "requests",
        "beautifulsoup4",
        "duckduckgo-search",
        "youtube-transcript-api",
    ],
    entry_points={
        "console_scripts": [
            "perplexity-local=perplexity_local.main:main",
        ],
    },
)