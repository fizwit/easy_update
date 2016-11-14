#!/usr/bin/env python

import os
import sys
import imp
import json
import ssl
import requests
import urllib2
import xmlrpclib

__author__ = "John Dey"
__version__ = "1.0"
__email__ = "jfdey@fredhutch.org"


class ExtsList(object):
    """ Easy Anotate is a utilty program for documenting EasyBuild easyconfig files for R and Python.
      Easyconfig files for R and Python can have over a hundred modules in an ext_list.  This program creates
      html documentation of extension list.
    """

    def __init__(self, file_path, verbose=False):
        self.verbose = verbose
        self.pkg_count = 0

        file_name = os.path.basename(file_path)
        if file_name[:21] == 'R-bundle-Bioconductor':
            self.out = open('Bioconductor.html', 'w')
        elif file_name[:2] == 'R-':
            self.out = open('R.html', 'w')
        elif file_name[:8] == 'Python-2':
            self.out = open('Python2.html', 'w')
        elif file_name[:8] == 'Python-3':
            self.out = open('Python3.html', 'w')
        else:
            print "Module name must begin with R-, R-bundle-Bioconductor or Python-"
            sys.exit(1)

        eb = self.parse_eb(file_name)
        self.extension = eb.exts_list
        self.toolchain = eb.toolchain
        self.dependencies = eb.dependencies
        self.pkg_name = eb.name + '-' + eb.version
        self.pkg_name += '-' + eb.toolchain['name'] + '-' + eb.toolchain['version']
        try:
            self.pkg_name += eb.versionsuffix
        except (AttributeError, NameError):
            pass
        print "Package:", self.pkg_name
        self.html_header()

        f_name = os.path.basename(file_name)[:-3]
        if f_name != self.pkg_name:
            print "file name does not match module. file name: ", f_name, " package: ", self.pkg_name
            sys.exit(0)

    @staticmethod
    def parse_eb(file_name):
        # type: (object) -> object file_name) -> dict:
        """ interpret easyconfig file with 'exec'.  Interperting fails if constants that are not defined within the
            Easyconfig file.  Add undefined constants it <header>.
        """
        header = 'SOURCE_TGZ  = "%(name)s-%(version)s.tgz"\n'
        header += 'SOURCE_TAR_GZ = "%(name)s-%(version)s.tar.gz"\n'
        code = header

        eb = imp.new_module("easyconfig")
        with open(file_name, "r") as f:
            code += f.read()
        try:
            exec (code, eb.__dict__)
        except Exception, e:
            print "interperting easyconfig error: %s" % e
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
  <title>EasyBuild Annotate extension list for R, Biocondotor and Python easyconfig files</title>
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
        self.out.write('<h2><span class="fh_green">%s</span></h2>' % self.pkg_name)
        self.out.write('<h3>Package List</h3>\n<div class="ext_list">\n')

    def exts2html(self):
        self.out.write('  <ul style="list-style-type:none">')
        for pkg in self.extension:
            if isinstance(pkg, tuple):
                pkg_name = pkg[0]
                version = str(pkg[1])
                url, description = self.get_package_url(pkg_name)

            else:
                pkg_name = pkg
                version = 'built in'
                url, description = 'not found', ''
            if url == 'not found':
                self.out.write('    <li>%s&emsp;%s</li>\n' % (pkg_name, version))
            else:
                self.out.write('    <li><a href="%s">%s-%s</a>&emsp;%s</li>\n' % (url, pkg_name, version, description))
        self.out.write('  </ul>\n</div>\n</body></html>')

    def get_package_url(self, pkg_name):
        pass
    

class R(ExtsList):
    depend_exclude = {'R', 'parallel', 'methods', 'utils', 'stats', 'stats4', 'graphics', 'grDevices',
                      'tools', 'tcltk', 'grid', 'splines'}

    def __init__(self, file_name, verbose=False):
        ExtsList.__init__(self, file_name, verbose)
        self.bioc_data = {}

        if 'bioconductor' in self.pkg_name.lower():
            self.bioconductor = True
            self.read_bioconductor_pacakges()
        else:
            self.bioconductor = False

    def read_bioconductor_pacakges(self):
            """ read the Bioconductor package list into bio_data dict
            """
            bioc_urls = {'https://bioconductor.org/packages/json/3.4/bioc/packages.json',
                         'https://bioconductor.org/packages/json/3.4/data/annotation/packages.json',
                         'https://bioconductor.org/packages/json/3.4/data/experiment/packages.json'}
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            for url in bioc_urls:
                try:
                    response = urllib2.urlopen(url, context=ctx)
                except IOError as e:
                    print 'URL request: ', url
                    sys.exit(e)
                self.bioc_data.update(json.loads(response.read()))

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
        """ example bioc_data['pkg']['Depends'] [u'R (>= 2.10)', u'BiocGenerics (>= 0.3.2)', u'utils']
                                    ['Imports'] [ 'Biobase', 'graphics', 'grDevices', 'venn', 'mclust', 'utils', 'MASS']
        """
        if pkg_name in self.bioc_data:
            url = 'http://bioconductor.org/packages/release/bioc/html/%s.html' % pkg_name
            description = self.bioc_data[pkg_name]['Title']
        else:
            url, description = self.check_CRAN
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
        print "usage: %s [R or Python easybuild file]" % sys.argv[0]
        sys.exit(0)

    base = os.path.basename(sys.argv[1])
    if base[:2] == 'R-':
        module = R(sys.argv[1], verbose=True)
    elif base[:7] == 'Python-':
        module = PythonExts(sys.argv[1], verbose=True)
    else:
        print "Module name must begin with R-, R-bundle-Bioconductor or Python-"
        sys.exit(1)
    module.exts2html()