import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="cannula",
    version="0.0.1",
    author="Robert Myers",
    author_email="robert@julython.org",
    description="Async GraphQL Helper Library",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/rmyers/cannula",
    packages=setuptools.find_packages(exclude=["tests"]),
    install_requires=['graphql-core-next'],
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
)
