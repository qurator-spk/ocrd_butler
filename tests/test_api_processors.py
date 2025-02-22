# -*- coding: utf-8 -*-

"""Testing the processor api for `ocrd_butler` package."""

from flask_testing import TestCase

from ocrd_butler.config import TestingConfig
from ocrd_butler.factory import create_app


class ApiTests(TestCase):
    """Test our api."""

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def create_app(self):
        return create_app(config=TestingConfig)

    def test_get_processors(self):
        """Check if our processors are getable."""
        response = self.client.get("/api/processors")
        assert response.status_code == 200
        assert response.json[0]["executable"] == "ocrd-olena-binarize"
        assert response.json[5]["package"]["git_url"] == "https://github.com/OCR-D/ocrd_tesserocr"
