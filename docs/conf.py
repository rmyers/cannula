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
    "sphinx.ext.autosummary",
    "sphinx.ext.napoleon",
    "sphinx_autodoc_typehints",
    "sphinxarg.ext",
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

html_static_path = ["_static"]
html_css_files = ["custom.css"]

html_context = {
    "github_user": "rmyers",
    "github_repo": "cannula",
    "github_version": "main",
    "doc_path": "docs",
}

html_theme_options = {
    "collapse_navigation": False,
    "external_links": [
        {
            "name": "GraphQL-Codegen",
            "url": "https://the-guild.dev/graphql/codegen",
        },
    ],
    "footer_start": ["copyright"],
    "footer_center": ["sphinx-version"],
    "logo": {
        "text": "Cannula Documentation",
        "image_light": "_static/mind-map.png",
        "image_dark": "_static/mind-map.png",
    },
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
    "navigation_depth": 2,
    "primary_sidebar_end": ["sidebar-ethical-ads.html"],
    "show_nav_level": 2,
    "show_toc_level": 1,
    "sidebar_includehidden": False,
    "sidebarwidth": 200,
    "use_edit_page_button": True,
}
