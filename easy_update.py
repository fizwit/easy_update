#!/usr/bin/env python

import re
import os
import sys
import imp
import json
import requests
import urllib2
import xmlrpclib


class ExtsList(object):
    """ Extension List Update is a utilty program for maintaining EasyBuild easyconfig files for R and Python.
     R and Python langueges support package extensions. Easyconfig supports the building of the language 
     with a list of extions. This program automates the the updating of extension lists for R and Python
     by using API for resolving current version for each package.
    """

    def __init__(self, file_name, lang, verbose=False):
        self.lang = lang
        self.verbose = verbose
        self.ext_list_len = 0
        self.ext_counter = 0
        self.pkg_update = 0 
        self.pkg_new = 0 

        self.exts_processed = []  # single list of package names
        self.depend_exclude = []  # built in packages not be added to exts_list 
        self.prolog = '## remove ##\n'
        self.ptr_head = 0 
        self.indent_n = 4
        self.indent = ' ' * self.indent_n
        self.pkg_top = None
        
        eb = self.parse_eb(file_name, primary=True)
        self.exts_orig = eb.exts_list
        self.toolchain = eb.toolchain
        self.dependencies = eb.dependencies
        self.pkg_name = eb.name + '-' + eb.version
        self.pkg_name += '-' + eb.toolchain['name'] + '-' + eb.toolchain['version']

        self.bioconductor = False
        try:
            self.pkg_name += eb.versionsuffix
        except (AttributeError, NameError):
            pass
        print "Package name:", self.pkg_name
        f_name = os.path.basename(file_name)[:-3]
        if f_name != self.pkg_name:
            print "file name does not match module. file name: ", f_name, " package: ", self.pkg_name
            sys.exit(0)
        self.out = open(self.pkg_name + ".update", 'w')

    def parse_eb(self, file_name, primary):
        """ interpret easyconfig file with 'exec'.  Interperting fails if constants that are not defined within the
            easyconfig file.  Add undefined constants it <header>.
        """
        header = 'SOURCE_TGZ  = "%(name)s-%(version)s.tgz"\n'
        header += 'SOURCE_TAR_GZ = "%(name)s-%(version)s.tar.gz"\n'
        header += self.prolog
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

    def get_package_info(self, pkg):
        pass

    def check_package(self, pkg ):
        pkg_name = pkg[0]
        if pkg_name in [i[0] for i in self.exts_processed] or pkg_name in self.depend_exclude: 
            if pkg_name == self.pkg_top:
                pkg.append('duplicate')
                self.exts_processed.append(pkg)
            return
        pkg_ver, depends = self.get_package_info(pkg)
        if pkg_ver == "error" or pkg_ver == 'not found':
            if pkg_name == self.pkg_top:
                pkg.append('keep')
            else:
                return
        else:
            if self.pkg_top == pkg_name:
                if pkg[1] == pkg_ver:
                     pkg.append('keep')
                else:
                     pkg[1] = pkg_ver 
                     pkg.append('update')
                     self.pkg_update +=1
            else:
                pkg[1] = pkg_ver 
                pkg.append('new')
                self.pkg_new +=1

        self.exts_processed.append(pkg)

        for depend in depends: 
            if depend not in self.depend_exclude:
                if self.lang == "Python":
                    ext_url  = "{\n%s'source_urls': " % (self.indent * 2)
                    ext_url += "['https://pypi.python.org/packages/source/%s/%s/'],\n%s}" % (
                        depend[0], depend, self.indent)
                else:
                    ext_url = ''
                self.check_package([depend, 'x', ext_url])
        self.ext_counter += 1
        if self.verbose:
            print "%20s : %-8s (%s) [%2d, %d]" % (pkg[0], pkg[1], pkg[-1], self.ext_list_len, self.ext_counter)

    def update_exts(self):
        self.ext_list_len = len(self.exts_orig)
        for pkg in self.exts_orig:
            if isinstance(pkg, tuple):
                self.pkg_top = pkg[0]
                self.check_package(list(pkg))
            else:
                self.exts_processed.append(pkg)

    def write_chunk(self, indx):
        self.out.write(self.code[self.ptr_head:indx])
        self.ptr_head = indx

    def rewriteExtension(self, pkg):
        indx = self.code[self.ptr_head:].find(pkg[0]) + self.ptr_head + len(pkg[0]) + 1  # parse to package name
        indx = self.code[indx:].find("'") + indx + 1  # beginning quote of version
        self.write_chunk(indx)
        self.out.write("%s'," % pkg[1])  # write version Number
        self.ptr_head = self.code[self.ptr_head:].find(',') + self.ptr_head + 1
        indx = self.code[self.ptr_head:].find('),') + self.ptr_head + 3  # search to the end of the extension
        self.write_chunk(indx)

    def print_update(self):
        """ this needs to be re-written correctly
            use source text as pattern
        """
        indx = self.code.find('exts_list') + len('exts_list')
        self.write_chunk(indx)

        for extension in self.exts_processed:
            if isinstance(extension, str):  # base library with no version
                indx = self.code[self.ptr_head:].find(extension) + self.ptr_head + len(extension) + 2
                self.write_chunk(indx)
                continue
            action = extension.pop()
            if action == 'keep' or action == 'update':
                self.rewriteExtension(extension)
                # sys.exit(0)
            elif action == 'duplicate':
                print("duplicate: %s" % extension[0])
                self.ptr_head = self.code[self.ptr_head:].find(extension[0]) + self.ptr_head + len(extension[0])
                self.ptr_head = self.code[self.ptr_head:].find('),') + self.ptr_head + 3
                continue
            elif action == 'new':
                if self.bioconductor and extension[2] == 'ext_options':  # do not add cran packages to bioConductor
                    print " CRAN depencancy: " + extension[0]
                else:
                    self.out.write("%s('%s', '%s', %s),\n" % (self.indent, extension[0], extension[1], extension[2]))
        self.out.write(self.code[self.ptr_head:])
        print "Updated Packages: %d" % self.pkg_update
        print "New Packages: %d" % self.pkg_new


