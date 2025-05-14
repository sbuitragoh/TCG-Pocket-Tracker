import sys
import os

def resource_path(relative_path):
    """Get absolute path to resource, works for dev, PyInstaller, and external folders."""
    # First, try the current working directory (for non-bundled folders)
    path = os.path.join(os.getcwd(), relative_path)
    if os.path.exists(path):
        return path
    # Fallback to PyInstaller _MEIPASS (for bundled resources)
    base_path = getattr(sys, '_MEIPASS', os.path.abspath("."))
    return os.path.join(base_path, relative_path)