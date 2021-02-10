# -*- coding: utf-8 -*-

"""
Extract predefined processors information.
"""

import copy

from flask import jsonify
from flask_restx import Resource

from ocrd_butler.api.restx import api
from ocrd_butler.util import logger
from ocrd_butler import config as ocrd_config


log = logger(__name__)

processors_namespace = api.namespace(
    "processors",
    description="Get the processors known by our butler.")

PROCESSORS_CONFIG = {
    package: {
        "package": {"name": package},
        **ocrd_config.processor_specs(package)
    }
    for package in ocrd_config.PROCESSORS
}

PROCESSOR_NAMES = PROCESSORS_CONFIG.keys()

# We prepare usable action configurations from the config itself.
PROCESSORS_ACTION = copy.deepcopy(PROCESSORS_CONFIG)
for processor in ['ocrd-olena-binarize', 'ocrd-sbb-binarize']:
    PROCESSORS_ACTION.get(
        processor, {}
    )['output_file_grp'] = ['OCR-D-IMG-BINPAGE']

for name, config in PROCESSORS_ACTION.items():

    if "package" in config:
        del config["package"]

    parameters = {}
    if "parameters" in config:
        for p_name, p_values in config["parameters"].items():
            if "default" in p_values:
                parameters[p_name] = p_values["default"]
    config["parameters"] = parameters

    # Just take the first in-/output file group for now.
    # TODO: This is also connected to the choosen paramters.
    for key in ["input_file_grp", "output_file_grp"]:
        config[key] = ''.join(config.get(key, []))


PROCESSORS_VIEW = []
for name, config in PROCESSORS_CONFIG.items():
    PROCESSORS_VIEW.append(
        {
            "name": name,
            **copy.deepcopy(config),
        }
    )


@processors_namespace.route("")
class Processors(Resource):
    """Shows the processor configuration."""

    def get(self):
        """Returns the processor informations as JSON data."""
        return jsonify(PROCESSORS_VIEW)
