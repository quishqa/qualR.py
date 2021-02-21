from setuptools import setup

setup(
    name="qualRpy",
    version="0.9.0",
    description="Download Sao Paulo air quality data",
    author="Mario Gavidia-Calderon",
    author_email="mario.calderon@iag.usp.br",
    packages=["qualRpy"],
    install_requires=["requests", "pandas", "datetime", "beautifulsoup4", "lxml"]
    )
