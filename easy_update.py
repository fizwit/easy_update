#!/usr/bin/env python

import re
import os
import sys
import argparse
import imp
import requests
from framework import FrameWork
from updateexts import UpdateExts
from packaging.markers import Marker, UndefinedEnvironmentName

# from pprint import pprint

"""
EasyUpdate performs package version updating for EasyBuild
easyconfig files. Automates the updating of version information for R,
Python and bundles that extend R and Python. Package version information
is updated for modules in exts_list. Use language specific APIs for resolving
current version for each package.
"""

""" Release Notes
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

__version__ = '2.0.8.3'
__maintainer__ = 'John Dey jfdey@fredhutch.org'
__date__ = 'Sep 25, 2019'


class UpdateR(UpdateExts):
    """extend UpdateExts class to update package names from CRAN and BioCondutor
    """
    def __init__(self, args, eb):
        UpdateExts.__init__(self, args, eb)
        self.debug = False
        self.bioc_data = {}
        self.depend_exclude = ['R', 'base', 'compiler', 'datasets', 'graphics',
                               'grDevices', 'grid', 'methods', 'parallel',
                               'splines', 'stats', 'stats4', 'tcltk', 'tools',
                               'utils', ]
        try:
            self.biocver = args.biocver
        except NameError:
            self.biocver = None
        if not self.biocver:
            try:
                self.biocver = eb.biocver
            except (AttributeError, NameError):
                self.biocver = None
                print('BioCondutor version: biocver not set')
        if self.biocver:
            self.read_bioconductor_packages()
        self.updateexts()
        if not self.search_pkg:
            eb.print_update('R', self.exts_processed)

    def read_bioconductor_packages(self):
        """ read the Bioconductor package list into bio_data dict
        """
        base_url = 'https://bioconductor.org/packages/json/%s' % self.biocver
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
        self.debug = False 
        self.pkg_dict = None
        self.not_found = 'not found'
        if eb:
            (nums) = eb.version.split('.')
        else:
            (nums) = args.pyver.split('.')
        self.python_version = "%s.%s" % (nums[0], nums[1])
        pymajor = int(nums[0])
        pyminor = int(nums[1])
        # Python >3.3 has additional built in modules
        if pymajor == 3 and pyminor > 3:
            self.depend_exclude += ['argparse', 'asyncio', 'typing', 'sys'
                                    'functools32', 'enum34', 'future', 'configparser']
        if self.search_pkg:
            self.check_package(self.sea_pkg) 
        else:
            self.updateexts()
        if not self.search_pkg:
            eb.print_update('Python', self.exts_processed)

    def get_pypi_pkg_data(self, pkg, version=None):
        """
        return meta data from PyPi.org
        """
        if version:
            req = 'https://pypi.org/pypi/%s/%s/json' % (pkg['name'], version)
        else:
            req = 'https://pypi.org/pypi/%s/json' % pkg['name']
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

    def print_meta(self, meta):
        """ print 'info' dict from pypi.org

        """
        if self.meta:
            for key in meta:
                if key == 'description':
                    print("%s: %s" % (key, meta[key][1:60]))
                elif key == 'requires_dist':
                    print('%s:' % 'requires_dist')
                    for req in meta[key]:
                        print("   %s" % req)
                else:
                    print("%s: %s" % (key, meta[key]))

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
                )
        for require in requires:
            pkg_name = re.split('[ ><=!;(]', require)[0]
            if self.is_processed(pkg={'name': pkg_name, 'from': name, 'type': 'dep'}):
                continue
            # check for Markers and process
            markers = require.split(';')
            marker_env = True
            if len(markers) > 1:
                marker_obj = Marker(markers[1])
                for env in envs:
                    marker_env = marker_obj.evaluate(environment=env)
                    if self.debug:
                        print(' - "{}": "{}" ({})'.format(pkg_name, markers[1],
                                                          marker_env))
                    if marker_env:
                        break
            if marker_env and pkg_name not in depends_on:
                depends_on.append(pkg_name)
        return depends_on

    def get_pypi_release(self, pkg, project):
        """if source dist is not available from pypi search
        the release for a wheel file.
        """
        status = self.not_found
        new_version = pkg['meta']['version']
        for ver in project['releases'][new_version]:
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
        project = self.get_pypi_pkg_data(pkg)
        if project == 'not found':
            return 'not found'
        pkg['meta'].update(project['info'])
        if 'requires_dist' in project['info']:
            requires = project['info']['requires_dist']
            pkg['meta']['requires'] = self.pypi_requires_dist(pkg['name'], requires)
        status = self.get_pypi_release(pkg, project)
        if self.meta:
            self.print_meta(project['info'])
            sys.exit(0)
        return status

    def output_module(self, pkg):
        """Python version
        this method is used with --search, otherwise, framework is used
        """
        pkg_fmt = self.indent + "('{}', '{}', {{\n"
        item_fmt = self.indent + self.indent + "'%s': %s,\n"
        if 'spec' in pkg:
            output = pkg_fmt.format(pkg['name'], pkg['version'])
            for item in pkg['spec'].keys():
                output += item_fmt % (item, pkg['spec'][item])
            output += self.indent + "}),"
        else:
            output = "('{}', '{}),".format(pkg['name'], pkg['version'])
        return output

def help():
    print("usage: easy_update  EasyConfig.eb [flags]")
    print("easy_update Updates ext_list information of EasyBuild"),
    print(" EasyConfig files")
    print("easy_update works with R, Python and R-bioconductor"),
    print(" EasyConfig files")
    print("  --verbose  diplay status for each package")
    print("  --add [filename]  filename contains list of package"),
    print(" names to add")
    sys.exit()


def main():
    """ main """
    parser = argparse.ArgumentParser(description='Update EasyConfig extslist')

    parser.add_argument('--version', action='version',
                        version='%(prog)s ' + __version__)
    parser.add_argument(
        '-v', '--verbose', dest='verbose', required=False, action='store_true',
        help='Verbose; print lots of extra stuff, (default: false)')
    parser.add_argument('--rver', dest='rver', required=False, action='store',
                        help='Set R version (major.minor) example 3.6')
    bioc_help = 'Set BioConductor version (major.minor) example 3.9. '
    bioc_help += 'Use with --rver'
    parser.add_argument('--biocver', dest='biocver', required=False,
                        action='store', help=bioc_help)
    parser.add_argument('--pyver', dest='pyver', required=False, action='store',
                        help='Set Python version [2.7 or 3.6]')
    search_help = 'Search for single package. requires --rver or --pyver'
    parser.add_argument('--search', dest='search_pkg', required=False, action='store',
                        help=search_help)
    parser.add_argument('--meta', dest='meta', required=False, action='store_true',
                        help='output select meta data keys from Pypi, if used with ' +
                             'verbose all metadata is output (default: false)')
    parser.add_argument('easyconfig', nargs='?')
    args = parser.parse_args()

    args.lang = None
    eb = None
    if args.easyconfig:
        eb = FrameWork(args)
        args.lang = eb.name
        if eb.name == 'R':
            args.rver = eb.version 
            args.biocver = eb.biocver
        if eb.name == 'Python':
            args.pyver = eb.version
    if args.search_pkg:
        if args.rver:
            args.lang = 'R'
        elif args.pyver:
            args.lang = 'Python'

    if (not args.search_pkg) and (not args.easyconfig):
        print('If no EasyConfig is given, a module name must be ' +
              'specified with --search pkg_name')
        sys.exit()

    if not args.lang:
        print('Could not determine language [R, Python]')
        sys.exit(1)

    if args.lang == 'R':
        UpdateR(args, eb)
    elif args.lang == 'Python':
        UpdatePython(args, eb)


if __name__ == '__main__':
    main()
