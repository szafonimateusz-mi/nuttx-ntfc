# NTFC Documentation configuration file

import os
import sys

sys.path.insert(0, os.path.abspath("../src"))

# -- Project information -----------------------------------------------------

project = "NTFC"
copyright = "2024, NTFC authors"
author = "NTFC community"
version = release = "0.0.1"

# -- General configuration ---------------------------------------------------

extensions = [
    "sphinx_rtd_theme",
    "myst_parser",
    "sphinx.ext.autosectionlabel",
    "sphinx.ext.todo",
    "sphinx.ext.autodoc",
    "sphinx.ext.autosummary",
    "sphinx.ext.viewcode",
    "sphinx_copybutton",
    "sphinx_design",
]

source_suffix = [".rst", ".md"]

todo_include_todos = True

autosectionlabel_prefix_document = True

highlight_language = "none"
primary_domain = None

templates_path = ["_templates"]

exclude_patterns = ["_build", "Thumbs.db", ".DS_Store", "venv"]

# -- Options for HTML output -------------------------------------------------

html_theme = "sphinx_rtd_theme"

html_show_sphinx = False

html_theme_options = {"navigation_depth": 5}

html_static_path = ["_static"]

html_show_license = True

today_fmt = "%d %B %y at %H:%M"

# -- Options for autodoc -----------------------------------------------------

autodoc_member_order = "bysource"
autodoc_typehints = "description"
autodoc_typehints_format = "short"

autodoc_default_options = {
    "members": True,
    "undoc-members": True,
    "private-members": False,
    "special-members": "__init__",
    "inherited-members": True,
    "show-inheritance": True,
    "exclude-members": "to_bytes,from_bytes",
}
