#   Copyright 2021 Red Hat, Inc.
#
#   Licensed under the Apache License, Version 2.0 (the "License"); you may
#   not use this file except in compliance with the License. You may obtain
#   a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#   WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#   License for the specific language governing permissions and limitations
#   under the License.
#
#

import unittest
import repo_setup.get_hash.hash_info as thi
import repo_setup.get_hash.exceptions as exc
from . import fakes as test_fakes
from unittest import mock
from unittest.mock import mock_open, MagicMock, patch


@mock.patch(
    'builtins.open', new_callable=mock_open, read_data=test_fakes.CONFIG_FILE
)
class TestGetHashInfo(unittest.TestCase):
    """In this class we test the functions and instantiation of the
    HashInfo class. The builtin 'open' function is mocked at a
    class level so we can mock the config.yaml with the contents of the
    fakes.CONFIG_FILE
    """

    def test_hashes_from_commit_yaml(self, mock_config):
        sample_commit_yaml = test_fakes.TEST_COMMIT_YAML_COMPONENT
        expected_result = (
            '476a52df13202a44336c8b01419f8b73b93d93eb_1f5a41f3',
            '476a52df13202a44336c8b01419f8b73b93d93eb',
            '1f5a41f31db8e3eb51caa9c0e201ab0583747be8',
            'None',
        )
        mocked = MagicMock(
            return_value=(test_fakes.TEST_COMMIT_YAML_COMPONENT, 200))
        with patch(
                'repo_setup.get_hash.hash_info.http_get', mocked):
            mock_hash_info = thi.HashInfo(
                'centos8', 'master', 'common', 'current-podified'
            )
            actual_result = mock_hash_info._hashes_from_commit_yaml(
                sample_commit_yaml
            )
            self.assertEqual(expected_result, actual_result)

    def test_resolve_repo_url_component_commit_yaml(self, mock_config):
        mocked = MagicMock(
            return_value=(test_fakes.TEST_COMMIT_YAML_COMPONENT, 200))
        with patch(
                'repo_setup.get_hash.hash_info.http_get', mocked):
            c8_component_hash_info = thi.HashInfo(
                'centos8', 'master', 'common', 'current-podified'
            )
            repo_url = c8_component_hash_info._resolve_repo_url("https://woo")
            self.assertEqual(
                repo_url,
                'https://woo/centos8-master/component/common/current-podified/commit.yaml',  # noqa
            )

    def test_resolve_repo_url_centos8_repo_md5(self, mock_config):
        mocked = MagicMock(
            return_value=(test_fakes.TEST_REPO_MD5, 200))
        with patch(
                'repo_setup.get_hash.hash_info.http_get', mocked):
            c8_hash_info = thi.HashInfo(
                'centos8', 'master', None, 'current-podified'
            )
            repo_url = c8_hash_info._resolve_repo_url("https://woo")
            self.assertEqual(
                repo_url, 'https://woo/centos8-master/current-podified/delorean.repo.md5'  # noqa

            )

    def test_resolve_repo_url_centos7_commit_yaml(self, mock_config):
        mocked = MagicMock(
            return_value=(test_fakes.TEST_COMMIT_YAML_CENTOS_7, 200))
        with patch(
                'repo_setup.get_hash.hash_info.http_get', mocked):
            c7_hash_info = thi.HashInfo(
                'centos7', 'master', None, 'current-podified'
            )
            repo_url = c7_hash_info._resolve_repo_url("https://woo")
            self.assertEqual(
                repo_url, 'https://woo/centos7-master/current-podified/commit.yaml'  # noqa

            )

    def test_get_hash_info_centos8_md5(self, mock_config):
        mocked = MagicMock(
            return_value=(test_fakes.TEST_REPO_MD5, 200))
        with patch(
                'repo_setup.get_hash.hash_info.http_get', mocked):
            created_hash_info = thi.HashInfo(
                'centos8', 'master', None, 'current-podified'
            )
            self.assertIsInstance(created_hash_info, thi.HashInfo)
            self.assertEqual(
                created_hash_info.full_hash, test_fakes.TEST_REPO_MD5
            )
            self.assertEqual(created_hash_info.tag, 'current-podified')
            self.assertEqual(created_hash_info.os_version, 'centos8')
            self.assertEqual(created_hash_info.release, 'master')

    def test_get_hash_info_component(self, mock_config):
        expected_commit_hash = '476a52df13202a44336c8b01419f8b73b93d93eb'
        expected_distro_hash = '1f5a41f31db8e3eb51caa9c0e201ab0583747be8'
        expected_full_hash = '476a52df13202a44336c8b01419f8b73b93d93eb_1f5a41f3'  # noqa
        mocked = MagicMock(
            return_value=(test_fakes.TEST_COMMIT_YAML_COMPONENT, 200))
        with patch(
                'repo_setup.get_hash.hash_info.http_get', mocked):
            created_hash_info = thi.HashInfo(
                'centos8', 'victoria', 'common', 'podified-ci-testing'
            )
            self.assertIsInstance(created_hash_info, thi.HashInfo)
            self.assertEqual(created_hash_info.full_hash, expected_full_hash)
            self.assertEqual(
                created_hash_info.distro_hash, expected_distro_hash
            )
            self.assertEqual(
                created_hash_info.commit_hash, expected_commit_hash
            )
            self.assertEqual(created_hash_info.component, 'common')
            self.assertEqual(created_hash_info.tag, 'podified-ci-testing')
            self.assertEqual(created_hash_info.release, 'victoria')

    def test_get_hash_info_centos7_commit_yaml(self, mock_config):
        expected_commit_hash = 'b5ef03c9c939db551b03e9490edc6981ff582035'
        expected_distro_hash = '76ebc4655502820b7677579349fd500eeca292e6'
        expected_full_hash = 'b5ef03c9c939db551b03e9490edc6981ff582035_76ebc465'  # noqa
        mocked = MagicMock(
            return_value=(test_fakes.TEST_COMMIT_YAML_CENTOS_7, 200))
        with patch(
                'repo_setup.get_hash.hash_info.http_get', mocked):
            created_hash_info = thi.HashInfo(
                'centos7', 'master', None, 'podified-ci-testing'
            )
            self.assertIsInstance(created_hash_info, thi.HashInfo)
            self.assertEqual(created_hash_info.full_hash, expected_full_hash)
            self.assertEqual(
                created_hash_info.distro_hash, expected_distro_hash
            )
            self.assertEqual(
                created_hash_info.commit_hash, expected_commit_hash
            )
            self.assertEqual(created_hash_info.os_version, 'centos7')

    def test_bad_config_file(self, mock_config):
        mocked = MagicMock(
            return_value=test_fakes.TEST_COMMIT_YAML_CENTOS_7)
        with patch(
                'repo_setup.get_hash.hash_info.http_get', mocked):
            with mock.patch(
                'builtins.open',
                new_callable=mock_open,
                read_data=test_fakes.BAD_CONFIG_FILE,
            ):
                self.assertRaises(
                    exc.HashInvalidConfig,
                    thi.HashInfo,
                    'centos7',
                    'master',
                    None,
                    'podified-ci-testing',
                )

    def test_override_config_dlrn_url(self, mock_config):
        expected_dlrn_url = 'https://foo.bar.baz/centos8-master/component/common/current-podified/commit.yaml'  # noqa
        mocked = MagicMock(
            return_value=(test_fakes.TEST_COMMIT_YAML_COMPONENT, 200))
        with patch(
                'repo_setup.get_hash.hash_info.http_get', mocked):
            mock_hash_info = thi.HashInfo(
                'centos8', 'master', 'common', 'current-podified',
                {'dlrn_url': 'https://foo.bar.baz'}
            )
            self.assertEqual(expected_dlrn_url, mock_hash_info.dlrn_url)

    def test_override_config_dlrn_url_empty_ignored(self, mock_config):
        expected_dlrn_url = 'https://trunk.rdoproject.org/centos8-master/component/common/current-podified/commit.yaml'  # noqa
        mocked = MagicMock(
            return_value=(test_fakes.TEST_COMMIT_YAML_COMPONENT, 200))
        with patch(
                'repo_setup.get_hash.hash_info.http_get', mocked):
            mock_hash_info = thi.HashInfo(
                'centos8', 'master', 'common', 'current-podified',
                {'dlrn_url': ''}
            )
            self.assertEqual(expected_dlrn_url, mock_hash_info.dlrn_url)

    def test_404_dlrn_http_status_code(self, mock_config):
        bad_dlrn_url = 'https://server.ok/centos8-master/component/common/current-podified/commit.yaml'  # noqa
        response_text_404 = "Some kind of 404 text NOT FOUND!"
        mocked = MagicMock(
            return_value=(response_text_404, 404))
        with patch(
                'repo_setup.get_hash.hash_info.http_get', mocked):
            with self.assertLogs() as captured:
                self.assertRaises(
                    exc.HashInvalidDLRNResponse,
                    thi.HashInfo,
                    'centos8',
                    'master',
                    'common',
                    'current-podified',
                    {'dlrn_url': 'https://server.ok'},
                )
            debug_msgs = [
                record.message
                for record in captured.records
                if record.levelname == 'ERROR'
            ]
            error_str = (
                "Invalid response received from the delorean server. Queried "
                "URL: {0}. Response code: {1}. Response text: {2}. Failed to "
                "create HashInfo object."
            ).format(bad_dlrn_url, '404', response_text_404)
            self.assertIn(error_str, debug_msgs)
