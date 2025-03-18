#!/usr/bin/env python3

import re
import sys
import requests
import logging
from updateexts import UpdateExts
from annotate import Annotate
from Bioconductor_packages import Bioconductor_packages
from pprint import pprint

__version__ = '2.2.3'
__date__ = 'March 11, 2025'
__maintainer__ = 'John Dey jfdey@fredhutch.org'


"""
updateR.py
EasyUpdate performs package version updating for EasyBuild
easyconfig files. Automates the updating of version information for R,

"""

logging.basicConfig(format='%(levelname)s [%(filename)s:%(lineno)-4d] %(message)s',
                    level=logging.WARN)
# logging.getLogger().setLevel(logging.DEBUG)


class UpdateR(UpdateExts, Annotate):
    """extend UpdateExts class to update package names from CRAN and Biocondutor
    """
    def __init__(self, argument, operation, verbose, eb):
        self.verbose = verbose
        self.dotGraph = {}
        self.name = eb.name
        self.depend_exclude = ['R', 'base', 'compiler', 'datasets', 'graphics',
                               'grDevices', 'grid', 'methods', 'parallel',
                               'splines', 'stats', 'stats4', 'tcltk', 'tools',
                               'utils', ]
        self.dep_types = ['Depends', 'Imports', 'LinkingTo']

        if eb.biocver:
            self.bioc = Bioconductor_packages(eb.biocver)
        else:
            print('WARNING: BioCondutor local_biocver is not defined. Bioconductor will not be searched')
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
            #   for pkg in self.exts_processed:
            #       print(f"    ('{pkg['name']}', '{pkg['version']}'),")
            #   print(f"Total packages: {self.ext_counter}")
            eb.print_update('R', self.exts_processed)

    def get_cran_package(self, pkg):
        """ MD5sum, Description, Package, releases[]
        normalize meta data from CRAN. Imports, Depends, LinkingTo are mapped to 'requires'
        """
        cran_list = "http://crandb.r-pkg.org/"
        resp = requests.get(url=cran_list + pkg['name'])
        if resp.status_code != 200:
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

    def is_processed(self, pkg):
        """ check if package has been previously processed
            if package exists AND is in the original exts_lists
                Mark as 'duplicate'
        updated July 2018
        """
        action = None
        name = pkg['name']
        if name in self.dep_exts_list:
            action = 'duplicate'
        else:
            for p_pkg in self.exts_processed:
                if name == p_pkg['name']:
                    action = 'processed'
                    break
        if not action and name in self.checking:
            action = 'duplicate-x'
        if action:
            if pkg['from'] is None:
                self.pkg_duplicate += 1
                self.ext_counter -= 1
                pkg['action'] = action
                if self.verbose:
                    self.print_status(pkg)
            return True
        else:
            return False

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

    def output_module(self, pkg):
        """ print module information for exts_list """
        return "%s('%s', '%s'),".format(self.indent, pkg['name'], pkg['version'])

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
