from setuptools import setup, find_packages

setup(
    name="pystrano",
    version="0.1.0",
    description="A Python package for managing deploying Django applications (like Capistrano for Ruby)",
    url="https://github.com/lexpank/pystrano",
    packages=find_packages(),
    install_requires=[
        "fabric>=3.2.2",
        "click>=8.1.7",
        "pyyaml>=6.0.2",
        "python-dotenv>=1.0.1",
    ],
    python_requires=">=3.6",
    entry_points={
        "console_scripts": [
            "pystrano=pystrano.deploy:main",
            "pystrano-setup=pystrano.deploy:setup",
        ]
    }
)