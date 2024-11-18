# Configuration file for the Sphinx documentation builder.
#
# This file only contains a selection of the most common options. For a full
# list see the documentation:
# http://www.sphinx-doc.org/en/master/config

# -- Path setup --------------------------------------------------------------

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#
import os
import sys

sys.path.insert(0, os.path.abspath(".."))

import cannula

# -- Project information -----------------------------------------------------

project = "Cannula"
copyright = "2024, Robert Myers"
author = "Robert Myers"

# The full version, including alpha/beta/rc tags
release = cannula.__VERSION__


# -- General configuration ---------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
    "sphinx_autodoc_typehints",
]

# Add any paths that contain templates here, relative to this directory.
templates_path = ["_templates"]

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store", "**/node_modules", "**/venv"]

source_suffix = [".rst"]

suppress_warnings = ["misc.highlighting_failure"]

# Typehints
always_use_bars_union = True
always_document_param_types = True
typehints_defaults = "braces"
autodoc_typehints = "description"

# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#
html_theme = "pydata_sphinx_theme"

html_theme_options = {
    "logo": {
        "text": "Cannula Documentation",
        "image_light": "_static/mind-map.png",
        "image_dark": "_static/mind-map.png",
    },
    "primary_sidebar_end": ["indices.html", "sidebar-ethical-ads.html"],
    "external_links": [
        {
            "name": "GraphQL-Codegen",
            "url": "https://the-guild.dev/graphql/codegen",
        },
    ],
    "icon_links": [
        {
            "name": "GitHub",
            "url": "https://github.com/rmyers/cannula",
            "icon": "fa-brands fa-github",
            "type": "fontawesome",
        },
        {
            "name": "PyPI",
            "url": "https://pypi.org/project/cannula/",
            "icon": "fa-brands fa-python",
            "type": "fontawesome",
        },
    ],
}
