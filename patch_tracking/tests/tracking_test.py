# -*- coding:utf-8 -*-
"""
Automated testing of the Tracking interface, including POST requests and GET requests
"""
import unittest
import json
from base64 import b64encode
from werkzeug.security import generate_password_hash
from patch_tracking.app import app
from patch_tracking.database import reset_db
from patch_tracking.api.business import create_tracking
from patch_tracking.api.constant import ResponseCode


class TestTracking(unittest.TestCase):
    """
    Automated testing of the Tracking interface, including POST requests and GET requests
    """
    def setUp(self):
        """
        Prepare the environment
        :return:
        """
        self.client = app.test_client()
        reset_db.reset()
        app.config["USER"] = "hello"
        app.config["PASSWORD"] = generate_password_hash("world")

        credentials = b64encode(b"hello:world").decode('utf-8')
        self.auth = {"Authorization": f"Basic {credentials}"}

    def test_none_data(self):
        """
        In the absence of data, the GET interface queries all the data
        :return:
        """
        with app.app_context():

            resp = self.client.get("/tracking")

            resp_dict = json.loads(resp.data)

            self.assertIn("code", resp_dict, msg="Error in data format return")
            self.assertEqual(ResponseCode.SUCCESS, resp_dict.get("code"), msg="Error in status code return")

            self.assertIn("msg", resp_dict, msg="Error in data format return")
            self.assertEqual(
                ResponseCode.CODE_MSG_MAP.get(ResponseCode.SUCCESS),
                resp_dict.get("msg"),
                msg="Error in status code return"
            )

            self.assertIn("data", resp_dict, msg="Error in data format return")
            self.assertIsNotNone(resp_dict.get("data"), msg="Error in data information return")
            self.assertEqual(resp_dict.get("data"), [], msg="Error in data information return")

    def test_find_nonexistent_data(self):
        """
        The GET interface queries data that does not exist
        :return:
        """
        with app.app_context():

            resp = self.client.get("/tracking?repo=aa&branch=aa")

            resp_dict = json.loads(resp.data)

            self.assertIn("code", resp_dict, msg="Error in data format return")
            self.assertEqual(ResponseCode.SUCCESS, resp_dict.get("code"), msg="Error in status code return")

            self.assertIn("msg", resp_dict, msg="Error in data format return")
            self.assertEqual(
                ResponseCode.CODE_MSG_MAP.get(ResponseCode.SUCCESS),
                resp_dict.get("msg"),
                msg="Error in status code return"
            )

            self.assertIn("data", resp_dict, msg="Error in data format return")
            self.assertIsNotNone(resp_dict.get("data"), msg="Error in data information return")
            self.assertEqual(resp_dict.get("data"), [], msg="Error in data information return")

    def test_insert_data(self):
        """
        The POST interface inserts data
        :return:
        """
        data_github = {
            "version_control": "github",
            "scm_repo": "A",
            "scm_branch": "A",
            "scm_commit": "A",
            "repo": "A",
            "branch": "A",
            "enabled": 0
        }

        data_git = {
            "version_control": "git",
            "scm_repo": "A",
            "scm_branch": "A",
            "scm_commit": "A",
            "repo": "A",
            "branch": "A",
            "enabled": 0
        }

        for data in [data_git, data_github]:
            resp = self.client.post("/tracking", json=data, content_type="application/json", headers=self.auth)
            resp_dict = json.loads(resp.data)
            self.assertIn("code", resp_dict, msg="Error in data format return")
            self.assertEqual(ResponseCode.SUCCESS, resp_dict.get("code"), msg="Error in status code return")

            self.assertIn("msg", resp_dict, msg="Error in data format return")
            self.assertEqual(
                ResponseCode.CODE_MSG_MAP.get(ResponseCode.SUCCESS),
                resp_dict.get("msg"),
                msg="Error in status code return"
            )

            self.assertIn("data", resp_dict, msg="Error in data format return")
            self.assertIsNotNone(resp_dict.get("data"), msg="Error in data information return")

    def test_query_inserted_data(self):
        """
        The GET interface queries existing data
        :return:
        """
        with app.app_context():
            data_github = {
                "version_control": "github",
                "scm_repo": "B",
                "scm_branch": "B",
                "scm_commit": "B",
                "repo": "B1",
                "branch": "B1",
                "enabled": False
            }

            data_git = {
                "version_control": "git",
                "scm_repo": "B",
                "scm_branch": "B",
                "scm_commit": "B",
                "repo": "B2",
                "branch": "B2",
                "enabled": False
            }

            for data_insert in [data_github, data_git]:
                create_tracking(data_insert)

                resp = self.client.get("/tracking?repo={}&branch={}".format(data_insert["repo"], data_insert["branch"]))

                resp_dict = json.loads(resp.data)
                self.assertIn("code", resp_dict, msg="Error in data format return")
                self.assertEqual(ResponseCode.SUCCESS, resp_dict.get("code"), msg="Error in status code return")

                self.assertIn("msg", resp_dict, msg="Error in data format return")
                self.assertEqual(
                    ResponseCode.CODE_MSG_MAP.get(ResponseCode.SUCCESS),
                    resp_dict.get("msg"),
                    msg="Error in status code return"
                )

                self.assertIn("data", resp_dict, msg="Error in data format return")
                self.assertIsNotNone(resp_dict.get("data"), msg="Error in data information return")
                self.assertIn(data_insert, resp_dict.get("data"), msg="Error in data information return")

    def test_fewer_parameters(self):
        """
        When the POST interface passes in parameters, fewer parameters must be passed
        :return:
        """
        data_github = {"version_control": "github", "scm_commit": "AA", "repo": "AA", "branch": "AA", "enabled": 1}
        data_git = {"version_control": "git", "scm_commit": "AA", "repo": "AA", "branch": "AA", "enabled": 1}

        for data in [data_git, data_github]:
            resp = self.client.post("/tracking", json=data, content_type="application/json", headers=self.auth)
            resp_dict = json.loads(resp.data)
            self.assertIn("code", resp_dict, msg="Error in data format return")
            self.assertEqual(
                ResponseCode.INPUT_PARAMETERS_ERROR, resp_dict.get("code"), msg="Error in status code return"
            )

            self.assertIn("msg", resp_dict, msg="Error in data format return")
            self.assertEqual(
                ResponseCode.CODE_MSG_MAP.get(ResponseCode.INPUT_PARAMETERS_ERROR),
                resp_dict.get("msg"),
                msg="Error in status code return"
            )

            self.assertIn("data", resp_dict, msg="Error in data format return")
            self.assertEqual(resp_dict.get("data"), None, msg="Error in data information return")

    def test_error_parameters_value(self):
        """
        The post interface passes in the wrong parameter
        :return:
        """
        data_github = {"version_control": "github", "scm_commit": "AA", "repo": "AA", "branch": "AA", "enabled": "AA"}
        data_git = {"version_control": "git", "scm_commit": "AA", "repo": "AA", "branch": "AA", "enabled": "AA"}

        for data in [data_git, data_github]:
            resp = self.client.post("/tracking", json=data, content_type="application/json", headers=self.auth)
            resp_dict = json.loads(resp.data)
            self.assertIn("code", resp_dict, msg="Error in data format return")
            self.assertEqual(
                ResponseCode.INPUT_PARAMETERS_ERROR, resp_dict.get("code"), msg="Error in status code return"
            )

            self.assertIn("msg", resp_dict, msg="Error in data format return")
            self.assertEqual(
                ResponseCode.CODE_MSG_MAP.get(ResponseCode.INPUT_PARAMETERS_ERROR),
                resp_dict.get("msg"),
                msg="Error in status code return"
            )

            self.assertIn("data", resp_dict, msg="Error in data format return")
            self.assertEqual(resp_dict.get("data"), None, msg="Error in data information return")

    def test_post_error_parameters(self):
        """
        The post interface passes in the wrong parameter
        :return:
        """
        data_github = {"version_control": "github", "scm_commit": "AA", "oper": "AA", "hcnarb": "AA", "enabled": "AA"}
        data_git = {"version_control": "git", "scm_commit": "AA", "oper": "AA", "hcnarb": "AA", "enabled": "AA"}

        for data in [data_git, data_github]:
            resp = self.client.post("/tracking", json=data, content_type="application/json", headers=self.auth)
            resp_dict = json.loads(resp.data)
            self.assertIn("code", resp_dict, msg="Error in data format return")
            self.assertEqual(
                ResponseCode.INPUT_PARAMETERS_ERROR, resp_dict.get("code"), msg="Error in status code return"
            )

            self.assertIn("msg", resp_dict, msg="Error in data format return")
            self.assertEqual(
                ResponseCode.CODE_MSG_MAP.get(ResponseCode.INPUT_PARAMETERS_ERROR),
                resp_dict.get("msg"),
                msg="Error in status code return"
            )

            self.assertIn("data", resp_dict, msg="Error in data format return")
            self.assertEqual(resp_dict.get("data"), None, msg="Error in data information return")

    def test_get_error_parameters(self):
        """
        The get interface passes in the wrong parameter
        :return:
        """
        with app.app_context():
            data_github = {
                "version_control": "github",
                "scm_repo": "BB",
                "scm_branch": "BB",
                "scm_commit": "BB",
                "repo": "BB1",
                "branch": "BB1",
                "enabled": True
            }

            data_git = {
                "version_control": "github",
                "scm_repo": "BB",
                "scm_branch": "BB",
                "scm_commit": "BB",
                "repo": "BB2",
                "branch": "BB2",
                "enabled": True
            }

            for data_insert in [data_github, data_git]:
                create_tracking(data_insert)

                resp = self.client.get("/tracking?oper=B&chcnsrb=B")

                resp_dict = json.loads(resp.data)
                self.assertIn("code", resp_dict, msg="Error in data format return")
                self.assertEqual(
                    ResponseCode.INPUT_PARAMETERS_ERROR, resp_dict.get("code"), msg="Error in status code return"
                )

                self.assertIn("msg", resp_dict, msg="Error in data format return")
                self.assertEqual(
                    ResponseCode.CODE_MSG_MAP.get(ResponseCode.INPUT_PARAMETERS_ERROR),
                    resp_dict.get("msg"),
                    msg="Error in status code return"
                )

                self.assertIn("data", resp_dict, msg="Error in data format return")
                self.assertEqual(resp_dict.get("data"), None, msg="Error in data information return")

    def test_update_data(self):
        """
        update data
        :return:
        """
        with app.app_context():
            data_old_list = [
                {
                    "version_control": "github",
                    "scm_repo": "str",
                    "scm_branch": "str",
                    "scm_commit": "str",
                    "repo": "string",
                    "branch": "string",
                    "enabled": False
                }, {
                    "version_control": "git",
                    "scm_repo": "str",
                    "scm_branch": "str",
                    "scm_commit": "str",
                    "repo": "string",
                    "branch": "string",
                    "enabled": False
                }
            ]
            data_new_list = [
                {
                    "version_control": "github",
                    "scm_repo": "string",
                    "scm_branch": "string",
                    "scm_commit": "string",
                    "repo": "string",
                    "branch": "string",
                    "enabled": False
                }, {
                    "branch": "string",
                    "enabled": True,
                    "repo": "string",
                    "scm_branch": "string",
                    "scm_commit": "string",
                    "scm_repo": "string",
                    "version_control": "git",
                }
            ]

            for data_old, data_new in zip(data_old_list, data_new_list):
                self.client.post("/tracking", json=data_old, content_type="application/json", headers=self.auth)
                self.client.post("/tracking", json=data_new, content_type="application/json")

                resp = self.client.get("/tracking?repo=string&branch=string")

                resp_dict = json.loads(resp.data)
                self.assertIn("code", resp_dict, msg="Error in data format return")
                self.assertEqual(ResponseCode.SUCCESS, resp_dict.get("code"), msg="Error in status code return")

                self.assertIn("msg", resp_dict, msg="Error in data format return")
                self.assertEqual(
                    ResponseCode.CODE_MSG_MAP.get(ResponseCode.SUCCESS),
                    resp_dict.get("msg"),
                    msg="Error in status code return"
                )

                self.assertIn("data", resp_dict, msg="Error in data format return")
                self.assertIsNotNone(resp_dict.get("data"), msg="Error in data information return")
                #self.assertIn(data_new, resp_dict.get("data"), msg="Error in data information return")

    def test_get_interface_uppercase(self):
        """
        The get interface uppercase
        :return:
        """
        with app.app_context():
            data_github = {
                "version_control": "github",
                "scm_repo": "BBB",
                "scm_branch": "BBB",
                "scm_commit": "BBB",
                "repo": "BBB1",
                "branch": "BBB1",
                "enabled": False
            }

            data_git = {
                "version_control": "github",
                "scm_repo": "BBB",
                "scm_branch": "BBB",
                "scm_commit": "BBB",
                "repo": "BBB2",
                "branch": "BBB2",
                "enabled": False
            }

            for data_insert in [data_github, data_git]:
                create_tracking(data_insert)

                resp = self.client.get("/tracking?rep=BBB&BRAnch=BBB")

                resp_dict = json.loads(resp.data)
                self.assertIn("code", resp_dict, msg="Error in data format return")
                self.assertEqual(
                    ResponseCode.INPUT_PARAMETERS_ERROR, resp_dict.get("code"), msg="Error in status code return"
                )

                self.assertIn("msg", resp_dict, msg="Error in data format return")
                self.assertEqual(
                    ResponseCode.CODE_MSG_MAP.get(ResponseCode.INPUT_PARAMETERS_ERROR),
                    resp_dict.get("msg"),
                    msg="Error in status code return"
                )

                self.assertIn("data", resp_dict, msg="Error in data format return")
                self.assertEqual(resp_dict.get("data"), None, msg="Error in data information return")

    def test_version_control_error(self):
        """
        The POST version control error
        :return:
        """
        data = {
            "version_control": "gitgitgit",
            "scm_repo": "A",
            "scm_branch": "A",
            "scm_commit": "A",
            "repo": "A",
            "branch": "A",
            "enabled": 0
        }

        resp = self.client.post("/tracking", json=data, content_type="application/json", headers=self.auth)
        resp_dict = json.loads(resp.data)
        self.assertIn("code", resp_dict, msg="Error in data format return")
        self.assertEqual(ResponseCode.INPUT_PARAMETERS_ERROR, resp_dict.get("code"), msg="Error in status code return")

        self.assertIn("msg", resp_dict, msg="Error in data format return")
        self.assertEqual(
            ResponseCode.CODE_MSG_MAP.get(ResponseCode.INPUT_PARAMETERS_ERROR),
            resp_dict.get("msg"),
            msg="Error in status code return"
        )

        self.assertIn("data", resp_dict, msg="Error in data format return")
        self.assertEqual(resp_dict.get("data"), None, msg="Error in data information return")

    def test_delete_data(self):
        """
        The POST interface inserts data
        :return:
        """
        data_github = {
            "version_control": "github",
            "scm_repo": "test_delete",
            "scm_branch": "test_delete",
            "scm_commit": "test_delete",
            "repo": "test_delete1",
            "branch": "test_delete1",
            "enabled": 0
        }

        data_git = {
            "version_control": "git",
            "scm_repo": "test_delete",
            "scm_branch": "test_delete",
            "scm_commit": "test_delete",
            "repo": "test_delete1",
            "branch": "test_delete1",
            "enabled": 0
        }

        for data in [data_git, data_github]:
            self.client.post("/tracking", json=data, content_type="application/json", headers=self.auth)

            resp = self.client.delete(
                "/tracking?repo=test_delete1&branch=test_delete1", content_type="application/json", headers=self.auth
            )
            resp_dict = json.loads(resp.data)
            self.assertIn("code", resp_dict, msg="Error in data format return")
            self.assertEqual(ResponseCode.SUCCESS, resp_dict.get("code"), msg="Error in status code return")

    def test_delete_not_found(self):
        """
        The POST interface inserts data
        :return:
        """
        resp = self.client.delete(
            "/tracking?repo=not_found1&branch=not_found1", content_type="application/json", headers=self.auth
        )
        resp_dict = json.loads(resp.data)
        self.assertIn("code", resp_dict, msg="Error in data format return")
        self.assertEqual(ResponseCode.DELETE_DB_NOT_FOUND, resp_dict.get("code"), msg="Error in status code return")


if __name__ == '__main__':
    unittest.main()
