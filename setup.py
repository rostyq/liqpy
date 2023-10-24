from setuptools import setup
from tomllib import load


with open("pyproject.toml", "rb") as f:
    project = load(f)["project"]

    setup(
        name=project["name"],
        version=project["version"],
        description=project["description"],
        keywords=project["keywords"],
        author=project["authors"][0]["name"],
        author_email=project["authors"][0]["email"],
        url=project["urls"]["Homepage"],
        packages=[project["name"]],
        install_requires=project["dependencies"],
        python_requires=">=3.11",
    )
