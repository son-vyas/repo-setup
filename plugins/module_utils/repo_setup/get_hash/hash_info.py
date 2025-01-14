#  Copyright 2021 Red Hat, Inc.
#
#  Licensed under the Apache License, Version 2.0 (the "License"); you may
#  not use this file except in compliance with the License. You may obtain
#  a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#  WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#  License for the specific language governing permissions and limitations
#  under the License.
#
#
from __future__ import absolute_import, division, print_function

import logging
import os
from .constants import CONFIG_PATH, CONFIG_KEYS, DEFAULT_CONFIG
from .exceptions import HashInvalidConfig, HashInvalidDLRNResponse

try:
    from repo_setup.utils import http_get
except ImportError:
    from ansible_collections.repo_setup.repos.plugins.module_utils.repo_setup.utils import (
        http_get,
    )


__metaclass__ = type


class HashInfo:
    """
    Objects of type HashInfo contain the attributes required to
    represent a particular delorean build hash. This includes the full, commit,
    distro and extended hashes (where applicable), as well as the release,
    OS name and version, component name (if applicable), named tag
    (current-podified, podified-testing etc) as well as the URL to the
    delorean server that provided the information used to build each object
    instance.
    """

    @classmethod
    def load_yaml(cls, filename):
        import yaml

        return yaml.safe_load(filename)

    @classmethod
    def _resolve_local_config_path(cls):
        """Load local config from disk from expected locations."""
        paths = [
            # pip install --user
            os.path.expanduser("~/.local/etc/repo_setup_get_hash/config.yaml"),
            # root install
            "/etc/repo_setup_get_hash/config.yaml",
            # embedded config.yaml as fallback
            os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.yaml"),
        ]
        for _local_config in paths:
            if cls._check_read_file(_local_config):
                return _local_config

    @classmethod
    def _check_read_file(cls, filepath):
        if os.path.isfile(filepath) and os.access(filepath, os.R_OK):
            return True
        return False

    @classmethod
    def load_config(cls, passed_config=None):
        """
        This is a class method since we call it from the CLI entrypoint
        before the HashInfo object is created. The method will first
        try to use constants.CONFIG_PATH. If that is missing it tries to use
        a local config.yaml for example for invocations from a source checkout
        directory. If the file is not found HashMissingConfig is raised.
        If any of the contants.CONFIG_KEYS is missing from config.yaml then
        HashInvalidConfig is raised. If the passed_config dict contains
        a given config value then that is used instead of the value from the
        loaded config file. Returns a dictionary containing
        the key->value for all the keys in constants.CONFIG_KEYS.

        :param passed_config: dict with configuration overrides
        :raises HashMissingConfig for missing config.yaml
        :raises HashInvalidConfig for missing keys in config.yaml
        :return: a config dictionary with the keys in constants.CONFIG_KEYS
        """

        passed_config = passed_config or {}
        result_config = {}
        config_path = ""
        local_config = cls._resolve_local_config_path()
        # prefer const.CONFIG_PATH then local_config
        if cls._check_read_file(CONFIG_PATH):
            config_path = CONFIG_PATH
        elif local_config:
            config_path = local_config
        else:
            logging.debug("Using embedded config file")
            loaded_config = DEFAULT_CONFIG
        logging.debug("Using config file at %s", config_path)
        if config_path != "":
            with open(config_path, "r") as config_yaml:
                loaded_config = cls.load_yaml(config_yaml)
        for k in CONFIG_KEYS:
            if k not in loaded_config:
                error_str = (
                    "Malformed config file - missing {0}. Expected all"
                    "of these configuration items: {1}"
                ).format(k, ", ".join(CONFIG_KEYS))
                logging.error(error_str)
                raise HashInvalidConfig(error_str)
            # if the passed config contains the key then use that value
            if passed_config.get(k):
                result_config[k] = passed_config[k]
            else:
                result_config[k] = loaded_config[k]
        return result_config

    def __init__(self, os_version, release, component, tag, config=None):
        """Create a new HashInfo object

        :param os_version: The OS and version e.g. centos8
        :param release: The OpenStack release e.g. wallaby
        :param component: The podified-ci component e.g. 'common' or None
        :param tag: The Delorean server named tag e.g. current-podified
        :param config: Use an existing config dictionary and don't load it
        """
        config = HashInfo.load_config(config)

        self.os_version = os_version
        self.release = release
        self.component = component
        self.tag = tag

        repo_url = self._resolve_repo_url(config["dlrn_url"])
        self.dlrn_url = repo_url

        repo_url_response, status = http_get(repo_url)

        if status != 200:
            error_str = (
                "Invalid response received from the delorean server. Queried "
                "URL: {0}. Response code: {1}. Response text: {2}. Failed to "
                "create HashInfo object."
            ).format(repo_url, status, repo_url_response)
            logging.error(error_str)
            raise HashInvalidDLRNResponse(error_str)

        if repo_url.endswith("commit.yaml"):
            from_commit_yaml = self._hashes_from_commit_yaml(repo_url_response)
            self.full_hash = from_commit_yaml[0]
            self.commit_hash = from_commit_yaml[1]
            self.distro_hash = from_commit_yaml[2]
            self.extended_hash = from_commit_yaml[3]
        else:
            self.full_hash = repo_url_response
            self.commit_hash = None
            self.distro_hash = None
            self.extended_hash = None

    def _resolve_repo_url(self, dlrn_url):
        """Resolve the delorean server URL given the various attributes of
        this HashInfo object. The only passed parameter is the
        dlrn_url. There are three main cases:
            * centos8/rhel8 component https://trunk.rdoproject.org/centos8/component/common/current-podified/commit.yaml
            * centos7 https://trunk.rdoproject.org/centos7/current-podified/commit.yaml
            * centos8/rhel8 non component https://trunk.rdoproject.org/centos8/current-podified/delorean.repo.md5
        Returns a string which is the full URL to the required item (i.e.
        commit.yaml or repo.md5 depending on the case).

        :param dlrn_url: The base url for the delorean server
        :returns string URL to required commit.yaml or repo.md5
        """  # noqa
        repo_url = ""
        if "centos7" in self.os_version:
            repo_url = "%s/%s-%s/%s/commit.yaml" % (
                dlrn_url,
                self.os_version,
                self.release,
                self.tag,
            )
        elif self.component is not None:
            repo_url = "%s/%s-%s/component/%s/%s/commit.yaml" % (
                dlrn_url,
                self.os_version,
                self.release,
                self.component,
                self.tag,
            )
        else:
            repo_url = "%s/%s-%s/%s/delorean.repo.md5" % (
                dlrn_url,
                self.os_version,
                self.release,
                self.tag,
            )
        logging.debug("repo_url is %s", repo_url)
        return repo_url

    def _hashes_from_commit_yaml(self, delorean_result):
        """This function is used when a commit.yaml file is returned
        by _resolve_repo_url. Returns a tuple containing the various
        extracted hashes: full, commit, distro and extended

        :returns tuple of strings full, commit, distro, extended hashes
        """
        parsed_yaml = self.load_yaml(delorean_result)
        commit = parsed_yaml["commits"][0]["commit_hash"]
        distro = parsed_yaml["commits"][0]["distro_hash"]
        full = "%s_%s" % (commit, distro[0:8])
        extended = parsed_yaml["commits"][0]["extended_hash"]
        logging.debug("delorean commit.yaml results %s", parsed_yaml["commits"][0])
        return full, commit, distro, extended

    def __repr__(self):
        """Returns a string representation of the object"""
        attrs = vars(self)
        return ",\n".join("%s: %s" % item for item in attrs.items())
