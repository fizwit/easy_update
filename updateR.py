#!/usr/bin/env python3

import sys
import requests
import logging
from updateexts import UpdateExts
from annotate import Annotate
from bioconductor_packages import Bioconductor_packages

logger = logging.getLogger()

__version__ = '2.2.3'
__date__ = 'March 11, 2025'
__maintainer__ = 'John Dey jfdey@fredhutch.org'


"""
updateR.py
EasyUpdate performs package version updating for EasyBuild
easyconfig files. Automates the updating of version information for R,

"""


class UpdateR(UpdateExts, Annotate):
    """extend UpdateExts class to update package names from CRAN and Biocondutor
    """
    def __init__(self, argument, operation, verbose, eb):
        self.verbose = verbose
        self.dotGraph = {}
        self.name = eb.name
        self.exts_processed_normalized = []  # only used for Python packages
        self.depend_exclude = ['R', 'base', 'compiler', 'datasets', 'graphics',
                               'grDevices', 'grid', 'methods', 'parallel',
                               'splines', 'stats', 'stats4', 'tcltk', 'tools',
                               'utils', ]
        self.dep_types = ['Depends', 'Imports', 'LinkingTo']

        self.bioc = Bioconductor_packages(eb.biocver, verbose)
        if operation == 'search_cran':
            pass
            #  display_cran_meta(argument)
        elif operation == 'description':
            self.exts_description(eb.exts_list)
            self.printDotGraph(self.dotGraph)
        elif operation == 'annotate':
            print(f'Annotate {eb.easyconfig} Argument: {argument}')
            UpdateExts.__init__(self, verbose, eb)
            Annotate.__init__(self, argument, verbose, self.exts_orig, self.dep_exts)
            self.create_markdown()
        elif operation == 'update':
            UpdateExts.__init__(self, verbose, eb)
            self.updateexts()
            print(f"Total packages: {self.ext_counter}")
            eb.print_update('R', self.exts_processed)

    def get_cran_package(self, pkg):
        """ MD5sum, Description, Package, releases[]
        normalize meta data from CRAN. Imports, Depends, LinkingTo are mapped to 'requires'
        """
        cran_list = "http://crandb.r-pkg.org/"
        resp = requests.get(url=cran_list + pkg['name'])
        if 200 < resp.status_code or resp.status_code >= 300:
            return "not found"
        cran_info = resp.json()
        pkg['info'] = cran_info
        if cran_info['Version'] != pkg['version']:
            pkg['orig_version'] = pkg['version']
            pkg['version'] = cran_info['Version']
        else:
            pkg['orig_version'] = None
        if u'License' in cran_info and u'Part of R' in cran_info[u'License']:
            return 'base package'
        if 'URL' in cran_info:
            pkg['url'] = cran_info['URL']
        if 'Title' in cran_info:
            pkg['Title'] = cran_info['Title']
        pkg['meta'] = {}
        pkg['meta']['requires'] = []
        for dep_type in self.dep_types:
            if dep_type in cran_info:
                for pkg_name in cran_info[dep_type].keys():
                    if pkg_name not in self.depend_exclude:
                        pkg['meta']['requires'].append([pkg_name, dep_type])
        return 'ok'

    def display_cran_meta(self, pkg_name):
        """ display metadata from CRAN
        --search-cran <pkg_name>
        """
        print("Search CRAN for %s" % pkg_name)
        pkg = {'name': pkg_name, 'version': ""}
        status = self.get_cran_package(pkg)
        if status == 'not found':
            sys.exit(1)
        self.print_meta(pkg['pkg_name']['info'])

    def print_depends(self, pkg):
        """ used for debugging """
        for p, method in pkg['meta']['requires']:
            if p not in self.depend_exclude:
                print("%20s : requires %s" % (pkg['name'], p))

    def get_package_info(self, pkg):
        """R version, check CRAN and BioConductor for version information
        """
        logging.debug('get_package_info: %s' % pkg['name'])
        pkg['meta']['requires'] = []
        status = self.bioc.get_bioc_package(pkg)
        if status == 'not found':
            status = self.get_cran_package(pkg)
        if logging.DEBUG >= logging.root.level:
            self.print_depends(pkg)
        return status

    def normalize_name(self, name):
        """ Normalize package is not required for R packages"""
        return name

    def get_package_url(self, pkg):
        """ Return URL and Description from CRAN or Biocondutor """
        status = self.bioc.get_bioc_package(pkg)
        if status == 'ok':
            url = f"https://www.bioconductor.org/packages/release/bioc/html/{pkg['name']}.html"
            if 'Title' in pkg:
                return url, pkg['Title']
            else:
                print(f"Title {pkg} not found in Bioconductor")
                return url, 'Description Not Found in Bioconductor'

        status = self.get_cran_package(pkg)
        if status == 'ok':
            url = f"https://cran.r-project.org/web/packages/{pkg['name']}/index.html"
            if 'Title' in pkg:
                return url, pkg['Title']
            else:
                return url, 'Description Not Found in CRAN'
        return 'not found', 'Package Not Found'

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

    def is_not_used(self):
        pass

    def exts_description(self, exts_list):
        """ print library description from CRAN
            CRAN "Description" is multiline,
            build DOT type dependancy list
        """
        ext_list_len = len(exts_list)
        ext_counter = 1
        pkg = {}
        for ext in exts_list:
            if isinstance(ext, tuple):
                pkg = {'name': ext[0], 'version': ext[1], 'meta': {}}
            else:
                continue
            project = self.get_package_info(pkg)
            if project == "not found":
                ext_description = 'Package Not Found in CRAN'
            else:
                self.dotGraph[str(pkg['name'])] = pkg
                ext_description = pkg['info']['Title']
            counter = f"[{ext_list_len}, {ext_counter}]"
            print(f"{counter:10} {pkg['name']}-{pkg['version']} : {ext_description}")
            ext_counter += 1
