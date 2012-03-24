import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

project = 'configdb'
version = '0.1'
language = 'en'
master_doc = 'index'
exclude_patterns = []
extensions = ['sphinx.ext.autodoc']

html_theme = 'minimal-hyde'
html_theme_path = ['/usr/share/sphinx/themes', '.']

html_show_sourcelink = False
html_show_sphinx = False
html_show_copyright = False