class R(ExtsList):
    def __init__(self, file_name, verbose=False):
        ExtsList.__init__(self, file_name, 'R', verbose)
        self.depend_exclude = ['R', 'parallel', 'methods', 'utils', 'stats', 
            'stats4', 'graphics', 'grDevices', 'tools', 'tcltk', 'grid', 'splines']

        if 'bioconductor' in self.pkg_name.lower():
            self.bioconductor = True
            self.R_modules = [] 

            #  Read the R package list from the dependent R package 
            for dep in self.dependencies:
                if dep[0] == 'R':
                   R_name =  dep[0] + '-' + dep[1] + '-' 
                   R_name += self.toolchain['name'] + '-' + self.toolchain['version']
                   if len(dep) > 2:
                       R_name += dep[2]
                   R_name += '.eb'
                   print 'Required R module: ', R_name
                   if  os.path.dirname(file_name):
                       R_name = os.path.dirname(file_name) + '/' + R_name
                   eb = self.parse_eb(R_name, primary=False)
                   break
            for pkg in eb.exts_list:
                if isinstance(pkg, tuple):
                    self.R_modules.append(pkg[0])
                else:
                    self.R_modules.append(pkg)
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

    def check_CRAN(self, pkg):
        cran_list = "http://crandb.r-pkg.org/"
        resp = requests.get(url=cran_list + pkg[0])

        cran_info = json.loads(resp.text)
        if 'error' in cran_info and cran_info['error'] == 'not_found':
            return "not found", []
        try:
            pkg_ver = cran_info[u'Version']
        except KeyError:
            return "error", []
        depends = []
        if u'License' in cran_info and u'Part of R' in cran_info[u'License']:
            return 'base package', [] 
        if u"Depends" in cran_info:
            depends = cran_info[u"Depends"].keys()
        if u"Imports" in cran_info:
           depends += cran_info[u"Imports"].keys() 
        return pkg_ver, depends

    def check_BioC(self, pkg):
        """ example bioc_data['pkg']['Depends'] [u'R (>= 2.10)', u'BiocGenerics (>= 0.3.2)', u'utils']
                                    ['Imports'] [ 'Biobase', 'graphics', 'grDevices', 'venn', 'mclust', 'stats', 'utils', 'MASS' ]
        """
        depends = []
        if pkg[0] in self.bioc_data:
            pkg_ver = self.bioc_data[pkg[0]]['Version']
            if 'Depends' in self.bioc_data[pkg[0]]:
                depends = [re.split('[ (><=,]',s)[0] for s in self.bioc_data[pkg[0]]['Depends']]
            if 'Imports' in self.bioc_data[pkg[0]]:
                depends = [re.split('[ (><=,]',s)[0] for s in self.bioc_data[pkg[0]]['Imports']]
        else:
            pkg_ver = "not found"
        return pkg_ver, depends

    def get_package_info(self, pkg):
        if self.bioconductor:
            pkg_ver, depends = self.check_BioC(pkg)
            pkg[2] = 'bioconductor_options'
            if pkg_ver == 'not found':
                if pkg[0] in self.R_modules:
                    return pkg_ver, []
                pkg_ver, depends = self.check_CRAN(pkg)
                pkg[2] = 'ext_options'
        else:
            pkg_ver, depends = self.check_CRAN(pkg)
            pkg[2] = 'ext_options'
        for p in depends:
            print("%s requires: %s" % (pkg[0], p)) 
        return pkg_ver, depends


