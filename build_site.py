#!/usr/bin/env python3

"""
Script for building a static CLLD site.

This script can be used both locally and for various integration services,
including Netlify.

There is no command-line argument parsing, at least for the time being, as
the entire configuration is supposed to take place through JSON files.

Upon deployment, previous files are not deleted: success in new generation
and deployment should be checked by the user from the script return codes.
"""

# TODO: copy image files if exists, etc.
# TODO: build essential latex template
# TODO: allow different templates (including latex? should be a list?)

# Import Python standard libraries
import logging
from pathlib import Path

# Import functions from the `staticcldf` directory; in the future, this will
# be turned into an actual Python library/package
import staticcldf


def main():
    """
    Entry point for the script.
    """

    # Obtain `base_path` for file manipulation
    base_path = Path(__file__).parent.resolve()

    # Load JSON configuration and replaces, and include paths in the first
    config, replaces = staticcldf.load_config(base_path)
    config["base_path"] = base_path
    config["output_path"] = base_path / config["output_path"]

    # Read CLDF data
    cldf_data = staticcldf.read_cldf_data(config)

    # Build site
    staticcldf.render_html(cldf_data, replaces, config)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
