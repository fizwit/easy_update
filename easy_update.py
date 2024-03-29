#!/usr/bin/env python

import re
import os
import sys
import json
import argparse
import requests
from framework import FrameWork
from updateexts import UpdateExts
from packaging.markers import Marker, UndefinedEnvironmentName

if sys.version_info < (3,):
    sys.stderr.write("ERROR: Python 3 required, found %s\n" % sys.version.split(' ')[0])
    sys.exit(1)

__version__ = '2.2.0'
__date__ = 'Aug 11, 2021'
__maintainer__ = 'John Dey jfdey@fredhutch.org'


"""
EasyUpdate performs package version updating for EasyBuild
easyconfig files. Automates the updating of version information for R,
Python and bundles that extend R and Python. Package version information
is updated for modules in exts_list. Use language specific APIs for resolving
current version for each package.
"""

""" Release Notes
2.2.1 Sept 2021 Explicitly request type of update via cli flags:  --update_python_exts, --update_R_exts 
    remove detect_language() from framework
    Pillow ~= pillow

2.2.0 Aug 11, 2020 - Dig deep to find all dependent Python libraries. Every dependency needs to be check
 to determine if it contains Python modules. Inspect every dependency for PythonBundle or PythonPackage,
 easyblock type.

2.1.5 July 8, 2021 - fix bug in find_easyconfig_paths 
   Add additonal headers 'SOURCE_WHL',  'SOURCE_PY3_WHL'; from caspar@SURFsara

2.1.4 May 20, 2021 - remove requirment for local_biocver. Issue a warning if local_biocver is
                     not set.
2.1.3 Feb 3, 2021 - bug Fix
      AttributeError: 'FrameWork' object has no attribute 'base_path'

2.1.2 Jan 28, 2021 - support constant OS_PKG_OPENSSL_DEV
2.1.1 Jan 6, 2021 - clean up requirements.txt with pigar

2.1.0 Nov 22, 2020 - Major changes to framework. See framework.py for more details.

2.0.8.10 July 29 minor bug fixes
2.0.8.9 July 6, 2020 CNVkit, dependencies on both R and Python. fix bug so easy_update could
        not determine language of exts_list. Fix base_path to find to of easyconfig
        directory tree. Did not reconize R-bundel-Bioconductor as an R depenency, fixed.
2.0.8.8 June 9, 2020 fix R package dependency lookups. Support for "local_biocver"
2.0.8.7 Jan 26, 2020 Fix multi file dependency to support bundles
2.0.8.6 Oct 1, 2019 PR #17 merged from ccoulombe
    R modules are not necessarily installed with extensions. Fix the AttributeError when
    the R EasyConfig file does not contains exts_list.

    PR #18 from ccoulombe  - Using importlib.util.module_from_spec(None) is not possible,
    therefore using types.ModuleType() is the solution.


2.0.8.5 Oct 1, 2019 Bug Fix: File "./easy_update.py", line 105, in __init__
    UpdateExts.__init__(self, args, eb)
  File "updateexts.py", line 91, in __init__
    if eb.dep_exts:
AttributeError: 'NoneType' object has no attribute 'dep_exts'

2.0.8.4 Sept 26, 2019 Bug Fix: File "./easy_update.py", line 378, in get_pypi_release
    for ver in project['releases'][new_version]:
    NameError: name 'new_version' is not defined

2.0.8.3 Sept 25, 2019 Bug Fix: File "updateexts.py", line 91, in __init__
    if eb.dep_exts:
    AttributeError: 'NoneType' object has no attribute 'dep_exts'
AttributeError: 'NoneType' object has no attribute 'dep_exts'

2.0.8.2 Sept 20, 2019 - more bug fixes for --search.  Fixed dependency issues
    when checking agaist easyconfigs with the search feature.

2.0.8.1 Sep 18, 2019 Bug fix - output_module was broken when framework was
    seperated from updateexts

2.0.8 Sep 13, 2019 refactor pypi_requires_dist. Use the Marker tool
    pkg_resources to check Python dependencies.
    keep track of package dependencies and display from which dist a package was requested
    use with --verbose and Python:  Example verbose output

```
              R.methodsS3 : 1.7.1                           (keep) [692, 226]
                     R.oo : 1.22.0                          (keep) [692, 227]
                 jsonlite : 1.6 from httr                    (add) [692, 228]
                      sys : 3.3 from askpass                 (add) [692, 229]
                  askpass : 1.1 from openssl                 (add) [692, 230]
                  openssl : 1.4.1 from httr                  (add) [692, 231]
                     httr : 1.4.1 from cgdsr                 (add) [692, 232]
                    cgdsr : 1.2.10 -> 1.3.0               (update) [692, 233]
                  R.utils : 2.8.0 -> 2.9.0                (update) [692, 234]
                 R.matlab : 3.6.2                           (keep) [692, 235]
                gridExtra : 2.3                             (keep) [692, 236]
                      gbm : 2.1.5                           (keep) [692, 237]
                  Formula : 1.2-3                           (keep) [692, 238]
```

    option --tree had been removed, the new "from" tracking is better.


2.0.7 Aug 15, 2019 framework is a module, remove from this file. Update
    to use new features of Framwork which were added to support easy_annotate.

2.0.6 July 9, 2019 easy_anotate read dependinces, add framework, pep8 issues
2.0.5 July 8, 2019 Only one flag for debugging metadata '--meta'.
    Used with --verbose all Metadata is output from Pypi. Try to fix package
    counter. Why was R Bioconductor broken?
2.0.4 Python issues, fixed bugs, but still not perfect
2.0.3 more issues with Pypi
2.0.2 fixed issue: could not open easyconfig if it was not in the present
   working directory.
2.0.1 2019.03.08 improve parse_pypi_requires to remove 'dev', 'tests' and
   'docs' related dependencies. Dependencies for pytest when fom 173 packages
   to 27. --Meta and --tree have been added as options to help with debugging
   Python dependencies.

2.0.0 2019-02-26 New feature to resolve dependent packages
   for R and Python bundles. Read exts_list for R and Python listed in
    dependencies. Refactor code into Two major classes: FrameWork and
    UpdateExts. Rename subclasses for for R and Python: UpdateR UpdatePython.
    This will help with migration into the EB FrameWork.
    Fix bug with pkg_update counter

1.3.2 2018-12-19 follow "LinkingTo" for BioConductor packages
   reported by Maxime Boissonneault

1.3.1 2018-11-28 fix bugs with pypi
  easy_update was adding incorrect package names from requests_dist.
  Verify package names and update easyconfig with name corrections.
  Package names from pypi.requests_dist are not always correct.
  Pypi Project names do not match package names
   ipython-genutils -> ipython_genutils
   jupyter-core -> jupyter_core
   jipython-genutils -> ipython_genutils
   pyncacl -> PyNaCl

1.3.0 July 2018
  update to use pypi.org JSON API
  Project API:  GET /pypi/<project_name>/json
  Release API: GET /pypi/<project_name>/<version>/json
"""


