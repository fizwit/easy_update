#!/usr/bin/env python

import os
import sys
import argparse
import json
from datetime import date
from framework import FrameWork
import requests

"""
Easy_Annotate creates Markdown documentation from R and Python easyconfigs.
All exts_list packages are documented. If possible the annotation will link
each package to its project page.
"""

""" Release Notes
    2.0.4  python.get_package_url -convert to requests
    Python 3.x updates pkgs.keys()  change to list(pkgs)

    2.0.3 Improve dependent package searches for Python easyconfigs to include
    PythonPackages. framework has been updated to check the dependenices for any
    easyconfig with a version suffix of "Python-%(pyver)s". If found locate the
    easyconfig and add the exts_list to dependend packages. Following depenedencies
    will allow a more acurate package listing with hierarchical package structure. 
    Example: Python 3.7.4 -fh1 -> Python 3.7.4 -> pytest, matplotlib ... etc.

    2.0.2 use FrameWork class from easyupdate. Create single document from R and
    Python Packages. Read Dependent module to append exts_list packages, to
    create a single
    document to describe compound Modules.

    Version 2 create Markdown output

    Version 1.x create HTML output
"""

__author__ = "John Dey"
__version__ = "2.0.3"
__date__ = "Aug 15, 2019"
__email__ = "jfdey@fredhutch.org"


class ExtsList(object):
    """ Easy Anotate is a utilty program for documenting EasyBuild easyconfig
    files for R and Python. Easyconfig files for R and Python can have over
    a hundred modules in an ext_list.  This program creates
    html documentation of extension list.
    """

    def __init__(self, eb, verbose):
        self.debug = False
        self.verbose = verbose
        self.pkg_count = 0

        try:
            self.extension = eb.dep_exts
        except NameError:
            self.extension = []
        self.extension.extend(eb.exts_list)
        self.biocver = None
        self.toolchain = eb.toolchain
        self.pkg_name = eb.name + '-' + eb.version + '-'
        self.pkg_name += eb.toolchain['name'] + '-'
        self.pkg_name += eb.toolchain['version']
        try:
            self.pkg_name += eb.versionsuffix
        except (AttributeError, NameError):
            pass
        print("Package: %s" % self.pkg_name)

        self.out = open(self.pkg_name + '.md', 'w')
        self.html_header()
        self.exts2md()

    def html_header(self):
        """write html head block
        All custom styles are defined here.  No external css is used.
        """
        today = date.today() 
        date_string = '%d-%02d-%02d' % (today.year, today.month, today.day) 
        block = '---\ntitle: %s\n' % self.pkg_name
        block += 'date: %s\n---\n\n' % date_string
        self.out.write(block)

    def exts2md(self):
        """ write the output file in Markdown format"""
        self.out.write('### Known Issues\n')
        self.out.write(' * None\n\n')
        self.out.write('### Package List\n')
        pkg_info = {}
        for pkg in self.extension:
            if isinstance(pkg, tuple):
                pkg_name = pkg[0]
                version = str(pkg[1])
                url, description = self.get_package_url(pkg_name)
                if self.verbose:
                    print('{}'.format(pkg_name))
            else:
                pkg_name = pkg
                version = 'built in'
                url, description = 'not found', ''
            pkg_info[pkg_name] = {}
            pkg_info[pkg_name]['version'] = version
            pkg_info[pkg_name]['url'] = url
            pkg_info[pkg_name]['description'] = description
        pkg_list = list(pkg_info)
        pkg_list.sort()
        for key in pkg_list:
            if pkg_info[key]['url'] == 'not found':
                self.out.write('  * %s %s\n' % (key, pkg_info[key]['version']))
            else:
                msg = '  * [%s-%s](%s) %s\n' % (key,
                                                pkg_info[key]['version'],
                                                pkg_info[key]['url'],
                                                pkg_info[key]['description'])
                self.out.write(msg)
        self.out.close()

    def get_package_url(self, pkg_name):
        pass


