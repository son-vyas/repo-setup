# Copyright 2016 Red Hat, Inc.
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import subprocess
import sys
from unittest import mock

import ddt
import testtools

from repo_setup import main


@ddt.ddt
class TestTripleORepos(testtools.TestCase):
    @mock.patch('repo_setup.main._get_distro')
    @mock.patch('sys.argv', ['repo-setup', 'current', '-d', 'centos8'])
    @mock.patch('repo_setup.main._run_pkg_clean')
    @mock.patch('repo_setup.main._validate_args')
    @mock.patch('repo_setup.main._get_base_path')
    @mock.patch('repo_setup.main._remove_existing')
    @mock.patch('repo_setup.main._install_repos')
    def test_main_centos8(self, mock_install, mock_remove, mock_gbp,
                          mock_validate, mock_clean, mock_distro):
        mock_distro.return_value = ('centos', '8', 'CentOS 8')
        args = main._parse_args('centos', '8')
        mock_path = mock.Mock()
        mock_gbp.return_value = mock_path
        main.main()
        mock_validate.assert_called_once_with(args, 'CentOS 8', '8')
        mock_gbp.assert_called_once_with(args)
        mock_remove.assert_called_once_with(args)
        mock_clean.assert_called_once_with('centos8')

    @mock.patch('repo_setup.main._get_distro')
    @mock.patch('sys.argv', ['repo-setup', 'current', '-d', 'fedora'])
    @mock.patch('repo_setup.main._run_pkg_clean')
    @mock.patch('repo_setup.main._validate_args')
    @mock.patch('repo_setup.main._get_base_path')
    @mock.patch('repo_setup.main._install_priorities')
    @mock.patch('repo_setup.main._remove_existing')
    @mock.patch('repo_setup.main._install_repos')
    def test_main_fedora(self, mock_install, mock_remove, mock_ip, mock_gbp,
                         mock_validate, mock_clean, mock_distro):
        mock_distro.return_value = ('centos', '8', 'CentOS 8')
        args = main._parse_args('centos', '8')
        mock_path = mock.Mock()
        mock_gbp.return_value = mock_path
        main.main()
        mock_validate.assert_called_once_with(args, 'CentOS 8', '8')
        mock_gbp.assert_called_once_with(args)
        assert not mock_ip.called, '_install_priorities should no tbe called'
        mock_remove.assert_called_once_with(args)
        mock_install.assert_called_once_with(args, mock_path)
        mock_clean.assert_called_once_with('fedora')

    @mock.patch('requests.get')
    def test_get_repo(self, mock_get):
        mock_response = mock.Mock()
        mock_response.status_code = 200
        mock_response.text = '88MPH'
        mock_get.return_value = mock_response
        fake_addr = 'http://lone/pine/mall'
        args = mock.Mock()
        args.distro = 'centos'
        content = main._get_repo(fake_addr, args)
        self.assertEqual('88MPH', content)
        mock_get.assert_called_once_with(fake_addr)

    @mock.patch('requests.get')
    def test_get_repo_404(self, mock_get):
        mock_response = mock.Mock()
        mock_response.status_code = 404
        mock_get.return_value = mock_response
        fake_addr = 'http://twin/pines/mall'
        main._get_repo(fake_addr, mock.Mock())
        mock_get.assert_called_once_with(fake_addr)
        mock_response.raise_for_status.assert_called_once_with()

    @mock.patch('os.listdir')
    @mock.patch('os.remove')
    @mock.patch('os.path.exists')
    def test_remove_existing(self, mock_exists, mock_remove, mock_listdir):
        fake_list = ['foo.repo', 'delorean.repo',
                     'delorean-current-podified.repo',
                     'repo-setup-centos-opstools.repo',
                     'repo-setup-centos-highavailability.repo']
        mock_exists.return_value = [True, False, True, False, True,
                                    False, False, True]
        mock_listdir.return_value = fake_list
        mock_args = mock.Mock()
        mock_args.output_path = '/etc/yum.repos.d'
        main._remove_existing(mock_args)
        self.assertIn(mock.call('/etc/yum.repos.d/delorean.repo'),
                      mock_remove.mock_calls)
        self.assertIn(mock.call('/etc/yum.repos.d/'
                                'delorean-current-podified.repo'),
                      mock_remove.mock_calls)
        self.assertIn(
            mock.call('/etc/yum.repos.d/repo-setup-centos-opstools.repo'),
            mock_remove.mock_calls)
        self.assertIn(
            mock.call('/etc/distro.repos.d/'
                      'repo-setup-centos-highavailability.repo'),
            mock_remove.mock_calls)
        self.assertNotIn(mock.call('/etc/yum.repos.d/foo.repo'),
                         mock_remove.mock_calls)

    # There is no $DISTRO single path anymore, every path has branch
    # specification, even master
    def test_get_base_path(self):
        args = mock.Mock()
        args.branch = 'master'
        args.distro = 'centos7'
        args.rdo_mirror = 'http://trunk.rdoproject.org'
        path = main._get_base_path(args)
        self.assertEqual('http://trunk.rdoproject.org/centos7-master/', path)

    def test_get_base_path_fedora(self):
        args = mock.Mock()
        args.branch = 'master'
        args.distro = 'fedora'
        args.rdo_mirror = 'http://trunk.rdoproject.org'
        path = main._get_base_path(args)
        self.assertEqual('http://trunk.rdoproject.org/fedora-master/', path)

    @mock.patch('subprocess.check_call')
    def test_install_priorities(self, mock_check_call):
        main._install_priorities()
        mock_check_call.assert_called_once_with(['yum', 'install', '-y',
                                                 'yum-plugin-priorities'])

    @mock.patch('subprocess.check_call')
    def test_install_priorities_fails(self, mock_check_call):
        mock_check_call.side_effect = subprocess.CalledProcessError(88, '88')
        self.assertRaises(subprocess.CalledProcessError,
                          main._install_priorities)

    @mock.patch('repo_setup.main._get_repo')
    @mock.patch('repo_setup.main._write_repo')
    def test_install_repos_current(self, mock_write, mock_get):
        args = mock.Mock()
        args.repos = ['current']
        args.branch = 'master'
        args.output_path = 'test'
        args.distro = 'fake'
        mock_get.return_value = '[delorean]\nMr. Fusion'
        main._install_repos(args, 'roads/')
        self.assertEqual([mock.call('roads/current/delorean.repo', args),
                          mock.call('roads/delorean-deps.repo', args),
                          ],
                         mock_get.mock_calls)
        self.assertEqual([mock.call('[delorean]\nMr. Fusion', 'test',
                                    name='delorean'),
                          mock.call('[delorean]\nMr. Fusion', 'test'),
                          ],
                         mock_write.mock_calls)

    @mock.patch('repo_setup.main._get_repo')
    @mock.patch('repo_setup.main._write_repo')
    def test_install_repos_current_mitaka(self, mock_write, mock_get):
        args = mock.Mock()
        args.repos = ['current']
        args.branch = 'mitaka'
        args.output_path = 'test'
        args.distro = 'fake'
        mock_get.return_value = '[delorean]\nMr. Fusion'
        main._install_repos(args, 'roads/')
        self.assertEqual([mock.call('roads/current/delorean.repo', args),
                          mock.call('roads/delorean-deps.repo', args),
                          ],
                         mock_get.mock_calls)
        self.assertEqual([mock.call('[delorean]\nMr. Fusion', 'test',
                                    name='delorean'),
                          mock.call('[delorean]\nMr. Fusion', 'test'),
                          ],
                         mock_write.mock_calls)

    @mock.patch('repo_setup.main._get_repo')
    @mock.patch('repo_setup.main._write_repo')
    def test_install_repos_deps(self, mock_write, mock_get):
        args = mock.Mock()
        args.repos = ['deps']
        args.branch = 'master'
        args.output_path = 'test'
        args.distro = 'fake'
        mock_get.return_value = '[delorean-deps]\nMr. Fusion'
        main._install_repos(args, 'roads/')
        mock_get.assert_called_once_with('roads/delorean-deps.repo', args)
        mock_write.assert_called_once_with('[delorean-deps]\nMr. Fusion',
                                           'test')

    @mock.patch('repo_setup.main._get_repo')
    @mock.patch('repo_setup.main._write_repo')
    def test_install_repos_current_podified(self, mock_write, mock_get):
        args = mock.Mock()
        args.repos = ['current-podified']
        args.branch = 'master'
        args.output_path = 'test'
        args.distro = 'fake'
        mock_get.return_value = '[delorean]\nMr. Fusion'
        main._install_repos(args, 'roads/')
        self.assertEqual([mock.call('roads/current-podified/delorean.repo',
                                    args),
                          mock.call('roads/delorean-deps.repo', args),
                          ],
                         mock_get.mock_calls)
        self.assertEqual([mock.call('[delorean]\nMr. Fusion', 'test'),
                          mock.call('[delorean]\nMr. Fusion', 'test'),
                          ],
                         mock_write.mock_calls)

    @mock.patch('repo_setup.main._get_repo')
    @mock.patch('repo_setup.main._write_repo')
    def test_install_repos_current_podified_dev(self, mock_write, mock_get):
        args = mock.Mock()
        args.repos = ['current-podified-dev']
        args.branch = 'master'
        args.output_path = 'test'
        args.distro = 'fake'
        mock_get.return_value = '[delorean]\nMr. Fusion'
        main._install_repos(args, 'roads/')
        mock_get.assert_any_call('roads/delorean-deps.repo', args)
        # This is the wrong name for the deps repo, but I'm not bothered
        # enough by that to mess with mocking multiple different calls.
        mock_write.assert_any_call('[delorean]\nMr. Fusion', 'test')
        mock_get.assert_any_call('roads/current-podified/delorean.repo', args)
        mock_write.assert_any_call('[delorean-current-podified]\n'
                                   'priority=20\nMr. Fusion', 'test',
                                   name='delorean-current-podified')
        mock_get.assert_called_with('roads/current/delorean.repo', args)
        mock_write.assert_called_with('[delorean]\npriority=10\n%s\n'
                                      'Mr. Fusion' %
                                      main.INCLUDE_PKGS, 'test',
                                      name='delorean')

    @mock.patch('repo_setup.main._get_repo')
    @mock.patch('repo_setup.main._write_repo')
    def test_install_repos_podified_ci_testing(self, mock_write, mock_get):
        args = mock.Mock()
        args.repos = ['podified-ci-testing']
        args.branch = 'master'
        args.output_path = 'test'
        args.distro = 'fake'
        mock_get.return_value = '[delorean]\nMr. Fusion'
        main._install_repos(args, 'roads/')
        self.assertEqual([mock.call('roads/podified-ci-testing/delorean.repo',
                                    args),
                          mock.call('roads/delorean-deps.repo', args),
                          ],
                         mock_get.mock_calls)
        self.assertEqual([mock.call('[delorean]\nMr. Fusion', 'test'),
                          mock.call('[delorean]\nMr. Fusion', 'test'),
                          ],
                         mock_write.mock_calls)

    @mock.patch('repo_setup.main._get_repo')
    @mock.patch('repo_setup.main._write_repo')
    def test_install_repos_current_podified_rdo(self, mock_write, mock_get):
        args = mock.Mock()
        args.repos = ['current-podified-rdo']
        args.branch = 'master'
        args.output_path = 'test'
        args.distro = 'fake'
        mock_get.return_value = '[delorean]\nMr. Fusion'
        main._install_repos(args, 'roads/')
        self.assertEqual([mock.call('roads/current-podified-rdo/delorean.repo',
                                    args),
                          mock.call('roads/delorean-deps.repo', args),
                          ],
                         mock_get.mock_calls)
        self.assertEqual([mock.call('[delorean]\nMr. Fusion', 'test'),
                          mock.call('[delorean]\nMr. Fusion', 'test'),
                          ],
                         mock_write.mock_calls)

    @ddt.data('liberty', 'mitaka', 'newton', 'ocata', 'pike', 'queens',
              'rocky', 'stein', 'master')
    @mock.patch('repo_setup.main._write_repo')
    @mock.patch('repo_setup.main._create_ceph')
    def test_install_repos_ceph(self,
                                branch,
                                mock_create_ceph,
                                mock_write_repo):
        ceph_release = {
            'liberty': 'hammer',
            'mitaka': 'hammer',
            'newton': 'jewel',
            'ocata': 'jewel',
            'pike': 'jewel',
            'queens': 'luminous',
            'rocky': 'luminous',
            'stein': 'nautilus',
            'train': 'nautilus',
            'ussuri': 'nautilus',
            'victoria': 'nautilus',
            'master': 'pacific',
        }
        args = mock.Mock()
        args.repos = ['ceph']
        args.branch = branch
        args.output_path = 'test'
        args.distro = 'fake'
        mock_repo = '[centos-ceph-luminous]\nMr. Fusion'
        mock_create_ceph.return_value = mock_repo
        main._install_repos(args, 'roads/')
        mock_create_ceph.assert_called_once_with(args, ceph_release[branch])
        mock_write_repo.assert_called_once_with(mock_repo, 'test')

    @mock.patch('repo_setup.main._write_repo')
    def test_install_repos_opstools(self, mock_write):
        args = mock.Mock()
        args.repos = ['opstools']
        args.branch = 'master'
        args.output_path = 'test'
        args.mirror = 'http://foo'
        args.distro = 'fake'
        main._install_repos(args, 'roads/')
        expected_repo = ('\n[repo-setup-centos-opstools]\n'
                         'name=repo-setup-centos-opstools\n'
                         'baseurl=http://foo/centos/7/opstools/$basearch/\n'
                         'gpgcheck=0\n'
                         'enabled=1\n')
        mock_write.assert_called_once_with(expected_repo,
                                           'test')

    @mock.patch('requests.get')
    @mock.patch('repo_setup.main._write_repo')
    def test_install_repos_deps_mirror(self, mock_write, mock_get):
        args = mock.Mock()
        args.repos = ['deps']
        args.branch = 'master'
        args.output_path = 'test'
        args.old_mirror = 'http://mirror.centos.org'
        args.mirror = 'http://foo'
        args.distro = 'centos7'
        args.rdo_mirror = 'http://bar'
        # Abbreviated repos to verify the regex works
        fake_repo = '''
[delorean-current-podified]
name=test repo
baseurl=https://trunk.rdoproject.org/centos7/some-repo-hash
enabled=1

[rdo-qemu-ev]
name=test qemu-ev
baseurl=http://mirror.centos.org/centos/7/virt/$basearch/kvm-common
enabled=1
'''
        expected_repo = '''
[delorean-current-podified]
name=test repo
baseurl=http://bar/centos7/some-repo-hash
enabled=1

[rdo-qemu-ev]
name=test qemu-ev
baseurl=http://foo/centos/7/virt/$basearch/kvm-common
enabled=1
'''
        mock_get.return_value = mock.Mock(text=fake_repo,
                                          status_code=200)
        main._install_repos(args, 'roads/')
        mock_write.assert_called_once_with(expected_repo,
                                           'test')

    def test_install_repos_invalid(self):
        args = mock.Mock()
        args.repos = ['roads?']
        self.assertRaises(main.InvalidArguments, main._install_repos, args,
                          'roads/')

    @mock.patch('repo_setup.main._get_repo')
    @mock.patch('repo_setup.main._write_repo')
    def test_install_repos_centos8(self, mock_write, mock_get):
        args = mock.Mock()
        args.repos = ['current']
        args.branch = 'master'
        args.output_path = 'test'
        args.distro = 'centos8'
        args.stream = False
        args.mirror = 'mirror'
        mock_get.return_value = '[delorean]\nMr. Fusion'
        main._install_repos(args, 'roads/')
        self.assertEqual([mock.call('roads/current/delorean.repo', args),
                          mock.call('roads/delorean-deps.repo', args),
                          ],
                         mock_get.mock_calls)
        self.assertEqual([mock.call('[delorean]\nMr. Fusion', 'test',
                                    name='delorean'),
                          mock.call('[delorean]\nMr. Fusion', 'test'),
                          mock.call((
                              '\n[repo-setup-centos-highavailability]\n'
                              'name=repo-setup-centos-highavailability\n'
                              'baseurl=mirror/centos/8/HighAvailability'
                              '/$basearch/os/\ngpgcheck=0\nenabled=1\n'),
                              'test'),
                          mock.call((
                              '\n[repo-setup-centos-powertools]\n'
                              'name=repo-setup-centos-powertools\n'
                              'baseurl=mirror/centos/8/PowerTools'
                              '/$basearch/os/\ngpgcheck=0\nenabled=1\n'),
                              'test')
                          ],
                         mock_write.mock_calls)

    @mock.patch('repo_setup.main._get_repo')
    @mock.patch('repo_setup.main._write_repo')
    def test_install_repos_centos8_stream(self, mock_write, mock_get):
        args = mock.Mock()
        args.repos = ['current']
        args.branch = 'master'
        args.output_path = 'test'
        args.distro = 'centos8'
        args.stream = True
        args.no_stream = False
        args.mirror = 'mirror'
        mock_get.return_value = '[delorean]\nMr. Fusion'
        main._install_repos(args, 'roads/')
        self.assertEqual([mock.call('roads/current/delorean.repo', args),
                          mock.call('roads/delorean-deps.repo', args),
                          ],
                         mock_get.mock_calls)
        self.assertEqual([mock.call('[delorean]\nMr. Fusion', 'test',
                                    name='delorean'),
                          mock.call('[delorean]\nMr. Fusion', 'test'),
                          mock.call((
                              '\n[repo-setup-centos-highavailability]\n'
                              'name=repo-setup-centos-highavailability\n'
                              'baseurl=mirror/centos/8-stream/HighAvailability'
                              '/$basearch/os/\ngpgcheck=0\nenabled=1\n'),
                              'test'),
                          mock.call((
                              '\n[repo-setup-centos-powertools]\n'
                              'name=repo-setup-centos-powertools\n'
                              'baseurl=mirror/centos/8-stream/PowerTools'
                              '/$basearch/os/\ngpgcheck=0\nenabled=1\n'),
                              'test')
                          ],
                         mock_write.mock_calls)

    @mock.patch('repo_setup.main._get_repo')
    @mock.patch('repo_setup.main._write_repo')
    def test_install_repos_centos9_stream(self, mock_write, mock_get):
        args = mock.Mock()
        args.repos = ['current']
        args.branch = 'master'
        args.output_path = 'test'
        args.distro = 'centos9'
        args.stream = True
        args.no_stream = False
        args.mirror = 'mirror'
        mock_get.return_value = '[delorean]\nMr. Fusion'
        main._install_repos(args, 'roads/')
        self.assertEqual([mock.call('roads/current/delorean.repo', args),
                          mock.call('roads/delorean-deps.repo', args),
                          ],
                         mock_get.mock_calls)
        self.assertEqual([mock.call('[delorean]\nMr. Fusion', 'test',
                                    name='delorean'),
                          mock.call('[delorean]\nMr. Fusion', 'test'),
                          mock.call((
                              '\n[repo-setup-centos-highavailability]\n'
                              'name=repo-setup-centos-highavailability\n'
                              'baseurl=mirror/9-stream/HighAvailability'
                              '/$basearch/os/\ngpgcheck=0\nenabled=1\n'),
                              'test'),
                          mock.call((
                              '\n[repo-setup-centos-powertools]\n'
                              'name=repo-setup-centos-powertools\n'
                              'baseurl=mirror/9-stream/CRB'
                              '/$basearch/os/\ngpgcheck=0\nenabled=1\n'),
                              'test'),
                          mock.call((
                              '\n[repo-setup-centos-appstream]\n'
                              'name=repo-setup-centos-appstream\n'
                              'baseurl=mirror/9-stream/AppStream'
                              '/$basearch/os/\ngpgcheck=0\nenabled=1\n\n'),
                              'test'),
                          mock.call((
                              '\n[repo-setup-centos-baseos]\n'
                              'name=repo-setup-centos-baseos\n'
                              'baseurl=mirror/9-stream/BaseOS'
                              '/$basearch/os/\ngpgcheck=0\nenabled=1\n'),
                              'test')
                          ],
                         mock_write.mock_calls)

    @mock.patch('repo_setup.main._get_repo')
    @mock.patch('repo_setup.main._write_repo')
    def test_install_repos_centos8_no_stream(self, mock_write, mock_get):
        args = mock.Mock()
        args.repos = ['current']
        args.branch = 'master'
        args.output_path = 'test'
        args.distro = 'centos8'
        args.stream = False
        args.no_stream = True
        args.mirror = 'mirror'
        mock_get.return_value = '[delorean]\nMr. Fusion'
        main._install_repos(args, 'roads/')
        self.assertEqual([mock.call('roads/current/delorean.repo', args),
                          mock.call('roads/delorean-deps.repo', args),
                          ],
                         mock_get.mock_calls)
        self.assertEqual([mock.call('[delorean]\nMr. Fusion', 'test',
                                    name='delorean'),
                          mock.call('[delorean]\nMr. Fusion', 'test'),
                          mock.call((
                              '\n[repo-setup-centos-highavailability]\n'
                              'name=repo-setup-centos-highavailability\n'
                              'baseurl=mirror/centos/8/HighAvailability'
                              '/$basearch/os/\ngpgcheck=0\nenabled=1\n'),
                              'test'),
                          mock.call((
                              '\n[repo-setup-centos-powertools]\n'
                              'name=repo-setup-centos-powertools\n'
                              'baseurl=mirror/centos/8/PowerTools'
                              '/$basearch/os/\ngpgcheck=0\nenabled=1\n'),
                              'test')
                          ],
                         mock_write.mock_calls)

    def test_write_repo(self):
        m = mock.mock_open()
        with mock.patch('repo_setup.main.open', m, create=True):
            main._write_repo('#Doc\n[delorean]\nThis=Heavy', 'test')
        m.assert_called_once_with('test/delorean.repo', 'w')
        m().write.assert_called_once_with('#Doc\n[delorean]\nThis=Heavy')

    def test_write_repo_invalid(self):
        self.assertRaises(main.NoRepoTitle, main._write_repo, 'Great Scot!',
                          'test')

    def test_parse_args(self):
        with mock.patch.object(sys, 'argv', ['', 'current', 'deps', '-d',
                                             'centos7', '-b', 'liberty',
                                             '-o', 'test']):
            args = main._parse_args('centos', '8')
        self.assertEqual(['current', 'deps'], args.repos)
        self.assertEqual('centos7', args.distro)
        self.assertEqual('liberty', args.branch)
        self.assertEqual('test', args.output_path)

    def test_parse_args_long(self):
        with mock.patch.object(sys, 'argv', ['', 'current', '--distro',
                                             'centos7', '--branch',
                                             'mitaka', '--output-path',
                                             'test']):
            args = main._parse_args('centos', '8')
        self.assertEqual(['current'], args.repos)
        self.assertEqual('centos7', args.distro)
        self.assertEqual('mitaka', args.branch)
        self.assertEqual('test', args.output_path)

    def test_change_priority(self):
        result = main._change_priority('[delorean]\npriority=1', 10)
        self.assertEqual('[delorean]\npriority=10', result)

    def test_change_priority_none(self):
        result = main._change_priority('[delorean]', 10)
        self.assertEqual('[delorean]\npriority=10', result)

    def test_change_priority_none_muilti(self):
        data = "[repo1]\n[repo2]\n"
        expected = "[repo1]\n{0}\n[repo2]\n{0}\n".format("priority=10")
        result = main._change_priority(data, 10)
        self.assertEqual(expected, result)

    def test_add_includepkgs(self):
        data = "[repo1]\n[repo2]"
        expected = "[repo1]\n{0}\n[repo2]\n{0}".format(main.INCLUDE_PKGS)
        result = main._add_includepkgs(data)
        self.assertEqual(expected, result)

    def test_create_ceph(self):
        mock_args = mock.Mock(mirror='http://foo')
        result = main._create_ceph(mock_args, 'jewel')
        expected_repo = '''
[repo-setup-centos-ceph-jewel]
name=repo-setup-centos-ceph-jewel
baseurl=http://foo/SIGs/9-stream/storage/$basearch/ceph-jewel/
gpgcheck=0
enabled=1
'''
        self.assertEqual(expected_repo, result)

        mock_args = mock.Mock(mirror='http://foo', distro='centos8')
        result = main._create_ceph(mock_args, 'jewel')
        expected_repo = '''
[repo-setup-centos-ceph-jewel]
name=repo-setup-centos-ceph-jewel
baseurl=http://foo/centos/8-stream/storage/$basearch/ceph-jewel/
gpgcheck=0
enabled=1
'''
        self.assertEqual(expected_repo, result)

    def test_inject_mirrors_centos(self):
        start_repo = '''
[delorean]
name=delorean
baseurl=https://trunk.rdoproject.org/centos7/some-repo-hash
enabled=1
[centos]
name=centos
baseurl=http://mirror.centos.org/centos/7/virt/$basearch/kvm-common
enabled=1
'''
        expected = '''
[delorean]
name=delorean
baseurl=http://bar/centos7/some-repo-hash
enabled=1
[centos]
name=centos
baseurl=http://foo/centos/7/virt/$basearch/kvm-common
enabled=1
'''
        mock_args = mock.Mock(mirror='http://foo',
                              rdo_mirror='http://bar',
                              distro='centos',
                              old_mirror='http://mirror.centos.org')
        result = main._inject_mirrors(start_repo, mock_args)
        self.assertEqual(expected, result)

    def test_inject_mirrors_rhel(self):
        start_repo = '''
[delorean]
name=delorean
baseurl=https://trunk.rdoproject.org/centos7/some-repo-hash
enabled=1
[rhel]
name=rhel
baseurl=https://some/stuff
enabled=1
'''
        expected = '''
[delorean]
name=delorean
baseurl=http://bar/centos7/some-repo-hash
enabled=1
[rhel]
name=rhel
baseurl=http://foo/stuff
enabled=1
'''
        mock_args = mock.Mock(mirror='http://foo',
                              rdo_mirror='http://bar',
                              distro='rhel',
                              old_mirror='https://some')
        result = main._inject_mirrors(start_repo, mock_args)
        self.assertEqual(expected, result)

    def test_inject_mirrors_no_match(self):
        start_repo = '''
[delorean]
name=delorean
baseurl=https://some.mirror.com/centos7/some-repo-hash
enabled=1
'''
        mock_args = mock.Mock(rdo_mirror='http://some.mirror.com',
                              distro='centos')
        # If a user has a mirror whose repos already point at itself then
        # the _inject_mirrors call should be a noop.
        self.assertEqual(start_repo, main._inject_mirrors(start_repo,
                                                          mock_args))

    @mock.patch('subprocess.check_call')
    def test_run_pkg_clean(self, mock_check_call):
        main._run_pkg_clean('centos7')
        mock_check_call.assert_called_once_with(['yum', 'clean', 'metadata'])

    @mock.patch('subprocess.check_call')
    def test_run_pkg_clean_fedora(self, mock_check_call):
        main._run_pkg_clean('fedora')
        mock_check_call.assert_called_once_with(['dnf', 'clean', 'metadata'])

    @mock.patch('subprocess.check_call')
    def test_run_pkg_clean_fails(self, mock_check_call):
        mock_check_call.side_effect = subprocess.CalledProcessError(88, '88')
        self.assertRaises(subprocess.CalledProcessError,
                          main._run_pkg_clean, ['centos7'])


