project = "nsjail-python"
copyright = "2026, nsjail-python contributors"
author = "nsjail-python contributors"
release = "0.1.0"

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
    "sphinx.ext.intersphinx",
]

templates_path = ["_templates"]
exclude_patterns = ["_build", "plans", "superpowers"]

html_theme = "furo"

intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
}
