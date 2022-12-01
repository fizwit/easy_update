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
Easyconfig templates module that provides templating that can
be used within an Easyconfig file.

:author: Stijn De Weirdt (Ghent University)
:author: Fotis Georgatos (Uni.Lu, NTUA)
:author: Kenneth Hoste (Ghent University)
"""
import re
import platform


# derived from easyconfig, but not from ._config directly
TEMPLATE_NAMES_EASYCONFIG = [
    ('module_name', "Module name"),
    ('nameletter', "First letter of software name"),
    ('toolchain_name', "Toolchain name"),
    ('toolchain_version', "Toolchain version"),
    ('version_major_minor', "Major.Minor version"),
    ('version_major', "Major version"),
    ('version_minor', "Minor version"),
]
# derived from EasyConfig._config
TEMPLATE_NAMES_CONFIG = [
    'bitbucket_account',
    'github_account',
    'name',
    'parallel',
    'version',
    'versionsuffix',
    'versionprefix',
]
# lowercase versions of ._config
TEMPLATE_NAMES_LOWER_TEMPLATE = "%(name)slower"
TEMPLATE_NAMES_LOWER = [
    'name',
    'nameletter',
]
# values taken from the EasyBlock before each step
TEMPLATE_NAMES_EASYBLOCK_RUN_STEP = [
    ('builddir', "Build directory"),
    ('installdir', "Installation directory"),
]
# software names for which to define <pref>ver and <pref>shortver templates
TEMPLATE_SOFTWARE_VERSIONS = [
    # software name, prefix for *ver and *shortver
    ('CUDA', 'cuda'),
    ('CUDAcore', 'cuda'),
    ('Java', 'java'),
    ('Perl', 'perl'),
    ('Python', 'py'),
    ('R', 'r'),
]
# template values which are only generated dynamically
TEMPLATE_NAMES_DYNAMIC = [
    ('arch', "System architecture (e.g. x86_64, aarch64, ppc64le, ...)"),
    ('mpi_cmd_prefix', "Prefix command for running MPI programs (with default number of ranks)"),
    ('cuda_compute_capabilities', "Comma-separated list of CUDA compute capabilities, as specified via "
     "--cuda-compute-capabilities configuration option or via cuda_compute_capabilities easyconfig parameter"),
    ('cuda_cc_space_sep', "Space-separated list of CUDA compute capabilities"),
    ('cuda_cc_semicolon_sep', "Semicolon-separated list of CUDA compute capabilities"),
    ('cuda_sm_comma_sep', "Comma-separated list of sm_* values that correspond with CUDA compute capabilities"),
    ('cuda_sm_space_sep', "Space-separated list of sm_* values that correspond with CUDA compute capabilities"),
]

# constant templates that can be used in easyconfigs
TEMPLATE_CONSTANTS = [
    # source url constants
    ('APACHE_SOURCE', 'https://archive.apache.org/dist/%(namelower)s',
     'apache.org source url'),
    ('BITBUCKET_SOURCE', 'https://bitbucket.org/%(bitbucket_account)s/%(namelower)s/get',
     'bitbucket.org source url (namelower is used if bitbucket_account easyconfig parameter is not specified)'),
    ('BITBUCKET_DOWNLOADS', 'https://bitbucket.org/%(bitbucket_account)s/%(namelower)s/downloads',
     'bitbucket.org downloads url (namelower is used if bitbucket_account easyconfig parameter is not specified)'),
    ('CRAN_SOURCE', 'https://cran.r-project.org/src/contrib',
     'CRAN (contrib) source url'),
    ('FTPGNOME_SOURCE', 'https://ftp.gnome.org/pub/GNOME/sources/%(namelower)s/%(version_major_minor)s',
     'http download for gnome ftp server'),
    ('GITHUB_SOURCE', 'https://github.com/%(github_account)s/%(name)s/archive',
     'GitHub source URL (namelower is used if github_account easyconfig parameter is not specified)'),
    ('GITHUB_LOWER_SOURCE', 'https://github.com/%(github_account)s/%(namelower)s/archive',
     'GitHub source URL (lowercase name, namelower is used if github_account easyconfig parameter is not specified)'),
    ('GNU_SAVANNAH_SOURCE', 'https://download-mirror.savannah.gnu.org/releases/%(namelower)s',
     'download.savannah.gnu.org source url'),
    ('GNU_SOURCE', 'https://ftpmirror.gnu.org/gnu/%(namelower)s',
     'gnu.org source url'),
    ('GOOGLECODE_SOURCE', 'http://%(namelower)s.googlecode.com/files',
     'googlecode.com source url'),
    ('LAUNCHPAD_SOURCE', 'https://launchpad.net/%(namelower)s/%(version_major_minor)s.x/%(version)s/+download/',
     'launchpad.net source url'),
    ('PYPI_SOURCE', 'https://pypi.python.org/packages/source/%(nameletter)s/%(name)s',
     'pypi source url'),  # e.g., Cython, Sphinx
    ('PYPI_LOWER_SOURCE', 'https://pypi.python.org/packages/source/%(nameletterlower)s/%(namelower)s',
     'pypi source url (lowercase name)'),  # e.g., Greenlet, PyZMQ
    ('R_SOURCE', 'https://cran.r-project.org/src/base/R-%(version_major)s',
     'cran.r-project.org (base) source url'),
    ('SOURCEFORGE_SOURCE', 'https://download.sourceforge.net/%(namelower)s',
     'sourceforge.net source url'),
    ('XORG_DATA_SOURCE', 'https://xorg.freedesktop.org/archive/individual/data/',
     'xorg data source url'),
    ('XORG_LIB_SOURCE', 'https://xorg.freedesktop.org/archive/individual/lib/',
     'xorg lib source url'),
    ('XORG_PROTO_SOURCE', 'https://xorg.freedesktop.org/archive/individual/proto/',
     'xorg proto source url'),
    ('XORG_UTIL_SOURCE', 'https://xorg.freedesktop.org/archive/individual/util/',
     'xorg util source url'),
    ('XORG_XCB_SOURCE', 'https://xorg.freedesktop.org/archive/individual/xcb/',
     'xorg xcb source url'),

    # TODO, not urgent, yet nice to have:
    # CPAN_SOURCE GNOME KDE_I18N XCONTRIB DEBIAN KDE GENTOO TEX_CTAN MOZILLA_ALL

    # other constants
    ('SHLIB_EXT',  'extension for shared libraries'),
]

extensions = ['tar.gz', 'tar.xz', 'tar.bz2', 'tgz', 'txz', 'tbz2', 'tb2', 'gtgz', 'zip', 'tar', 'xz', 'tar.Z']
for ext in extensions:
    suffix = ext.replace('.', '_').upper()
    TEMPLATE_CONSTANTS += [
        ('SOURCE_%s' % suffix, '%(name)s-%(version)s.' + ext, "Source .%s bundle" % ext),
        ('SOURCELOWER_%s' % suffix, '%(namelower)s-%(version)s.' + ext, "Source .%s bundle with lowercase name" % ext),
    ]
for pyver in ('py2.py3', 'py2', 'py3'):
    if pyver == 'py2.py3':
        desc = 'Python 2 & Python 3'
        name_infix = ''
    else:
        desc = 'Python ' + pyver[-1]
        name_infix = pyver.upper() + '_'
    TEMPLATE_CONSTANTS += [
        ('SOURCE_%sWHL' % name_infix, '%%(name)s-%%(version)s-%s-none-any.whl' % pyver,
         'Generic (non-compiled) %s wheel package' % desc),
        ('SOURCELOWER_%sWHL' % name_infix, '%%(namelower)s-%%(version)s-%s-none-any.whl' % pyver,
         'Generic (non-compiled) %s wheel package with lowercase name' % desc),
    ]