class UpdateR(UpdateExts):
    """extend UpdateExts class to update package names from CRAN and BioCondutor
    """
    def __init__(self, args, eb):
        UpdateExts.__init__(self, args, eb)
        print('processing: {}'.format(eb.name))
        self.debug = args.debug
        self.bioc_data = {}
        self.depend_exclude = ['R', 'base', 'compiler', 'datasets', 'graphics',
                               'grDevices', 'grid', 'methods', 'parallel',
                               'splines', 'stats', 'stats4', 'tcltk', 'tools',
                               'utils', ]
        if eb.biocver:
            self.read_bioconductor_packages(eb.biocver)
        else:
            print('WARNING: BioCondutor local_biocver is not defined. BioConductor will not be searched')
        self.updateexts()
        if not self.search_pkg:
            eb.print_update('R', self.exts_processed)

    def read_bioconductor_packages(self, biocver):
        """ read the Bioconductor package list into bio_data dict
        """
        base_url = 'https://bioconductor.org/packages/json/%s' % biocver
        bioc_urls = ['%s/bioc/packages.json' % base_url,
                     '%s/data/annotation/packages.json' % base_url,
                     '%s/data/experiment/packages.json' % base_url]
        for url in bioc_urls:
            resp = requests.get(url)
            if resp.status_code != 200:
                print('Error: %s %s' % (resp.status_code, url))
                sys.exit(1)
            self.bioc_data.update(resp.json())
            if self.debug:
                print('reading Bioconductor Package inf: %s' % url)
                pkgcount = len(self.bioc_data.keys())
                print('size: %s' % pkgcount)

    def get_cran_info(self, pkg):
        """ MD5sum, Description, Package, releases[]
        """
        cran_list = "http://crandb.r-pkg.org/"
        resp = requests.get(url=cran_list + pkg['name'])
        if resp.status_code != 200:
            return "not found"
        cran_info = resp.json()
        pkg['meta']['info'] = cran_info
        if self.meta:
            self.print_meta(cran_info)
        pkg['meta']['version'] = cran_info['Version']
        if u'License' in cran_info and u'Part of R' in cran_info[u'License']:
            return 'base package'
        pkg['meta']['requires'] = []
        if u"LinkingTo" in cran_info:
            pkg['meta']['requires'].extend(cran_info[u"LinkingTo"].keys())
        if u"Depends" in cran_info:
            pkg['meta']['requires'].extend(cran_info[u"Depends"].keys())
        if u"Imports" in cran_info:
            pkg['meta']['requires'].extend(cran_info[u"Imports"].keys())
        return 'ok'

    def get_bioc_info(self, pkg):
        """Extract <Depends> and <Imports> from BioCondutor json metadata
        Example:
        bioc_data['pkg']['Depends']
                    [u'R (>= 2.10)', u'BiocGenerics (>= 0.3.2)', u'utils']
        interesting fields from BioCoductor:
        bioc_data['pkg']['Depends', 'Imports', 'Biobase', 'graphics', 'URL']
        """
        status = 'ok'
        if pkg['name'] in self.bioc_data:
            pkg['meta']['version'] = self.bioc_data[pkg['name']]['Version']
            if 'LinkingTo' in self.bioc_data[pkg['name']]:
                pkg['meta']['requires'].extend(
                    [re.split('[ (><=,]', s)[0]
                     for s in self.bioc_data[pkg['name']]['LinkingTo']])
            if 'Depends' in self.bioc_data[pkg['name']]:
                pkg['meta']['requires'].extend(
                    [re.split('[ (><=,]', s)[0]
                     for s in self.bioc_data[pkg['name']]['Depends']])
            if 'Imports' in self.bioc_data[pkg['name']]:
                pkg['meta']['requires'].extend(
                    [re.split('[ (><=,]', s)[0]
                     for s in self.bioc_data[pkg['name']]['Imports']])
        else:
            status = "not found"
        return status

    def print_depends(self, pkg):
        """ used for debugging """
        for p in pkg['meta']['requires']:
            if p not in self.depend_exclude:
                print("%20s : requires %s" % (pkg['name'], p))

    def get_package_info(self, pkg):
        """R version, check CRAN and BioConductor for version information
        """
        if self.debug:
            print('get_package_info: %s' % pkg['name'])
        pkg['meta']['requires'] = []
        status = self.get_bioc_info(pkg)
        if status == 'not found':
            status = self.get_cran_info(pkg)
        if self.debug:
            self.print_depends(pkg)
        return status

    def print_meta(self, meta):
        """Display metadata from CRAN
        :rtype: None
        """
        self.is_not_used()
        for tag in meta:
            if tag == 'info':
                for md in meta['info']:
                    print("%s: %s" % (md, meta['info'][md]))
            else:
                print("%s: %s" % (tag, meta[tag]))

    def output_module(self, pkg):
       return "%s('%s', '%s')," % (self.indent, pkg['name'], pkg['version'])

    def is_not_used(self):
        pass


