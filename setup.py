from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="pystrano",
    version="2.0.0",
    description="Capistrano-inspired deployment automation for Django and FastAPI apps.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    license="MIT",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Environment :: Console",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: POSIX :: Linux",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3.12",
        "Topic :: Software Development :: Build Tools",
        "Topic :: System :: Systems Administration",
    ],
    keywords=[
        "pystrano",
        "deployment",
        "deploy",
        "django",
        "fastapi",
        "cli",
        "yaml",
        "capistrano",
        "ssh",
        "gunicorn",
        "systemd",
    ],
    packages=find_packages(),
    python_requires=">=3.12",
    install_requires=[
        "fabric>=3.2.3,<4.0",
        "click>=8.4.1,<9.0",
        "pyyaml>=6.0.3,<7.0",
        "python-dotenv>=1.2.2,<2.0",
    ],
    entry_points={
        "console_scripts": [
            "pystrano=pystrano.deploy:main",
        ],
    },
    url="https://pystrano.com",
    project_urls={
        "Homepage": "https://pystrano.com",
        "Documentation": "https://pystrano.com/docs",
        "Source": "https://github.com/lexpank/pystrano",
        "Issues": "https://github.com/lexpank/pystrano/issues",
    },
)
