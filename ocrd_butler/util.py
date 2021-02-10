# -*- coding: utf-8 -*-

"""Utils module."""

import os
import json
import re
import logging.config

logging_conf_path = os.path.normpath(os.path.join(
    os.path.dirname(__file__), '../logging.conf'))
logging.config.fileConfig(logging_conf_path)
log = logging.getLogger(__name__)


def camel_case_split(identifier):
    """CamelCase split"""
    matches = re.finditer(
        ".+?(?:(?<=[a-z])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])|$)",
        identifier)
    return [m.group(0) for m in matches]


def host_url(request):
    return request.host_url
    # return "http://localhost:5000/"


def to_json(data):
    if isinstance(data, str):
        data = data.replace("'", '"')
        data = json.loads(data)
    return data