class TestValidate(testtools.TestCase):
    def setUp(self):
        super(TestValidate, self).setUp()
        self.args = mock.Mock()
        self.args.repos = ['current']
        self.args.branch = 'master'
        self.args.distro = 'centos7'
        self.distro_major_version_id = "7"
        self.args.stream = False
        self.args.no_stream = False

    def test_good(self):
        main._validate_args(self.args, '', '')

    def test_current_and_podified_dev(self):
        self.args.repos = ['current', 'current-podified-dev']
        self.assertRaises(main.InvalidArguments, main._validate_args,
                          self.args, '', '')

    def test_podified_ci_testing_and_current_podified(self):
        self.args.repos = ['current-podified', 'podified-ci-testing']
        self.assertRaises(main.InvalidArguments, main._validate_args,
                          self.args, '', '')

    def test_podified_ci_testing_and_ceph_opstools_allowed(self):
        self.args.repos = ['ceph', 'opstools', 'podified-ci-testing']
        main._validate_args(self.args, '', '')

    def test_podified_ci_testing_and_deps_allowed(self):
        self.args.repos = ['deps', 'podified-ci-testing']
        main._validate_args(self.args, '', '')

    def test_ceph_and_podified_dev(self):
        self.args.repos = ['current-podified-dev', 'ceph']
        self.args.output_path = main.DEFAULT_OUTPUT_PATH
        main._validate_args(self.args, '', '')

    def test_deps_and_podified_dev(self):
        self.args.repos = ['deps', 'current-podified-dev']
        self.assertRaises(main.InvalidArguments, main._validate_args,
                          self.args, '', '')

    def test_current_and_tripleo(self):
        self.args.repos = ['current', 'current-podified']
        self.assertRaises(main.InvalidArguments, main._validate_args,
                          self.args, '', '')

    def test_deps_and_podified_allowed(self):
        self.args.repos = ['deps', 'current-podified']
        main._validate_args(self.args, '', '')

    def test_invalid_distro(self):
        self.args.distro = 'Jigawatts 1.21'
        self.assertRaises(main.InvalidArguments, main._validate_args,
                          self.args, '', '')

    def test_invalid_stream(self):
        self.args.output_path = main.DEFAULT_OUTPUT_PATH
        self.args.stream = True
        self.assertRaises(main.InvalidArguments, main._validate_args,
                          self.args, 'CentOS 8', '8')

    def test_invalid_no_stream(self):
        self.args.output_path = main.DEFAULT_OUTPUT_PATH
        self.args.stream = False
        self.args.no_stream = True
        self.assertRaises(main.InvalidArguments, main._validate_args,
                          self.args, 'CentOS 8 Stream', '8')

    def test_validate_distro_repos(self):
        self.assertTrue(main._validate_distro_repos(self.args))

    def test_validate_distro_repos_fedora_podified_dev(self):
        self.args.distro = 'fedora'
        self.args.repos = ['current-podified-dev']
        self.assertRaises(main.InvalidArguments, main._validate_distro_repos,
                          self.args)
