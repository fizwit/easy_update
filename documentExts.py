#!/usr/bin/env python

import os
import sys
import imp
import json
import requests
import urllib2
import xmlrpclib


class ExtsList(object):
    """ Extension List Update is a utilty program for maintaining EasyBuild easyconfig files for R and Python.
     Easyconfig files for R and Python can have over a hundred modules in an ext_list.  This program automates the
     the updating of extension lists for R and Python.

    """

    def __init__(self, file_path, verbose=False):
        self.verbose = verbose
        self.pkg_count = 0

        file_name = os.path.basename(file_path)
        if file_name[:2] == 'R-bundle-Bioconductor':
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

        eb = self.parse_eb(file_name, primary=True)
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
        self.out.write('<h2>%s</h2>' % self.pkg_name)
        f_name = os.path.basename(file_name)[:-3]
        if f_name != self.pkg_name:
            print "file name does not match module. file name: ", f_name, " package: ", self.pkg_name
            sys.exit(0)

    def parse_eb(self, file_name, primary):
        """ interpret easyconfig file with 'exec'.  Interperting fails if constants that are not defined within the
            easyconfig file.  Add undefined constants it <header>.
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
        if primary:     # save original text of source code 
            self.code = code
            self.ptr_head = len(header)
        return eb

    def exts2html(self):
        for pkg in self.extension:
            if isinstance(pkg, tuple):
                pkg_name = pkg[0]
                version = str(pkg[1])
                url = self.get_package_url(pkg_name)
                self.out.write('<li><a href="%s">%s-%s</a></li>' % (url, pkg_name, version))
            else:
                pkg_name = pkg
                version = 'built in'
                self.out.write('<li>%s-%s</li>' % (pkg_name, version))

    def get_package_url(sefl, pkg_name):
        pass
    
class R(ExtsList):
    depend_exclude = {'R', 'parallel', 'methods', 'utils', 'stats', 'stats4', 'graphics', 'grDevices',
                      'tools', 'tcltk', 'grid', 'splines'}

    def __init__(self, file_name, verbose=False):
        ExtsList.__init__(self, file_name, verbose)

        if 'bioconductor' in self.pkg_name.lower():
            self.bioconductor = True
            self.read_bioconductor_pacakges()
        else:
            self.bioconductor = False

    def read_bioconductor_pacakges(self):
            """ read the Bioconductor package list into bio_data dict
            """
            self.bioc_data = {}
            bioc_urls = {'https://bioconductor.org/packages/json/3.4/bioc/packages.json',
                         'https://bioconductor.org/packages/json/3.4/data/annotation/packages.json',
                         'https://bioconductor.org/packages/json/3.4/data/experiment/packages.json'}
            self.bioc_data = {}
            for url in bioc_urls:
                try:
                    response = urllib2.urlopen(url)
                except IOError as e:
                    print 'URL request: ', url
                    sys.exit(e)
                self.bioc_data.update(json.loads(response.read()))

    def check_CRAN(self, pkg_name):
        url = 'https://cran.r-project.org/web/packages/%s/index.html' % pkg_name
        return url

    def check_BioC(self, pkg_name):
        """ example bioc_data['pkg']['Depends'] [u'R (>= 2.10)', u'BiocGenerics (>= 0.3.2)', u'utils']
                                    ['Imports'] [ 'Biobase', 'graphics', 'grDevices', 'venn', 'mclust', 'stats', 'utils', 'MASS' ]
        """
        if pkg_name in self.bioc_data:
            url = 'http://bioconductor.org/packages/release/bioc/html/%s.html' % pkg_name
        else:
            url = 'not found'
        return url

    def get_package_url(self, pkg_name):
        if self.bioconductor:
            url = self.check_BioC(pkg_name)
        else:
            url = self.check_CRAN(pkg_name)
        return url

class PythonExts(ExtsList):
    def __init__(self, file_name, verbose=False):
        ExtsList.__init__(self, file_name, 'Python')
        self.verbose = verbose
        self.pkg_dict = None

    def parse_pypi_requires(self, requires):
        if ';' in requires:
            name = requires.split(';')[0]
        elif '(' in requires:
            name = requires.split('(')[0]
        else:
            name = requires
        return name

    def check_package(self, pkg_name):
        if pkg_name in self.exts_processed:
            return []
        client = xmlrpclib.ServerProxy('https://pypi.python.org/pypi')
        xml_vers = client.package_releases(pkg_name)
        if xml_vers:
            self.pkg_dict[pkg_name] = [xml_vers[0]]
            xml_info = client.release_data(pkg_name, xml_vers[0])
            if 'requires_dist' in xml_info:
                for requires in xml_info['requires_dist']:
                    req_pkg = self.parse_pypi_requires(requires)
                    self.exts_processed[pkg_name].append(req_pkg)
                    # print("requires_dist:",req)
        else:
            print("Warning: could not find Python package:", pkg_name)


if __name__ == '__main__':
    if len(sys.argv) != 2:
        print "usage: %s [R or Python easybuild file]" % sys.argv[0]
        sys.exit(0)

    file_name = os.path.basename(sys.argv[1])
    if file_name[:2] == 'R-':
        module = R(sys.argv[1], verbose=True)
    elif file_name[:7] == 'Python-':
        module = PythonExts(sys.argv[1], verbose=True)
    else:
        print "Module name must begin with R-, R-bundle-Bioconductor or Python-"
        sys.exit(1)
    module.exts2html()