#!/usr/bin/env python

import os
import sys
import imp
import json
import ssl
from datetime import datetime
import requests
import urllib2
import xmlrpclib

__author__ = "John Dey"
__version__ = "1.0.1"
__email__ = "jfdey@fredhutch.org"


class ExtsList(object):
    """ Easy Anotate is a utilty program for documenting EasyBuild easyconfig
    files for R and Python. Easyconfig files for R and Python can have over
    a hundred modules in an ext_list.  This program creates
    html documentation of extension list.
    """

    def __init__(self, file_path, verbose=False):
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
        file_name = os.path.basename(file_path)
        f_name = os.path.basename(file_name)[:-3]
        print("Package: %s" % self.pkg_name)
        if f_name != self.pkg_name:
            print("file name does not match module name. " +
                  "file name: %s, package: %s" % (f_name, self.pkg_name))
            sys.exit(0)
        self.out = open(f_name + '.html', 'w')
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
        block = """<!DOCTYPE html>
<html>
<head>
  <title>Fred Hutchinson Cancer Research Center</title>
  <title>EasyBuild Annotate extension list for R, Biocondotor and
 Python easyconfig files</title>
  <style>
    body {font-family: Helvetica,Arial,"Calibri","Lucida Grande",sans-serif;}
    .ext_list a {color: black; text-decoration: none; font-weight: bold;}
    .ext_list li:hover a:hover {color: #89c348;}
    span.fh_green {color: #89c348;}  <!-- Hutch Green -->
  </style>
</head>
<body>
"""
        self.out.write(block)
        self.out.write('<h2><span class="fh_green">%s</span></h2>\n' %
                       self.pkg_name)
        self.out.write('<h3>Package List</h3>\n<div class="ext_list">\n')

    def exts2html(self):
        self.out.write('  <ul style="list-style-type:none">\n')
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
                self.out.write('    <li>%s&emsp;%s</li>\n' %
                               (key, pkg_info[key]['version']))
            else:
                self.out.write('    <li><a href="%s">%s-%s</a>&emsp;%s</li>\n'
                               % (pkg_info[key]['url'],
                                  key,
                                  pkg_info[key]['version'],
                                  pkg_info[key]['description']))
        self.out.write('  </ul>\n</div>\n')
        self.out.write('  updated: %s\n' %
                       "{:%B %d, %Y}".format(datetime.now()))
        self.out.write('</body></html>\n')

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

        if 'bioconductor' in self.pkg_name.lower():
            self.bioconductor = True
            self.read_bioconductor_packages()
        else:
            self.bioconductor = False

    def read_bioconductor_packages(self):
        """ read the Bioconductor package list into bio_data dict
            """
        self.bioc_urls = [
            ['packages',
             'https://bioconductor.org/packages/json/3.4/bioc/packages.json',
             'https://bioconductor.org/packages/release/bioc/html/'
             ],
            ['annotation',
             'https://bioconductor.org/packages/json/3.4/data/annotation/packages.json',
             'https://bioconductor.org/packages/release/data/annotation/html/'
             ],
            ['experiment',
             'https://bioconductor.org/packages/json/3.4/data/experiment/packages.json',
             'https://bioconductor.org/packages/release/data/experiment/html/'
             ]
        ]
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        for url in self.bioc_urls:
            try:
                response = urllib2.urlopen(url[1], context=ctx)
            except IOError as e:
                print('URL request: %s' % url[1])
                sys.exit(e)
            self.bioc_data[url[0]] = json.loads(response.read())

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
        """
        url = 'not found'
        for bioc_pkg in self.bioc_urls:
            if pkg_name in self.bioc_data[bioc_pkg[0]]:
                url = bioc_pkg[2] + pkg_name + '.html'
                description = self.bioc_data[bioc_pkg[0]][pkg_name]['Title']
        if url == 'not found':
            url, description = self.check_CRAN(pkg_name)
            description = '[CRAN]&emsp;' + description
        return url, description

    def get_package_url(self, pkg_name):
        if self.bioconductor:
            url, description = self.check_BioC(pkg_name)
        else:
            url, description = self.check_CRAN(pkg_name)
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
