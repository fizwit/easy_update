#!/usr/bin/env python3

import re
import sys
import json
import argparse
import requests
from framework import FrameWork
from updateexts import UpdateExts
from pep508 import Pep508
from pep508_parser import parser

__version__ = '2.2.2'
__date__ = 'June 27, 2024'
__maintainer__ = 'John Dey jfdey@fredhutch.org'


"""
EasyUpdate performs package version updating for EasyBuild
easyconfig files. Automates the updating of version information for R,
Python and bundles that extend R and Python. Package version information
is updated for modules in exts_list. Use language specific APIs for resolving
current version for each package.
"""

""" 

2.2.2 refactor pypi_requires_dist to use pep508 pareser.  This will allow for much more
    reliable parsing of package dependencies.  The pep508 parser is used to evaluate the
    output of the parser.

    pkg['meta']['requires'] is a list of lists.  The first element is the package name
    and the second element is the type of dependency.  This is used to track where the
    package was requested from.  This is useful when updating packages.  The package
    name is used to search for the package in the exts_list.  The type of dependency
    is used to determine if the package is a 'Depends', 'Imports', or 'LinkingTo' type.

    Command line flags have changed to use '--exts-' as a prefix. The use of '--update' is
    over used. Need to explicitly request the type of update; --exts-update-r or --exts-update-python
    this might change again after integrating the EB framework.

    Updating Python is still very broken.  Should update to use pyproject.toml. 

2.2.1 Sept 2021 Explicitly request type of update via cli flags:  --update_python_exts, --update_R_exts
    remove detect_language() from framework
    Pillow ~= pillow
    Was only implemented for R, and the Python side was broken. 

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
    """extend UpdateExts class to update package names from CRAN and Biocondutor
    """
    def __init__(self, args, eb):
        self.verbose = args.verbose
        self.debug = args.debug
        self.exts_search_cran = args.exts_search_cran

        self.bioc_data = {}
        self.dotGraph = {}
        self.name = eb.name
        self.depend_exclude = ['R', 'base', 'compiler', 'datasets', 'graphics',
                               'grDevices', 'grid', 'methods', 'parallel',
                               'splines', 'stats', 'stats4', 'tcltk', 'tools',
                               'utils', ]
        self.dep_types = ['Imports', 'Depends', 'LinkingTo']
        if eb.biocver:
            self.read_bioconductor_packages(eb.biocver)
        else:
            print('WARNING: BioCondutor local_biocver is not defined. Bioconductor will not be searched')
        if args.exts_description_r or args.exts_search_cran:
            self.exts_description(eb.exts_list)
            self.printDotGraph()
        else:
            UpdateExts.__init__(self, args, eb, 'R')
            self.updateexts()
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
        pkg['info'] = cran_info
        if self.exts_search_cran:
            self.print_meta(cran_info)
        pkg['meta']['version'] = cran_info['Version']
        if u'License' in cran_info and u'Part of R' in cran_info[u'License']:
            return 'base package'
        pkg['meta']['requires'] = []
        for dep_type in self.dep_types:
            if dep_type in cran_info:
                for pkg_name in cran_info[dep_type].keys():
                    if pkg_name not in self.depend_exclude:
                        pkg['meta']['requires'].append([pkg_name, dep_type])
        return 'ok'

    def get_bioc_info(self, pkg):
        """Extract Dependencies from BioCondutor json metadata
        Example:
        bioc_data['pkg']['Depends']
                    [u'R (>= 2.10)', u'BiocGenerics (>= 0.3.2)', u'utils']
        interesting fields from BioCoductor:
        bioc_data['pkg']['Depends', 'Imports', 'LinkingTo', 'Biobase', 'graphics', 'URL']
        """
        status = 'ok'
        if pkg['name'] in self.bioc_data:
            pkg['meta']['version'] = self.bioc_data[pkg['name']]['Version']
            for dep_type in self.dep_types:
                if dep_type in self.bioc_data[pkg['name']]:
                    dep_list = [re.split('[ (><=,]', s)[0] for s in self.bioc_data[pkg['name']][dep_type]]
                    for dep in dep_list:
                        pkg['meta']['requires'].append([dep, dep_type])
        else:
            status = "not found"
        return status

    def print_depends(self, pkg):
        """ used for debugging """
        for p, method in pkg['meta']['requires']:
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

    def exts_description(self, exts_list):
        """ print library description from CRAN
            CRAN "Description" is multiline,
            build DOT type dependancy list
        """
        ext_list_len = len(exts_list)
        ext_counter = 1
        for ext in exts_list:
            if isinstance(ext, tuple):
                pkg = {'name': ext[0], 'version': ext[1], 'meta': {}}
            else:
                continue
            status = self.get_package_info(pkg)
            counter = '[{}, {}]'.format(ext_list_len, ext_counter)
            if status == "not found":
                ext_description = 'Package Not Found in CRAN'
                print('{:10} {}-{} : {}'.format(counter, pkg['name'], pkg['version'], ext_description))
            else:
                ext_description = pkg['info']['Title']
                print('{:10} {}-{} : {}'.format(counter, pkg['name'], pkg['version'], ext_description))
                self.dotGraph[str(pkg['name'])] = pkg
            ext_counter += 1

    def printDotGraph(self):
        print("digraph {} {{".format(self.name))
        print('{};'.format(self.name))
        for p in self.dotGraph.keys():
            print('"{}";'.format(p))
        for p in self.dotGraph.keys():
            print('"{}" -> "{}";'.format(self.name, p))
            for dep, method in self.dotGraph[p]['meta']['requires']:
                print('"{}" -> "{}";'.format(p, dep))
        print("}")


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
        self.debug = args.debug
        self.pkg_dict = None
        self.dep_types = ['requires_dist']
        self.python_version = None
        self.pep508 = Pep508()
        
        if args.exts_search_pypi:
            self.exts_search_pypi = args.exts_search_pypi
            self.get_pypi_project({'name': args.exts_search_pypi, 'version': ""})
        else:
            self.exts_search_pypi = None
            (nums) = eb.pyver.split('.')
            self.python_version = "%s.%s" % (nums[0], nums[1])
            UpdateExts.__init__(self, args, eb, 'Python')
            # Python >3.3 has additional built in modules
            self.depend_exclude = ['argparse', 'asyncio', 'typing', 'sys'
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
        if self.exts_search_pypi:
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
        """ process the requires_dist from Pypi. The requires_dist is a list. Evaluate each item
            with pep508_evaluator.  If the item is True, add the package name to the list of dependencies.
        """
        if requires is None:
            return []
        depends_on = []
        if self.debug:
            print(f' == {name} requires: {requires}', file=sys.stderr)
        for require in requires:
            try:
                parsed = parser.parse(require)
            except Exception:
                print(f' ** {name} Invaild PEP 508 Requires: {require}', file=sys.stderr)
                continue
            pkg_name = parsed[0]
            if self.pep508.eval_508(parsed) and pkg_name not in depends_on:
                depends_on.append(pkg_name)
        return depends_on

    def get_pypi_release(self, pkg, project):
        """if source dist is not available from pypi search
        the release for a wheel file.
        """
        status = 'not found'
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
            cplist = ['cp36', 'cp37', 'cp38', 'cp39']
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
        pkg['meta']['requires'] = []
        if 'requires_dist' in project['info']:
            requires = project['info']['requires_dist']
            dep_list = self.pypi_requires_dist(pkg['name'], requires)
            for dep in dep_list:
                pkg['meta']['requires'].append([dep, 'requires'])
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

    def exts_description(self, exts_list):
        """ Print library description from PyPi metadata for each extsion in exts_list """
        ext_list_len = len(exts_list)
        ext_counter = 1
        for ext in exts_list:
            if isinstance(ext, tuple):
                pkg = {'name': ext[0], 'version': ext[1], 'meta': {}}
            else:
                continue
            status = self.get_package_info(pkg)
            ext_description = pkg['meta']['summary']
            counter = '[{}, {}]'.format(ext_list_len, ext_counter)
            print('{:10} {}-{} : {}'.format(counter, pkg['name'], pkg['version'], ext_description))
            ext_counter += 1


def main():
    """ main """
    parser = argparse.ArgumentParser(description='Update EasyConfig exts_list')

    parser.add_argument('--version', action='version', version='%(prog)s ' + 
                        __version__ + '  ' + __date__)
    parser.add_argument('-v', '--verbose', dest='verbose', required=False, 
                        action='store_true',
                        help='Verbose; print lots of extra stuff')
    parser.add_argument('--debug', required=False, action='store_true',
                        help='set log level to debug, (default: false)')
    parser.add_argument('--exts-description-r', action='store_true', 
                        help='Output descrption for libraries in exts_list')
    parser.add_argument('--exts-update-r', nargs='?', help='Update R extensions')
    parser.add_argument('--exts-search-cran', action='store_true', help='output libray metadata from CRAN/BioConductor')
    parser.add_argument('--exts-update-python', nargs='?', help='update Python extensions')
    parser.add_argument('--exts-search-pypi', nargs='?', help='output library metadata from PyPi')
    parser.add_argument('--exts-description-python', action='store_true', help='Output descrption for libraries in exts_list')
    #parser.add_argument('easyconfig', metavar='EasyConfig file', help='EasyConfig file')
    args = parser.parse_args()

    if args.exts_update_r or args.exts_description_r:
        eb = FrameWork(args, args.exts_update_r, 'R')
        UpdateR(args, eb)
    elif args.exts_update_python or args.exts_description_python:
        eb = FrameWork(args, args.exts_update_python, 'Python')
        UpdatePython(args, eb)
    elif args.exts_search_pypi:
        print(f"Search PyPi for {args.exts_search_pypi}")
        UpdatePython(args, None)


if __name__ == '__main__':
    main()
