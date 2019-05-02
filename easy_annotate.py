#!/usr/bin/env python

import os
import sys
import imp
import json
import ssl
from datetime import date
import requests
import urllib2
import xmlrpclib
from pprint import pprint

__author__ = "John Dey"
__version__ = "2.0.1"
__date__ = "April 3, 2019"
__email__ = "jfdey@fredhutch.org"

"""Versioin 1.x create HTML output
   Version 2 create Markdown output
"""

class ExtsList(object):
    """ Easy Anotate is a utilty program for documenting EasyBuild easyconfig
    files for R and Python. Easyconfig files for R and Python can have over
    a hundred modules in an ext_list.  This program creates
    html documentation of extension list.
    """

    def __init__(self, file_path, verbose=False):
        self.debug = False 
        self.verbose = verbose
        self.pkg_count = 0

        eb = self.parse_eb(file_path)
        self.extension = eb.exts_list
        self.toolchain = eb.toolchain
        self.dependencies = eb.dependencies
        self.pkg_name = eb.name + '-' + eb.version + '-'
        self.pkg_name += eb.toolchain['name'] + '-'
        self.pkg_name += eb.toolchain['version']
        try:
            self.pkg_name += eb.versionsuffix
        except (AttributeError, NameError):
            pass
        try:
            self.biocver = eb.biocver
        except (AttributeError, NameError):
            print("biocver not set")
            pass
        file_name = os.path.basename(file_path)
        f_name = os.path.basename(file_name)[:-3]
        print("Package: %s" % self.pkg_name)
        if f_name != self.pkg_name:
            print("file name does not match module name. " +
                  "file name: %s, package: %s" % (f_name, self.pkg_name))
            sys.exit(0)
        self.out = open(f_name + '.md', 'w')
        self.html_header()

    @staticmethod
    def parse_eb(file_path):
        # type: (object) -> object file_name) -> dict:
        """ interpret easyconfig file with 'exec'.  Interperting fails if
            undefined constants are within the Easyconfig file.
            Add undefined constants to <header>.
        """
        header = 'SOURCE_TGZ  = "%(name)s-%(version)s.tgz"\n'
        header += 'SOURCE_TAR_GZ = "%(name)s-%(version)s.tar.gz"\n'
        header += 'PYPI_SOURCE = "https://pypi.org/project/%(name)s"\n'
        code = header

        eb = imp.new_module("easyconfig")
        with open(file_path, "r") as f:
            code += f.read()
        try:
            exec (code, eb.__dict__)
        except Exception as e:
            print("interperting easyconfig error: %s" % e)
            eb = {}
        return eb

    def html_header(self):
        """write html head block
        All custom styles are defined here.  No external css is used.
        """
        today = date.today() 
        date_string = '%d-%02d-%02d' % (today.year, today.month, today.day) 
        block = '---\ntitle: %s\n' % self.pkg_name
        block += 'date: %s\n---\n\n' % date_string
        self.out.write(block)

    def exts2html(self):
        self.out.write('### Package List\n')
        pkg_info = {}
        for pkg in self.extension:
            if isinstance(pkg, tuple):
                pkg_name = pkg[0]
                version = str(pkg[1])
                url, description = self.get_package_url(pkg_name)
            else:
                pkg_name = pkg
                version = 'built in'
                url, description = 'not found', ''
            pkg_info[pkg_name] = {}
            pkg_info[pkg_name]['version'] = version
            pkg_info[pkg_name]['url'] = url
            pkg_info[pkg_name]['description'] = description
        pkg_list = pkg_info.keys()
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

    def __init__(self, file_name, verbose=False):
        ExtsList.__init__(self, file_name, verbose)
        self.bioc_data = {}
        self.bioc_urls = []

        if self.biocver :
            self.read_bioconductor_pacakges()
            self.bioconductor = True

    def read_bioconductor_pacakges(self):
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
            url = 'https://cran.r-project.org/packages=%s' % pkg_name

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
    def __init__(self, file_name, verbose=False):
        ExtsList.__init__(self, file_name, verbose)
        self.verbose = verbose
        self.pkg_dict = None

    def get_package_url(self, pkg_name):
        client = xmlrpclib.ServerProxy('https://pypi.python.org/pypi')
        url = 'not found'
        description = ''
        xml_vers = client.package_releases(pkg_name)
        if xml_vers:
            version = xml_vers[0]
        else:
            return url, description
        pkg_data = client.release_data(pkg_name, version)
        if pkg_data and 'summary' in pkg_data:
            description = pkg_data['summary']
        if pkg_data and 'package_url' in pkg_data:
            url = pkg_data['package_url']
        return url, description


if __name__ == '__main__':
    if len(sys.argv) != 2:
        print("usage: %s [R or Python easybuild file]" % sys.argv[0])
        sys.exit(0)

    base = os.path.basename(sys.argv[1])
    if base[:2] == 'R-':
        module = R(sys.argv[1], verbose=True)
    elif base[:7] == 'Python-':
        module = PythonExts(sys.argv[1], verbose=True)
    else:
        print("Module name must begin with R-, or Python-")
        sys.exit(1)
    module.exts2html()
