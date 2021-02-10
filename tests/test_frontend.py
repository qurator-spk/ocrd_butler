# -*- coding: utf-8 -*-
"""
Testing the frontend of `ocrd_butler` package.
"""

import json
import os
from unittest import mock
from flask_testing import TestCase

import responses
from requests_html import HTML

from ocrd_butler.config import TestingConfig
from ocrd_butler.factory import (
    create_app,
    db
)
from ocrd_butler.database.models import Task as db_model_Task


class FrontendTests(TestCase):
    """Test our frontend."""

    def setUp(self):
        db.create_all()

        def create_api_task_callback(request):
            db_task = db_model_Task(
                uid="id",
                src="mets_url",
                default_file_grp="file_grp",
                worker_task_id="worker_task.id",
                chain_id="chain.id",
                parameters="")
            db.session.add(db_task)
            db.session.commit()
            headers = {}
            # "message": "Task created."
            return (201, headers, json.dumps({"task_id": 1, "created": True}))

        def delete_api_task_callback(request):
            db_model_Task.query.filter_by(id=1).delete()
            db.session.commit()
            return (200, {}, json.dumps({"task_id": 1, "deleted": True}))

        responses.add_callback(
            responses.POST, "http://localhost/api/tasks",
            callback=create_api_task_callback)

        responses.add(responses.GET, "http://foo.bar/mets.xml",
                      body="<xml>foo</xml>", status=200)

        responses.add_callback(
            responses.DELETE, "http://localhost/api/tasks/1",
            callback=delete_api_task_callback)

        def api_get_taskinfo_callback(request):
            return (200, {}, json.dumps({
                "task_id": 1,
                "state": "PENDING",
                "result": None,
            }))

        responses.add_callback(
            responses.GET, "http://localhost:5555/api/task/info/worker_task.id",
            callback=api_get_taskinfo_callback)

    def tearDown(self):
        db.session.remove()
        db.drop_all()

    def create_app(self):
        return create_app(config=TestingConfig)

    def test_task_page(self):
        """Check if tasks page is visible."""
        response = self.client.get("/tasks")
        self.assert200(response)
        self.assert_template_used("tasks.html")
        html = HTML(html=response.data)
        assert len(html.find('table > tr > th')) == 10
        assert len(html.find('table > tr > td')) == 0

    def get_chain_id(self):
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
        return chain_response.json["id"]

    @responses.activate
    def test_create_task(self):
        """Check if task will be created."""
        self.client.post("/new-task", data=dict(
            task_id="foobar",
            description="barfoo",
            src="http://foo.bar/mets.xml",
            chain_id=self.get_chain_id()
        ))

        response = self.client.get("/tasks")
        html = HTML(html=response.data)
        assert len(html.find('table > tr > td')) == 10
        assert html.find('table > tr > td')[6].text == "worker_task.id"
        self.client.get("/task/delete/1")

    @responses.activate
    def test_delete_task(self):
        """Check if task will be deleted."""

        self.client.post("/new-task", data=dict(
            task_id="foobar-del",
            description="barfoo",
            src="http://foo.bar/mets.xml",
            chain_id=self.get_chain_id()
        ))

        response = self.client.get("/tasks")
        html = HTML(html=response.data)
        assert len(html.find('table > tr > td')) == 10

        delete_link = html.find('table > tr > td > a.delete-task')[0].attrs["href"]
        assert delete_link == "/task/delete/1"
        response = self.client.get(delete_link)
        assert response.status == '302 FOUND'
        assert response.status_code == 302

        response = self.client.get("/tasks")
        html = HTML(html=response.data)
        assert len(html.find('table > tr > td')) == 0

    @mock.patch('flask_sqlalchemy._QueryProperty.__get__')
    @mock.patch("ocrd_butler.frontend.tasks.task_information")
    def test_frontend_download_txt(self, mock_task_information, mock_fs):
        """Check if download txt is working."""
        mock_task_information.return_value = {
            "ready": True,
            "result": {
                "result_dir": "{0}/files/ocr_result_01".format(os.path.dirname(__file__)),
                "task_id": 23
            }
        }
        mock_fs\
            .return_value.filter_by\
            .return_value.first\
            .return_value = type('', (object,), {
                "chain_id": 1,
                "processors": ["ocrd-calamari-recognize"]
            })()

        response = self.client.get("/download/txt/foobar")

        assert response.status_code == 200
        assert response.content_type == "text/txt; charset=utf-8"
        assert b"nen eer gbaun nonenronrndannn" in response.data
