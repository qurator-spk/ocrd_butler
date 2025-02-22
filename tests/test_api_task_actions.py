# -*- coding: utf-8 -*-

"""Testing the api for `ocrd_butler` package."""

import pytest
import os
import responses
import shutil
from unittest import mock

from flask_restx import fields
from flask_testing import TestCase

from ocrd_butler.config import TestingConfig
from ocrd_butler.factory import create_app, db
from ocrd_butler.api.models import task_model


CURRENT_DIR = os.path.dirname(__file__)


@pytest.fixture(scope='session')
def celery_config():
    return {
        'broker_url': 'amqp://',
        'result_backend': 'redis://'
    }

@pytest.fixture(scope='session')
def celery_enable_logging():
    return True

@pytest.fixture(scope='session')
def celery_includes():
    return [
        'ocrd_butler.execution.tasks',
        # 'proj.tests.celery_signal_handlers',
    ]


# https://medium.com/@scythargon/how-to-use-celery-pytest-fixtures-for-celery-intergration-testing-6d61c91775d9
# # @pytest.mark.usefixtures("config")
# @pytest.mark.usefixtures('celery_session_app')
# @pytest.mark.usefixtures('celery_session_worker')
class ApiTests(TestCase):
    """Test our api actions."""

    def setUp(self):

        from ocrd_butler import celery
        celery.conf.task_always_eager = True

        db.create_all()

        testfiles = os.path.join(os.path.dirname(
            os.path.abspath(__file__)), "files")
        with open("{0}/sbb-mets-PPN821929127.xml".format(testfiles), "r") as tfh:
            responses.add(responses.GET, "http://foo.bar/mets.xml",
                          body=tfh.read(), status=200)
            tfh.close()
        with open("{0}/00000001.jpg".format(testfiles), "rb") as tfh:
            responses.add(
                responses.GET,
                "http://content.staatsbibliothek-berlin.de/dms/"
                "PPN821929127/800/0/00000001.jpg",
                body=tfh.read(), status=200, content_type="image/jpg")
            tfh.close()
        with open("{0}/00000002.jpg".format(testfiles), "rb") as tfh:
            responses.add(
                responses.GET,
                "http://content.staatsbibliothek-berlin.de/dms/"
                "PPN821929127/800/0/00000002.jpg",
                body=tfh.read(), status=200, content_type="image/jpg")
            tfh.close()
        with open("{0}/00000003.jpg".format(testfiles), "rb") as tfh:
            responses.add(
                responses.GET,
                "http://content.staatsbibliothek-berlin.de/dms/"
                "PPN821929127/800/0/00000003.jpg",
                body=tfh.read(), status=200, content_type="image/jpg")
            tfh.close()

    def tearDown(self):
        """Remove the test database."""
        db.session.remove()
        db.drop_all()
        # self.clearTestDir()

    def clearTestDir(self, config):
        config = TestingConfig()
        test_dirs = glob.glob("%s/*" % config.OCRD_BUTLER_RESULTS)
        for test_dir in test_dirs:
            shutil.rmtree(test_dir, ignore_errors=True)

    def create_app(self):
        return create_app(config=TestingConfig)

    def t_chain(self):
        response = self.client.post("/api/chains", json=dict(
            name="T Chain",
            description="Some foobar chain.",
            processors=[
                "ocrd-tesserocr-segment-region",
                "ocrd-tesserocr-segment-line",
                "ocrd-tesserocr-segment-word",
                "ocrd-tesserocr-recognize",
            ],
            parameters={
                "ocrd-tesserocr-recognize": {
                    "model": "deu"
                }
            }
        ))
        return response.json["id"]

    @mock.patch("ocrd_butler.execution.tasks.run_task")
    @responses.activate
    def test_task_tesserocr(self, mock_run_task):
        """Check if a new task is created."""
        response = self.client.post("/api/tasks", json=dict(
            chain_id=self.t_chain(),
            src="http://foo.bar/mets.xml",
            description="Tesserocr task."
        ))

        response = self.client.post("/api/tasks/1/run")
        assert response.status_code == 200
        assert response.json["status"] == "SUCCESS"

        response = self.client.get("/api/tasks/1/status")
        assert response.json["status"] == "SUCCESS"

        response = self.client.get("/api/tasks/1/results")
        ocr_results = os.path.join(response.json["result_dir"],
                                   "OCR-D-OCR-TESS")
        result_files = os.listdir(ocr_results)
        with open(os.path.join(ocr_results, result_files[2])) as result_file:
            text = result_file.read()
            assert "<pc:Unicode>пропуск\nдля нeмецких" in text

    @mock.patch("ocrd_butler.execution.tasks.run_task")
    @responses.activate
    def test_task_tess_cal(self, mock_run_task):
        """Check if a new task is created."""
        chain_response = self.client.post("/api/chains", json=dict(
            name="TC Chain",
            description="Chain with tesseract and calamari recog.",
            processors=[
                "ocrd-tesserocr-segment-region",
                "ocrd-tesserocr-segment-line",
                "ocrd-tesserocr-segment-word",
                "ocrd-calamari-recognize"
            ]
        ))

        task_response = self.client.post("/api/tasks", json=dict(
            chain_id=chain_response.json["id"],
            src="http://foo.bar/mets.xml",
            description="Tesserocr calamari task.",
            parameters={
                "ocrd-calamari-recognize": {
                    "checkpoint": "{0}/calamari_models/*ckpt.json".format(
                        CURRENT_DIR)
                }
            }
        ))

        response = self.client.post("/api/tasks/{0}/run".format(
            task_response.json["id"]))
        assert response.status_code == 200
        assert response.json["status"] == "SUCCESS"

        response = self.client.get("/api/tasks/{0}/results".format(
            task_response.json["id"]))

        ocr_results = os.path.join(response.json["result_dir"],
                                   "OCR-D-OCR-CALAMARI")
        result_files = os.listdir(ocr_results)
        with open(os.path.join(ocr_results, result_files[2])) as result_file:
            text = result_file.read()
            assert "<pc:Unicode>der klauptstaalt lortgethrt.</pc:Unicode>" in text

    @mock.patch("ocrd_butler.execution.tasks.run_task")
    @responses.activate
    def test_task_ole_cal(self, mock_run_task):
        """Currently using /opt/calamari_models/fraktur_historical/0.ckpt.json
           as checkpoint file.
        """
        chain_response = self.client.post("/api/chains", json=dict(
            name="TC Chain",
            description="Chain with olena binarization, tesseract segmentation"
                        " and calamari recog.",
            processors=[
                "ocrd-olena-binarize",
                "ocrd-tesserocr-segment-region",
                "ocrd-tesserocr-segment-line",
                "ocrd-calamari-recognize"
            ],
            parameters={
                "ocrd-olena-binarize": {
                    "impl": "sauvola-ms-split"
                }
            }
        ))

        task_response = self.client.post("/api/tasks", json=dict(
            chain_id=chain_response.json["id"],
            src="http://foo.bar/mets.xml",
            description="Olena calamari task.",
            parameters={
                "ocrd-olena-binarize": {
                    "impl": "sauvola-ms-split"
                },
                "ocrd-calamari-recognize": {
                    "checkpoint": "{0}/calamari_models/*ckpt.json".format(
                        CURRENT_DIR)
                }
            }
        ))

        response = self.client.post("/api/tasks/{0}/run".format(
            task_response.json["id"]))
        assert response.status_code == 200
        assert response.json["status"] == "SUCCESS"

        response = self.client.get("/api/tasks/{0}/results".format(
            task_response.json["id"]))

        ocr_results = os.path.join(response.json["result_dir"],
                                   "OCR-D-OCR-CALAMARI")
        result_files = os.listdir(ocr_results)
        with open(os.path.join(ocr_results, result_files[2])) as result_file:
            text = result_file.read()
            assert "<pc:Unicode>für deutsehe Soldaten und</pc:Unicode>" in text