class R(ExtsList):
    depend_exclude = {'R', 'parallel', 'methods', 'utils',
                      'stats', 'stats4', 'graphics', 'grDevices',
                      'tools', 'tcltk', 'grid', 'splines'
                      }

    def __init__(self, eb, verbose):
        self.debug = False
        self.verbose = verbose
        self.biocver = None
        self.bioc_data = {}
        self.bioc_urls = []
        try:
            self.biocver = eb.biocver
        except (AttributeError, NameError):
            print("biocver not set")
        if self.biocver:
            self.read_bioconductor_packages()
            self.bioconductor = True
        ExtsList.__init__(self, eb, verbose)

    def read_bioconductor_packages(self):
        """ read the Bioconductor package list into bio_data dict
            """
        base_url = 'https://bioconductor.org/packages/json/%s' % self.biocver
        self.bioc_urls = [
             '%s/bioc/packages.json' % base_url,
             '%s/data/annotation/packages.json' % base_url,
             '%s/data/experiment/packages.json' % base_url,
        ]
        for url in self.bioc_urls:
            resp = requests.get(url)
            if resp.status_code != 200:
                print('Error: %s %s' % (resp.status_code, url))
                sys.exit(1)
            self.bioc_data.update(resp.json())
            if self.debug:
                print('reading Bioconductor Package inf: %s' % url)
                pkgcount = len(self.bioc_data.keys())
                print('size: %s' % pkgcount)

    @staticmethod
    def check_CRAN(pkg_name):
        cran_list = "http://crandb.r-pkg.org/"
        resp = requests.get(url=cran_list + pkg_name)
        cran_info = json.loads(resp.text)
        if 'error' in cran_info and cran_info['error'] == 'not_found':
            url = 'not found'
            description = ''
        else:
            try:
                description = cran_info[u'Title']
            except KeyError:
                description = ''
            url = 'https://cran.r-project.org/web/packages/%s/index.html' % pkg_name

        return url, description

    def check_BioC(self, pkg_name):
        """ example:
            bioc_data['pkg']['Depends']
                     [u'R (>= 2.10)', u'BiocGenerics (>= 0.3.2)', u'utils']
                     ['Imports']
                     ['Biobase', 'graphics', 'grDevices', 'venn', 'mclust',
                      'utils', 'MASS']
            some fun fields in the MetaData:
            ['Description', 'MD5sum', 'Package', 'URL', 'Version',etc...]
        """
        url = 'not found'
        base_url = 'https://www.bioconductor.org/packages/release/bioc/html/%s.html'
        if pkg_name in self.bioc_data.keys():
            url = base_url % pkg_name
            description = self.bioc_data[pkg_name]['Title']
        if url == 'not found':
            url, description = self.check_CRAN(pkg_name)
            description = '[CRAN]&emsp;' + description
        return url, description

    def get_package_url(self, pkg_name):
        url, description = self.check_CRAN(pkg_name)
        if url == 'not found':
            if self.debug:
                print('package %s not found in CRAN, check Bioconductor' % pkg_name)
            url, description = self.check_BioC(pkg_name)
        return url, description


class PythonExts(ExtsList):
    def __init__(self, eb, verbose):
        ExtsList.__init__(self, eb, verbose)
        self.verbose = verbose
        self.pkg_dict = None

    def get_package_url(self, pkg_name):
        """ Python PYPI """
        req = 'https://pypi.org/pypi/%s/json' % pkg_name
        resp = requests.get(req)
        description = ''
        if resp.status_code != 200:
            return 'not found', ''
        project = resp.json()
        if 'description' in project['info']:
            description = project['info']['summary']
        if 'home_page' in project['info']:
            url =  project['info']['home_page']
        elif 'project_urls' in project['info']:
            url =  project['info']['project_urls']['Homepage']
        elif 'project_url' in project['info']:
            url =  project['info']['project_url']
        else:
            url = project['info']['package_url']
        return url, description


def help():
    print("usage: easy_annotate [R or Python Easyconfig]")
    print("Create markdown documentation from Easyconfigs. Document all the libraries"),
    print("from the exts_list for R and Python EasyConfigs.")


def main():
    """ main """
    parser = argparse.ArgumentParser(description='Annotate extslist')
    parser.add_argument('--version', action='version',
                        version='%(prog)s ' + __version__)
    parser.add_argument(
        '-v', '--verbose', dest='verbose', required=False, action='store_true',
        help='Verbose; print lots of extra stuff, (default: false)')
    parser.add_argument('easyconfig', nargs='?')
    args = parser.parse_args()

    if args.easyconfig:
        eb = FrameWork(args)
    else:
        print("provide a module nameModule with R-, or Python-")
        sys.exit(1)
    if eb.name == 'R':
        R(eb, args.verbose)
    elif eb.name == 'Python':
        PythonExts(eb, args.verbose)
    else:
        print('easyanotate does not know how to process: {}'.format(eb.name))


if __name__ == '__main__':
    main()
