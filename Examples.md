## Easy_Update Command Line Examples
Easy_Update was designed to update exts_list package information for 
 updating EasyBuild configuration files. In the process of developing tools
to resolve package depenencies many command options have been added
to easy_update. Lookup and output of metadata from package authorities
CRAN and Pypi are supported. Command line options for examining meta
data only work with the **--search** option. Search takes a single
arguement which is a package name.  Search must be qualified with either
**--pyver X.x** or **--rver X.x --biocver X.x**

 * Command line option [--tree](python_tree) with Python
 * Command line option [--meta](cran_meta) with R
 * Command line option [--meta](pypi_meta) with Python
 * Command line option [--Meta](pypi_Meta) with Python
 
#### Print Dependency Tree<a name="python_tree"></a>
Option --tree only works with Python at this time. Tree outputs an
inverted dependency tree for a Python package.

```
./easy_update.py --tree --pyver 2.7 --search pytest
    py
    six
        certifi
    setuptools
    attrs
    atomicwrites
    pluggy
    funcsigs
        scandir
    pathlib2
    more-itertools
    colorama
    hypothesis
    nose
        chardet
        idna
                cryptography
                flaky
                pretend
            pyOpenSSL
            ipaddress
            PySocks
        urllib3
        win-inet-pton
    requests
    mock
pytest
```

#### Search CRAN and print metadata for package<a name="cran_meta"></a>
Uppercase option --Meta does not resolve dependencies.


<pre><code>./easy_update.py --Meta --rver 3.5 --biocver 3.8 --search Rcpp

VignetteBuilder: knitr
Author: Dirk Eddelbuettel, Romain Francois, JJ Allaire, Kevin Ushey, Qiang Kou,
Nathan Russell, Douglas Bates and John Chambers
Version: 1.0.0
releases: []
NeedsCompilation: yes
Date/Publication: 2018-11-07 20:00:03 UTC
MailingList: Please send questions and comments regarding Rcpp to
rcpp-devel@lists.r-forge.r-project.org
Description: The 'Rcpp' package provides R functions as well as C++ classes which
offer a seamless integration of R and C++. Many R data types and objects can be
mapped back and forth to C++ equivalents which facilitates both writing of new
code as well as easier integration of third-party libraries. Documentation
about 'Rcpp' is provided by several vignettes included in this package, via the
'Rcpp Gallery' site at <http://gallery.rcpp.org>, the paper by Eddelbuettel and
Francois (2011, <doi:10.18637/jss.v040.i08>), the book by Eddelbuettel (2013,
<doi:10.1007/978-1-4614-6868-4>) and the paper by Eddelbuettel and Balamuta (2018,
<doi:10.1080/00031305.2017.1375990>); see 'citation("Rcpp")' for details.
Repository: CRAN
RoxygenNote: 6.0.1
Title: Seamless R and C++ Integration
Packaged: 2018-11-06 03:02:42.98448 UTC; edd
Date: 2018-11-05
crandb_file_date: 2018-11-07 20:02:33
License: GPL (>= 2)
Package: Rcpp
URL: http://www.rcpp.org, http://dirk.eddelbuettel.com/code/rcpp.html,
https://github.com/RcppCore/Rcpp
Suggests: {u'RUnit': u'*', u'rmarkdown': u'*', u'rbenchmark': u'*', u'inline': u'*', u'pinp': u'*', u'pkgKitten': u'>= 0.1.2', u'knitr': u'*'}
date: 2018-11-07T19:00:03+00:00
Maintainer: Dirk Eddelbuettel <edd@debian.org>
Imports: {u'utils': u'*', u'methods': u'*'}
MD5sum: 47ef1ad37fd75d19e8404b31e58ba994
Depends: {u'R': u'>= 3.0.0'}
BugReports: https://github.com/RcppCore/Rcpp/issues
    ('Rcpp', '1.0.0'),
</pre></code>

#### Search Pypi.org print Metadata and exita name="pypi_meta"></a>
Lowercase option --meta only prints select fields from PyPi and will
resolve dependencies.


