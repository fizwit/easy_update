#!/usr/bin/env python

"""
   updateexts.py
   EasyUpdate performs package version updating for EasyBuild
   easyconfig files. Automates the updating of version information for R,
   Python and bundles that extend R and Python. Package version information
"""

import logging

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
        self.language = eb.language
        self.ext_counter = 0
        self.pkg_updated = 0
        self.pkg_new = 0
        self.pkg_duplicate = 0
        self.indent_n = 4
        self.indent = ' ' * self.indent_n
        self.ext_list_len = 1
        self.dep_exts = eb.dep_exts
        self.checking = list()  # prevent infinite loops while resolving dependencies
        self.exts_processed = list()
        self.exts_orig = eb.exts_list
        self.interpolate = {'name': eb.name, 'namelower': eb.name.lower(),
                            'version': eb.version}
        self.dep_exts_list = [sub_list[0] for sub_list in self.dep_exts]

    def processed(self, pkg):
        """
            Save package name to list of Processed packages.
        """
        dup_pkg = dict(pkg)
        if pkg['action'] == 'add':
            self.ext_counter += 1
        self.exts_processed.append(dup_pkg)

    def print_status(self, pkg):
        """ print one line status for each package if --verbose
        updated July 2018
        """
        if pkg['action'] == 'update':
            version = f"{pkg['orig_version']} -> {pkg['version']}"
        elif pkg['action'] == 'add':
            from_pkg, method = pkg['from']
            version = f"{pkg['version']} {method} from {from_pkg}"
        else:
            version = pkg['version']
        name = pkg['name']
        action = f"({pkg['action']})"
        merge = name + ' : ' + version
        if len(name) > 25 and len(name) + len(version) < 53:
            print(f"{merge:53} {action:>12} [{self.ext_list_len}, {self.ext_counter}]")
        elif len(version) > 25 and len(name) + len(version) < 53:
            print(f"{merge:>53} {action:>12} [{self.ext_list_len}, {self.ext_counter}]")
        else:
            tmpl = f"{name:>25} : {version:<25} {action:>12} [{self.ext_list_len}, {self.ext_counter}]"
            print(tmpl)

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
          - 'processed' package appears twice
          - 'deplicate' package is a dependency of another package
          - 'remove' not compatible, wrong OS, not supported version
        """
        logging.debug('check_package: %s from: %s', pkg['name'], pkg['from'])
        if self.is_processed(pkg):
            return
        status = self.get_package_info(pkg)
        logging.debug('check_package: %s pkg data: %s', pkg['name'], pkg)
        if status in ["error", 'not found']:
            if pkg['from'] is None:
                pkg['action'] = 'keep'
                self.processed(pkg)
                return
            else:
                print(f" Warning: {pkg['name']} is dependency from {pkg['from']}, but can't be found!")
                return

        if pkg['from']:
           pkg['action'] = 'add'
           self.pkg_new += 1
           self.ext_counter += 1
        else:
            if pkg['orig_version']:
                pkg['action'] = 'update'
                self.pkg_updated += 1
                if len(pkg) == 3:
                    if 'checksums' in pkg[2]:
                        del pkd[2]['checksums']
            else:
                pkg['action'] = 'keep'
        if 'requires' in pkg['meta'] and pkg['meta']['requires'] is not None:
            self.checking.append(pkg['name'])
            logging.debug('%s: requires: %s', pkg['name'], pkg['meta']['requires'])
            for depend, method in pkg['meta']['requires']:
                if depend not in self.depend_exclude:
                    dep_pkg = {'name': depend,
                               'from': [pkg['name'], method],
                               'version': 'x',
                               'spec': {}, 'meta': {}, 'level': pkg['level']+1}
                    self.check_package(dep_pkg)
        self.processed(pkg)
        if self.verbose:
            self.print_status(pkg)

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
            if pkg['action'] in ['processed', 'duplicate']:
                self.processed(pkg)

        if self.verbose:
            self.stats()

    def printDotGraph(self, dotGraph):
        print(f"digraph {self.name} {{")
        print(f"{self.name};")
        for p in dotGraph.keys():
            print(f'"{p}";')
        for p in dotGraph.keys():
            print(f'"{self.name}" -> "{p}";')
            for dep, method in dotGraph[p]['meta']['requires']:
                print(f'"{p}" -> "{dep}";')
        print("}")

    def stats(self):
        print(f"== Updated Packages: {self.pkg_updated}")
        print(f"== New Packages: {self.pkg_new}")
        print(f"== Dropped Packages: {self.pkg_duplicate}")
        print(f"== Total Packages: {self.ext_list_len}")
