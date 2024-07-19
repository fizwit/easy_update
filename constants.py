#
# Copyright 2013-2022 Ghent University
#
# This file is part of EasyBuild,
# originally created by the HPC team of Ghent University (http://ugent.be/hpc/en),
# with support of Ghent University (http://ugent.be/hpc),
# the Flemish Supercomputer Centre (VSC) (https://www.vscentrum.be),
# Flemish Research Foundation (FWO) (http://www.fwo.be/en)
# and the Department of Economy, Science and Innovation (EWI) (http://www.ewi-vlaanderen.be/en).
#
# https://github.com/easybuilders/easybuild
#
# EasyBuild is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation v2.
#
# EasyBuild is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with EasyBuild.  If not, see <http://www.gnu.org/licenses/>.
#

"""
Easyconfig constants module that provides all constants that can
be used within an Easyconfig file.

:author: Stijn De Weirdt (Ghent University)
:author: Kenneth Hoste (Ghent University)
"""
import os
import sys
import platform

try:
    import distro
    HAVE_DISTRO = True
except ImportError as err:
    sys.stderr.write("Failed to import 'distro' Python module: %s".format(err))
    sys.exit()

EXTERNAL_MODULE_MARKER = 'EXTERNAL_MODULE'

# from easybuild.tools.systemtools import get_os_type, KNOWN_ARCH_CONSTANTS
KNOWN_ARCH_CONSTANTS = ('aarch64', 'ppc64le', 'riscv64', 'x86_64')

def get_os_version():
    """Determine system version."""

    os_version = None
    if not os_version and HAVE_DISTRO:
        os_version = distro.version()
    return os_version

def get_os_name():
    """
    Determine system name, e.g., 'redhat' (generic), 'centos', 'debian', 'fedora', 'suse', 'ubuntu',
    'red hat enterprise linux server', 'SL' (Scientific Linux), 'opensuse', ...
    """
    os_name = None

    # platform.linux_distribution was removed in Python 3.8,
    # see https://docs.python.org/2/library/platform.html#platform.linux_distribution
    if hasattr(platform, 'linux_distribution'):
        # platform.linux_distribution is more useful, but only available since Python 2.6
        # this allows to differentiate between Fedora, CentOS, RHEL and Scientific Linux (Rocks is just CentOS)
        os_name = platform.linux_distribution()[0].strip()

    # take into account that on some OSs, platform.distribution returns an empty string as OS name,
    # for example on OpenSUSE Leap 15.2
    if not os_name and HAVE_DISTRO:
        # distro package is the recommended alternative to platform.linux_distribution,
        # see https://pypi.org/project/distro
        os_name = distro.name()

    if not os_name and os.path.exists(ETC_OS_RELEASE):
        os_release_txt = read_file(ETC_OS_RELEASE)
        name_regex = re.compile('^NAME="?(?P<name>[^"\n]+)"?$', re.M)
        res = name_regex.search(os_release_txt)
        if res:
            os_name = res.group('name')

    os_name_map = {
        'red hat enterprise linux server': 'RHEL',
        'red hat enterprise linux': 'RHEL',  # RHEL8 has no server/client
        'scientific linux sl': 'SL',
        'scientific linux': 'SL',
        'suse linux enterprise server': 'SLES',
    }

    if os_name:
        return os_name_map.get(os_name.lower(), os_name)
    else:
        return UNKNOWN


def get_os_type():
    """Determine system type, e.g., 'Linux', 'Darwin', 'Java'."""
    os_type = platform.system()
    if len(os_type) > 0:
        return os_type
    else:
        raise SystemToolsException("Failed to determine system name using platform.system().")

def _get_arch_constant():
    """
    Get value for ARCH constant.
    """
    arch = platform.uname()[4]

    # macOS on Arm produces 'arm64' rather than 'aarch64'
    if arch == 'arm64':
        arch = 'aarch64'

    if arch not in KNOWN_ARCH_CONSTANTS:
        sys.stderr.write("Using unknown value for ARCH constant: %s", arch)

    return arch


# constants that can be used in easyconfig
EASYCONFIG_CONSTANTS = {
    'ARCH': (_get_arch_constant(), "CPU architecture of current system (aarch64, x86_64, ppc64le, ...)"),
    'EXTERNAL_MODULE': (EXTERNAL_MODULE_MARKER, "External module marker"),
    'HOME': (os.path.expanduser('~'), "Home directory ($HOME)"),
    'OS_TYPE': (get_os_type(), "System type (e.g. 'Linux' or 'Darwin')"),
    'OS_NAME': (get_os_name(), "System name (e.g. 'fedora' or 'RHEL')"),
    'OS_VERSION': (get_os_version(), "System version"),
    'SYS_PYTHON_VERSION': (platform.python_version(), "System Python version (platform.python_version())"),
    'SYSTEM': ({'name': 'system', 'version': 'system'}, "System toolchain"),

    'OS_PKG_IBVERBS_DEV': (('libibverbs-dev', 'libibverbs-devel', 'rdma-core-devel'),
                           "OS packages providing ibverbs/infiniband development support"),
    'OS_PKG_OPENSSL_BIN': (('openssl'),
                           "OS packages providing the openSSL binary"),
    'OS_PKG_OPENSSL_LIB': (('libssl', 'libopenssl'),
                           "OS packages providing openSSL libraries"),
    'OS_PKG_OPENSSL_DEV': (('openssl-devel', 'libssl-dev', 'libopenssl-devel'),
                           "OS packages providing openSSL developement support"),
    'OS_PKG_PAM_DEV': (('pam-devel', 'libpam0g-dev'),
                       "OS packages providing Pluggable Authentication Module (PAM) developement support"),
}