class UpdatePython(UpdateExts):
    """extend ExtsList class to update package names from PyPI
    Python Issues
       There are many small inconsistancies with PyPi which make it difficult
       to fully automate building of EasyConfig files.
       - dependancy checking - check for extra=='all'
       - pypi projects names do not always match module names and or file names
         project: liac-arff, module: arff,  file name: liac_arff.zip
    """
    def __init__(self, args, eb):
        UpdateExts.__init__(self, args, eb)
        self.debug = args.debug
        self.meta = args.pypimeta
        self.pkg_dict = None
        self.not_found = 'not found'
        (nums) = eb.pyver.split('.')
        self.python_version = "%s.%s" % (nums[0], nums[1])
        # Python >3.3 has additional built in modules
        self.depend_exclude += ['argparse', 'asyncio', 'typing', 'sys'
                                'functools32', 'enum34', 'future', 'configparser']
        self.updateexts()
        eb.print_update('Python', self.exts_processed)

    def get_pypi_project(self, pkg):
        """ Python PyPi project
        ['info']['classifiers']: 'audience', 'Topic'
        """
        req = 'https://pypi.org/pypi/%s/json' % pkg['name']
        resp = requests.get(req)
        if resp.status_code != 200:
            sys.stderr.write('{} not in PyPi'.format(pkg['name']))
            return 'not found'
        project = resp.json()
        if self.meta:
            self.print_meta(project)
        return project

    def get_pypi_pkg_data(self, pkg, version=None):
        """
        return meta data from PyPi.org)
        """
        req = 'https://pypi.org/pypi/%s/%s/json' % (pkg['name'], version)
        resp = requests.get(req)
        if resp.status_code != 200:
            msg = "API error: %s GET release %s\n"
            sys.stderr.write(msg % (resp.status_code, pkg['name']))
            return 'not found'
        project = resp.json()
        # verify that Project name is correct
        # projects names might differ from import names
        # sphinx -> Sphinx
        if pkg['name'] != project['info']['name']:
            if self.debug:
                print('Project name {} modulename {}\n'.format(
                      project['info']['name'], pkg['name']))
            if 'spec' in pkg:
                pkg['spec']['modulename'] = pkg['name']
            else:
                pkg['spec'] = {'modulename': pkg['name']}
            pkg['name'] = project['info']['name']
        return project

    def check_package_name(self, pkg_name):
        """
        verify that package name from EasyConfig
        matches package name from PyPi
        """
        pkg = {'name': pkg_name}
        response = self.get_pypi_pkg_data(pkg)
        if response == 'not found':
            return response
        else:
            return response['info']['name']

    def print_meta(self, project):
        """ print 'info' dict from pypi.org

        """
        if 'info' in project:
            info = project['info']
        else:
            return
        print("{}: {}".format(info['name'], info['version']))
        for key in info:
            if key == 'description':
                print("    %s: %s" % (key, info[key][1:60]))
            else:
                print('    {}: {}'.format(key, json.dumps(info[key], indent=4)))

    def pypi_requires_dist(self, name, requires):
        """ process the requires_dist from Pypi. remove packages that do not match the os
        and Python release. Return the edited list of dependancies. Format of output
        is a single list with only the package names.

        Note: the project name can be different from the 'package' name.

        Only add deps where "extra" == 'deps' or 'all'
        requires_dist: <name> <version>[; Environment Markers]

        use Marker from packaging to evaluate Markers.
        https://github.com/pypa/packaging/blob/master/docs/markers.rst

        EasyUpdate always installs the latest version of pakcages, so ignore
        version information for packages.
        input: 'numpy (>=1.7.1)'  output: 'numpy'
        """
        if requires is None:
            return []
        depends_on = []
        envs = ({'python_version': self.python_version, 'extra': 'deps'},
                {'python_version': self.python_version, 'extra': 'all'},
                {'python_version': self.python_version, 'extra': 'tests'},
                {'python_version': self.python_version, 'extra': 'doc'},
                {'python_version': self.python_version, 'extra': 'examples'},
                )
        for require in requires:
            pkg_name = re.split('[ ><=!;(]', require)[0]
            #print('checking: {}'.format(pkg_name))
            if self.is_processed(pkg={'name': pkg_name, 'from': name, 'type': 'dep'}):
                continue
            # check for Markers and process
            markers = require.split(';')
            if len(markers) > 1 and 'extra' in markers[1]:
                continue
            if pkg_name not in depends_on:
                depends_on.append(pkg_name)
        return depends_on

    def get_pypi_release(self, pkg, project):
        """if source dist is not available from pypi search
        the release for a wheel file.
        """
        status = self.not_found
        if 'version' in pkg['meta']:
            version = pkg['meta']['version']
        else:
            print('no version info! for {}'.format(pkg['name']))
        for ver in project['releases'][version]:
            if 'packagetype' in ver and ver['packagetype'] == 'sdist':
                pkg['meta']['url'] = ver['url']
                pkg['meta']['filename'] = ver['filename']
                status = 'ok'
                break
        # one last try to find package release data
        if status != 'ok':
            cplist = ['cp35', 'cp36', 'cp37']
            for rel in project['releases'][version]:
                if any(cver in rel['python_version'] for cver in cplist):
                    if 'manylinux' in rel['filename']:
                        pkg['meta'].update(rel)
                        status = 'ok'
                        break
        return status

    def get_package_info(self, pkg):
        """get version information from pypi.  If <pkg_name> is not processed
        seach pypi. pkg_name is now case sensitive and must match
        """
        project = self.get_pypi_project(pkg)
        if project == 'not found':
            return 'not found'
        pkg['meta'].update(project['info'])
        # new_version = pkg['meta']['version']
        status = self.get_pypi_release(pkg, project)

        if 'requires_dist' in project['info']:
            requires = project['info']['requires_dist']
            pkg['meta']['requires'] = self.pypi_requires_dist(pkg['name'], requires)
        return status

    def output_module(self, pkg):
        """Python version
        this method is used with --search, otherwise, framework is used
        """
        pkg_fmt = self.indent + "('{}', '{}', {{\n"
        item_fmt = self.indent + self.indent + "'%s': '%s',\n"
        if 'spec' in pkg:
            output = pkg_fmt.format(pkg['name'], pkg['version'])
            for item in pkg['spec'].keys():
                output += item_fmt % (item, pkg['spec'][item])
            output += self.indent + "}),"
        else:
            output = self.indent + "('{}', '{}'),".format(pkg['name'], pkg['version'])
        return output