```
./easy_update.py --meta --pyver 2.7 --search setuptools
    ('certifi', '2018.11.29', {
        'level': 1,
        'source_urls': ['https://pypi.io/packages/source/c/certifi'],
    }),
filename: certifi-2018.11.29.tar.gz
url: https://files.pythonhosted.org/packages/55/54/3ce77783acba5979ce16674fc98b1920d00b01d337cfaaf5db22543505ed/certifi-2018.11.29.tar.gz
requires_dist: None
summary: Python package for providing Mozilla's CA Bundle.
requires_python:
classifiers: [u'Development Status :: 5 - Production/Stable', u'Intended Audience :: Developers', u'License :: OSI Approved :: Mozilla Public License 2.0 (MPL 2.0)', u'Natural Language :: English', u'Programming Language :: Python', u'Programming Language :: Python :: 2', u'Programming Language :: Python :: 2.6', u'Programming Language :: Python :: 2.7', u'Programming Language :: Python :: 3', u'Programming Language :: Python :: 3.3', u'Programming Language :: Python :: 3.4', u'Programming Language :: Python :: 3.5', u'Programming Language :: Python :: 3.6', u'Programming Language :: Python :: 3.7']
    ('setuptools', '40.8.0', {
        'level': 0,
        'source_urls': ['https://pypi.io/packages/source/s/setuptools'],
    }),
filename: setuptools-40.8.0.zip
url: https://files.pythonhosted.org/packages/c2/f7/c7b501b783e5a74cf1768bc174ee4fb0a8a6ee5af6afa92274ff964703e0/setuptools-40.8.0.zip
requires_dist: [u"certifi (==2016.9.26) ; extra == 'certs'", u"wincertstore (==0.2) ; (sys_platform=='win32') and extra == 'ssl'"]
summary: Easily download, build, install, upgrade, and uninstall Python packages
requires_python: >=2.7,!=3.0.*,!=3.1.*,!=3.2.*,!=3.3.*
classifiers: [u'Development Status :: 5 - Production/Stable', u'Intended Audience :: Developers', u'License :: OSI Approved :: MIT License', u'Operating System :: OS Independent', u'Programming Language :: Python :: 2', u'Programming Language :: Python :: 2.7', u'Programming Language :: Python :: 3', u'Programming Language :: Python :: 3.4', u'Programming Language :: Python :: 3.5', u'Programming Language :: Python :: 3.6', u'Programming Language :: Python :: 3.7', u'Topic :: Software Development :: Libraries :: Python Modules', u'Topic :: System :: Archiving :: Packaging', u'Topic :: System :: Systems Administration', u'Topic :: Utilities']
```

#### --Meta print all metadata and exit<a name="pypi_Meta"></a>
```
./easy_update.py --Meta --pyver 2.7 --search pytest

maintainer:
docs_url: None
requires_python: >=2.7, !=3.0.*, !=3.1.*, !=3.2.*, !=3.3.*
maintainer_email:
keywords: test,unittest
package_url: https://pypi.org/project/pytest/
author: Holger Krekel, Bruno Oliveira, Ronny Pfannschmidt, Floris Bruynooghe, Brianna Laugher, Florian Bruhin and others
author_email:
download_url:
project_urls: {u'Source': u'https://github.com/pytest-dev/pytest', u'Tracker': u'https://github.com/pytest-dev/pytest/issues', u'Homepage': u'https://docs.pytest.org/en/latest/'}
platform: unix
version: 4.3.0
description: .. image:: https://docs.pytest.org/en/latest/_static/pytest1.png
   :target: https://docs.pytest.org/en/latest/
   :align: center
   :alt: pytest


------

.. image:: https://img.shields.io/pypi/v/pytest.svg
    :target: https://pypi.org/project/pytest/

.. image:: https://img.shields.io/conda/vn/conda-forge/pytest.svg
    :target: https://anaconda.org/conda-forge/pytest

.. image:: https://img.shields.io/pypi/pyversions/pytest.svg
    :target: https://pypi.org/project/pytest/

.. image:: https://codecov.io/gh/pytest-dev/pytest/branch/master/graph/badge.svg
    :target: https://codecov.io/gh/pytest-dev/pytest
    :alt: Code coverage Status

.. image:: https://travis-ci.org/pytest-dev/pytest.svg?branch=master
    :target: https://travis-ci.org/pytest-dev/pytest

.. image:: https://ci.appveyor.com/api/projects/status/mrgbjaua7t33pg6b?svg=true
    :target: https://ci.appveyor.com/project/pytestbot/pytest

.. image:: https://img.shields.io/badge/code%20style-black-000000.svg
    :target: https://github.com/ambv/black

.. image:: https://www.codetriage.com/pytest-dev/pytest/badges/users.svg
    :target: https://www.codetriage.com/pytest-dev/pytest

The ``pytest`` framework makes it easy to write small tests, yet
scales to support complex functional testing for applications and libraries.

An example of a simple test:

.. code-block:: python

    # content of test_sample.py
    def inc(x):
        return x + 1


    def test_answer():
        assert inc(3) == 5


To execute it::

    $ pytest
    ============================= test session starts =============================
    collected 1 items

    test_sample.py F

    ================================== FAILURES ===================================
    _________________________________ test_answer _________________________________

        def test_answer():
    >       assert inc(3) == 5
    E       assert 4 == 5
    E        +  where 4 = inc(3)

    test_sample.py:5: AssertionError
    ========================== 1 failed in 0.04 seconds ===========================


Due to ``pytest``'s detailed assertion introspection, only plain ``assert`` statements are used. See `getting-started <https://docs.pytest.org/en/latest/getting-started.html#our-first-test-run>`_ for more examples.