class PythonExts(ExtsList):

    def __init__(self, file_name, verbose=False):
        ExtsList.__init__(self, file_name, 'Python')
        self.verbose = verbose
        self.pkg_dict = None
        self.client = xmlrpclib.ServerProxy('https://pypi.python.org/pypi')
        #self.depend_exclude = []

    def parse_pypi_requires(self, requires):
        """ pypi requiers_list is a mess of ugly inconsistent strings
            extreme badness incounted includes packages that referance them selves (infinite recursion) And
            pypi package names with incorect case

            We only care about the package name so ignore all version information 
            input: 'numpy (>=1.7.1)'  output: ['numpy', '']
            badness:  
                psutil (<2.0.0,>=1.1.1)
                netaddr (!=0.7.16,>=0.7.13)
                requests>=2.0    # no delimiters at all
                apscheduler  != APScheduler
        """
        require_re = '^([A-Za-z0-9_\-\.]+)(?:.*)$'
        ans = re.search(require_re, requires)
        if ans:
            name = ans.group(1)
        else:
             print("difficult to parse requirement: <%s>" % requires)
             name = requires
        return name

    def get_package_info(self, pkg):
        """Python pypi API for package version and dependancy list 
           pkg is a list; ['package name', 'version', 'other stuff']
           return the version number for the package and a list of dependancie
        """
        depends = []
        xml_vers = self.client.package_releases(pkg[0])
        if xml_vers:
            pkg_ver = xml_vers[0]
            xml_info = self.client.release_data(pkg[0], pkg_ver)
            if 'requires_dist' in xml_info.keys():
                for requires in xml_info['requires_dist']:
                    if "=='win32'" in requires or '=="win32"' in requires:
                        continue 
                    pkg_name = self.parse_pypi_requires(requires)
                    depends.append(pkg_name)
                print("%s requires_dist: " % pkg[0]),
                print(', '.join(depends))
        else:
            self.depend_exclude.append(pkg[0])
            print("Warning: %s Not in PyPi. No depdancy checking performed" % pkg[0])
            pkg_ver = 'not found'
        return pkg_ver, depends


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
        print "Module name must begin with R- or Python-"
        sys.exit(1)
    module.update_exts()
    module.print_update()