def main():
    """ main """
    parser = argparse.ArgumentParser(description='Update EasyConfig exts_list')

    parser.add_argument('--version', action='version',
                        version='%(prog)s ' + __version__ + '  ' + __date__)
    parser.add_argument(
        '-v', '--verbose', dest='verbose', required=False, action='store_true',
        help='Verbose; print lots of extra stuff, (default: false)')
    parser.add_argument('--debug', required=False, action='store_true',
        help='set log level to debug, (default: false)')
    parser.add_argument('--pypi_meta', dest='pypimeta', action='store_true', required=False,
        help='Output PyPi metadata for module')
    parser.add_argument('--update-R-exts', type=str, metavar='R-Easyconfig', dest='r_eb',
        help='Update R extentions')
    parser.add_argument('--update-python-exts', type=str, metavar='Python-EasyConfig', dest='python_eb',
        help='Update Python extentions')
    args = parser.parse_args()

    if args.r_eb:
        print('R EasyConfig file: {}'.format(args.r_eb))
        eb = FrameWork(args, args.r_eb, 'R')
        UpdateR(args, eb)
    elif args.python_eb:
        print('filename: {}'.format(args.python_eb))
        eb = FrameWork(args, args.python_eb, 'Python')
        UpdatePython(args, eb)


if __name__ == '__main__':
    main()