Features
--------

- Detailed info on failing `assert statements <https://docs.pytest.org/en/latest/assert.html>`_ (no need to remember ``self.assert*`` names);

- `Auto-discovery
  <https://docs.pytest.org/en/latest/goodpractices.html#python-test-discovery>`_
  of test modules and functions;

- `Modular fixtures <https://docs.pytest.org/en/latest/fixture.html>`_ for
  managing small or parametrized long-lived test resources;

- Can run `unittest <https://docs.pytest.org/en/latest/unittest.html>`_ (or trial),
  `nose <https://docs.pytest.org/en/latest/nose.html>`_ test suites out of the box;

- Python 2.7, Python 3.4+, PyPy 2.3, Jython 2.5 (untested);

- Rich plugin architecture, with over 315+ `external plugins <http://plugincompat.herokuapp.com>`_ and thriving community;


Documentation
-------------

For full documentation, including installation, tutorials and PDF documents, please see https://docs.pytest.org/en/latest/.


Bugs/Requests
-------------

Please use the `GitHub issue tracker <https://github.com/pytest-dev/pytest/issues>`_ to submit bugs or request features.


Changelog
---------

Consult the `Changelog <https://docs.pytest.org/en/latest/changelog.html>`__ page for fixes and enhancements of each version.


License
-------

Copyright Holger Krekel and others, 2004-2019.

Distributed under the terms of the `MIT`_ license, pytest is free and open source software.

.. _`MIT`: https://github.com/pytest-dev/pytest/blob/master/LICENSE



release_url: https://pypi.org/project/pytest/4.3.0/
description_content_type:
downloads: {u'last_month': -1, u'last_week': -1, u'last_day': -1}
requires_dist: [u'py (>=1.5.0)', u'six (>=1.10.0)', u'setuptools', u'attrs (>=17.4.0)', u'atomicwrites (>=1.0)', u'pluggy (>=0.7)', u'funcsigs ; python_version < "3.0"', u'pathlib2 (>=2.2.0) ; python_version < "3.6"', u'more-itertools (<6.0.0,>=4.0.0) ; python_version <= "2.7"', u'more-itertools (>=4.0.0) ; python_version > "2.7"', u'colorama ; sys_platform == "win32"', u"hypothesis (>=3.56) ; extra == 'testing'", u"nose ; extra == 'testing'", u"requests ; extra == 'testing'", u'mock ; (python_version == "2.7") and extra == \'testing\'']
project_url: https://pypi.org/project/pytest/
classifiers: [u'Development Status :: 6 - Mature', u'Intended Audience :: Developers', u'License :: OSI Approved :: MIT License', u'Operating System :: MacOS :: MacOS X', u'Operating System :: Microsoft :: Windows', u'Operating System :: POSIX', u'Programming Language :: Python :: 2', u'Programming Language :: Python :: 2.7', u'Programming Language :: Python :: 3', u'Programming Language :: Python :: 3.4', u'Programming Language :: Python :: 3.5', u'Programming Language :: Python :: 3.6', u'Programming Language :: Python :: 3.7', u'Topic :: Software Development :: Libraries', u'Topic :: Software Development :: Testing', u'Topic :: Utilities']
bugtrack_url: None
name: pytest
license: MIT license
summary: pytest: simple powerful testing with Python
home_page: https://docs.pytest.org/en/latest/
```