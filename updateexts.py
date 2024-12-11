#!/usr/bin/env python

import re
import os
import sys
import argparse
import requests
from framework import FrameWork
# from pprint import pprint
# from pprint import pformat

"""
EasyUpdate performs package version updating of exts_list for EasyBuild
easyconfig files. Automates the the updating of version information for R,
Python and bundles that extend R and Python. Use language specific APIs for resolving
current versions. (CRAN, Pypi, Bioconductor)
"""

""" Release Notes
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
  Pypi package names are changing from dashes to underscores
   ipython-genutils -> ipython_genutils
   jupyter-core -> jupyter_core
   jipython-genutils -> ipython_genutils
   pyncacl -> PyNaCl

1.3.0 July 2018
  update to use pypi.org JSON API
  Project API:  GET /pypi/<project_name>/json
  Release API: GET /pypi/<project_name>/<version>/json
"""

__version__ = '2.0.7'
__maintainer__ = 'John Dey jfdey@fredhutch.org'
__date__ = 'Aug 15, 2019'


class UpdateExts:
    """
    """
    def __init__(self, verbose, eb):
        """
        """
        self.verbose = verbose
        self.debug = False
        self.language = eb.language
        self.ext_counter = 0
        self.pkg_update = 0
        self.pkg_new = 0
        self.pkg_duplicate = 0
        self.indent_n = 4
        self.indent = ' ' * self.indent_n
        self.ext_list_len = 1
        self.dep_exts = eb.dep_exts
        self.checking = list()  # pytest -> attrs -> pytest
        self.exts_processed = list()
        self.exts_orig = eb.exts_list
        self.interpolate = {'name': eb.name, 'namelower': eb.name.lower(),
                            'version': eb.version}
        self.dep_exts_lower = [sub_list[0].lower() for sub_list in self.dep_exts]

    def is_processed(self, pkg):
        """ check if package has been previously processed
            if package exists AND is in the original exts_lists
                Mark as 'duplicate'
        updated July 2018
        """
        names = []
        names.append(pkg['name'])
        if 'spec' in pkg and 'modulename' in pkg['spec']:
            names.append(pkg['spec']['modulename'])
        if '-' in pkg['name']:
            names.append(pkg['name'].replace('-', '_'))
        found = False
        for name in names:
            if name.casefold() in self.dep_exts_lower:
                found = True
            elif name in self.checking:
                found = True
            else:
                for p_pkg in self.exts_processed:
                    if 'spec' in p_pkg and 'modulename' in p_pkg['spec']:
                        modulename = p_pkg['spec']['modulename']
                    else:
                        modulename = ''
                    if (str(name) == str(p_pkg['name'])) or (name == modulename):
                        found = True
                        break
        if found:
            if not pkg['from']:
                pkg['action'] = 'duplicate'
                self.pkg_duplicate += 1
                self.ext_counter -= 1
                self.processed(pkg)
                if self.verbose:
                    self.print_status(pkg)
                    return True
        return found

    def processed(self, pkg):
        """ save Processed packages
        save a normalize version of package name to <exts_search> for Python
        updated July 2018
        """
        pkg['processed'] = True
        pkg2 = dict(pkg)
        self.exts_processed.append(pkg2)

    def print_status(self, pkg):
        """ print one line status for each package if --verbose
        updated July 2018
        """
        if pkg['action'] == 'update':
            version = '{} -> {}'.format(pkg['orig_ver'], pkg['version'])
        elif pkg['action'] == 'add':
            from_pkg, method = pkg['from']
            version = '{} {} from {}'.format(pkg['version'], method, from_pkg)
        else:
            version = pkg['version']
        name = pkg['name']
        action = '(%s)' % pkg['action']
        merge = name + ' : ' + version
        if len(name) > 25 and len(name) + len(version) < 53:
            print('{:53} {:>12} [{}, {}]'.format(merge, action,
                  self.ext_list_len, self.ext_counter))
        elif len(version) > 25 and len(name) + len(version) < 53:
            print('{:>53} {:>12} [{}, {}]'.format(merge, action,
                  self.ext_list_len, self.ext_counter))
        else:
            tmpl = '{:>25} : {:<25} {:>12} [{}, {}]'
            print(tmpl.format(name, version, action, self.ext_list_len, self.ext_counter))

    def check_package(self, pkg):
        """query package authority [Pypi, CRAN, Bio] to get the latest version
        information for a package. This is the heart of the program.

        input: pkg{}
        check that all dependencies are meet for each package.
        check_package can be called recursively.
        pkg['from'] is used to track recursion.
          - None module is from source file
          - not None:  Name of package that depends from
        pkg['action'] What action will be take to exts_list.
          - 'add'; new package
          - 'keep'; no update required
          - 'update'; version change
          - 'duplicate' package appears twice
          - 'remove' not compatible, wrong OS, not supported version
        """
        if self.debug:
            sys.stderr.write('check_package: {} from: {}\n'.format(pkg['name'], pkg['from']))
        if self.is_processed(pkg):
            return
        self.checking.append(pkg['name'])
        status = self.get_package_info(pkg)
        if status in ["error", 'not found']:
            if pkg['from'] is None:
                pkg['action'] = 'keep'
                self.processed(pkg)
                return
            else:
                msg = " Warning: {} is dependency from {}, but can't be found!"
                print(msg.format(pkg['name'],pkg['from']))
                return
        if status == 'remove':
            msg = " removing {} "
            pkg['action'] = 'remove'
            self.processed(pkg)
            print(msg.format(pkg['name']))
            return

        if 'version' in pkg['meta']:
            version = pkg['meta']['version']
        else:
            version = pkg['version']
        if pkg['version'] == version:
            pkg['action'] = 'keep'
        else:
            pkg['orig_ver'] = pkg['version']
            pkg['version'] = pkg['meta']['version']
            if pkg['from'] is None:
                pkg['action'] = 'update'
                self.pkg_update += 1
                if len(pkg) == 3:
                    if 'checksums' in pkg[2]:
                        del pkd[2]['checksums']
            else:
                if self.debug:
                    print('check_package - add {} from {}'.format(pkg['name'],pkg['from']))
                pkg['action'] = 'add'
                self.pkg_new += 1

        if 'requires' in pkg['meta'] and pkg['meta']['requires'] is not None:
            if self.debug:
                print(f'{pkg["name"]} requires: {pkg["meta"]["requires"]}', file=sys.stderr)
            for depend, method in pkg['meta']['requires']:
                if depend not in self.depend_exclude:
                    dep_pkg = {'name': depend,
                               'from': [pkg['name'], method],
                               'mothod': method,
                               'version': 'x',
                               'spec': {}, 'meta': {}, 'level': pkg['level']+1}
                    self.check_package(dep_pkg)
        # if self.search_pkg:
        #     output = self.output_module(pkg)
        #     print(output)
        if self.verbose:
            self.print_status(pkg)
        if pkg['action'] == 'add':
            self.ext_counter += 1

    def updateexts(self):
        """Loop through exts_list and check which packages need to be updated.
        this is an external method for the class
        """
        self.ext_list_len = len(self.exts_orig)
        for ext in self.exts_orig:
            self.ext_counter += 1
            if isinstance(ext, tuple):
                name = ext[0] % self.interpolate
                version = ext[1] % self.interpolate
                pkg = {'name': name, 'version': version,
                       'from': None,
                       'level': 0, 'meta': {}}
                if len(ext) > 2:
                    pkg['spec'] = ext[2]
                else:
                    pkg['spec'] = {}
                pkg['meta'] = {}
                self.check_package(pkg)
            else:
                pkg = {'name': ext, 'from': 'base'}
            if self.language == 'Python':
                self.check_download_filename(pkg)
            if pkg['action'] != 'duplicate':
                self.processed(pkg)

        if self.verbose:
            self.stats()

    def exts_description(self):
        """ Print library description from CRAN metadata for each extension in exts_list.

        This method iterates over the exts_orig list and retrieves the package information for each extension.
        It then prints the package name, version, and description based on the selected programming language.

        Args:
            None

        Returns:
            None
        """
        for pkg in self.exts_orig:
            status = get_package_info(pkg)
            print("{}".format(pkg[0]))
            if self.language== 'Python':
                ext_description = pkg['meta']['summary']
            elif self.language== 'R':
                ext_description = pkg['meta']['info']['Description']
            merge = pkg['name'] + ' : ' + pkg['version']
            counter = '[{}, {}]'.format(self.ext_list_len, self.ext_counter)
            print('{:10} {:53} {}'.format(counter, merge, ext_description))

    def printDotGraph(self, dotGraph):
        print("digraph {} {{".format(self.name))
        print('{};'.format(self.name))
        for p in dotGraph.keys():
            print('"{}";'.format(p))
        for p in dotGraph.keys():
            print('"{}" -> "{}";'.format(self.name, p))
            for dep, method in dotGraph[p]['meta']['requires']:
                print('"{}" -> "{}";'.format(p, dep))
        print("}")

    def stats(self):
        sys.stderr.write("Updated Packages: %d\n" % self.pkg_update)
        sys.stderr.write("New Packages: %d\n" % self.pkg_new)
        sys.stderr.write("Dropped Packages: %d\n" % self.pkg_duplicate)

    def get_package_info(self, pkg):
        pass

