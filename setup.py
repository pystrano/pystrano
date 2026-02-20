from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="pystrano",
    version="1.2.0",
    description="A Python package for managing deploying Django applications (like Capistrano for Ruby)",
    long_description=long_description,
    long_description_content_type="text/markdown",
    license="MIT",
    classifiers=[
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.12",
        "Programming Language :: Python :: 3.14",
    ],
    keywords=["pystrano"],
    packages=find_packages(),
    python_requires=">=3.12",
    install_requires=[
        "fabric>=3.2.2,<4.0",
        "click>=8.3.1,<9.0",
        "pyyaml>=6.0.3,<7.0",
        "python-dotenv>=1.2.1,<2.0",
    ],
    entry_points={
        "console_scripts": [
            "pystrano=pystrano.deploy:main",
        ],
    },
    url="https://github.com/lexpank/pystrano",
    project_urls={
        "Homepage": "https://github.com/lexpank/pystrano",
        "Issues": "https://github.com/lexpank/pystrano/issues",
    },
)
