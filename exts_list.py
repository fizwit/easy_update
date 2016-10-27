#!/usr/bin/env python



import imp
import json
import requests
import urllib2


class ExtsList(object):
    """ Extension List Update is a utilty program for maintaining EasyBuild easyconfig files for R and Python.
     Easyconfig files for R and Python can have over a hundred modules in an ext_list.  This program automates the
     the updating of extension lists for R and Python.

    """
    def __init__(self, file_name, lang, verbose=False):
        self.offline = True
        self.lang = lang
        self.verbose = verbose
        self.indent_n = 4

        self.new_exts = []
        self.exts_remove = []
        self.exts_processed = []  # single list of package names
        self.prolog = '## remove ##\n'
        self.indent = ' ' * self.indent_n
        self.pkg_top = None
        eb = imp.new_module("easyconfig")

        """ interpreting easyconfig files fail due to missing constants that are not defined within the
            easyconfig file.  Add undefined constants here.
        """
        header = 'SOURCE_TGZ  = "%(name)s-%(version)s.tgz"\n'
        header += 'SOURCE_TAR_GZ = "%(name)s-%(version)s.tar.gz"\n'
        header += self.prolog
        self.ptr_head = len(header)
        self.code = header

        with open(file_name, "r") as f:
            self.code += f.read()
        try:
            exec (self.code, eb.__dict__)
        except Exception, e:
            print "interperting easyconfig error: %s" % e

        self.exts_orig = eb.exts_list
        self.pkg_name = eb.name + '-' + eb.version
        self.pkg_name += '-' + eb.toolchain['name'] + '-' + eb.toolchain['version']
        try:
            self.pkg_name += eb.versionsuffix
        except (AttributeError, NameError):
            pass
        print "Package:", self.pkg_name

        if 'bioconductor' in eb.name.lower():
            self.bioconductor = True
            self.bioc_data = {}
            if self.offline:
                bioc_files = ['packages.json', 'annotation.json', 'experiment.json']
                for bioc_file in bioc_files:
                    json_data = open(bioc_file).read()
                    self.bioc_data.update(json.loads(json_data))
            else:
                bioc_urls = {'https://bioconductor.org/packages/json/3.3/bioc/packages.json',
                             'https://bioconductor.org/packages/json/3.3/data/annotation/packages.json',
                             'https://bioconductor.org/packages/json/3.3/data/experiment/packages.json'}
                self.bioc_data = {}
                for url in bioc_urls:
                    response = urllib2.urlopen(url)
                    self.bioc_data.update(json.loads(response.read()))

    def update_exts(self):
        for pkg in self.exts_orig:
            if isinstance(pkg, tuple):
                self.pkg_top = pkg[0]
                self.check_package(list(pkg))
            else:
                self.new_exts.append(pkg)

    def rewriteExtension(self, pkg):
        indx = self.code[self.ptr_head:].find(pkg[0])+ self.ptr_head + len(pkg[0]) + 1 # parse to package name
        indx = self.code[indx:].find("'") + indx + 1    # beginning quote of version
        self.write_chunk(indx)
        self.out.write("%s'," % pkg[1])    # write version Number
        self.ptr_head = self.code[self.ptr_head:].find(',') + self.ptr_head + 1
        indx = self.code[self.ptr_head:].find(',') + self.ptr_head + 2   # find end of extension
        self.write_chunk(indx)

    def write_chunk(self, indx):
        self.out.write(self.code[self.ptr_head:indx])
        self.ptr_head = indx

    def print_update(self):
        """ this needs to be re-written correctly
            use source text as pattern
        """
        self.out = open(self.pkg_name + ".update", 'w')
        indx = self.code.find('exts_list') + len('exts_list')
        self.write_chunk(indx)

        for extension in self.new_exts:
            if isinstance(extension, str):  # base library with no version
                self.ptr_head = self.write_chunk(indx, len(extension[0]))
                continue
            action = extension.pop()
            print "processing: " + extension[0] + " - " + action
            if action == 'keep' or action == 'update':
                self.rewriteExtension(extension)
                #sys.exit(0)
            elif action == 'duplicate':
                self.ptr_head = self.code[self.ptr_head:].find(extension[0]) + len(extension[0])
                continue
            elif action == 'new':
                if self.bioconductor and extension[2] == 'ext_options':  # do not add cran packages to bioConductor
                    print " CRAN depencancy: " + extension[0]
                else:
                    self.out.write("%s('%s', '%s', %s),\n" % (self.indent, extension[0], extension[1], extension[2]))
        self.out.write(self.code[self.ptr_head:])

    def check_package(self, pkg):
        pass


class R(ExtsList):
    depend_exclude = {'R', 'parallel', 'methods', 'utils', 'stats', 'stats4', 'graphics', 'grDevices',
                      'tools', 'tcltk'}

    def __init__(self, file_name, verbose=False):
        ExtsList.__init__(self, file_name, 'R', verbose)

    def check_CRAN(self, pkg):
        if self.offline:
            return pkg[1], []
        cran_list = "http://crandb.r-pkg.org/"
        resp = requests.get(url=cran_list + pkg[0])

        cran_info = json.loads(resp.text)
        if 'error' in cran_info and cran_info['error'] == 'not_found':
            return "not found", []
        try:
            pkg_ver = cran_info[u'Version']
        except KeyError, e:
            self.exts_remove.append(pkg[0])
            return "error", []
        depends = []
        if u"Depends" in cran_info:
            depends = cran_info[u"Depends"].keys()
        return pkg_ver, depends

    def check_BioC(self, pkg):
        """
            example bioc_data['pkg']['Depends'] [u'R (>= 2.10)', u'BiocGenerics (>= 0.3.2)', u'utils']
        """
        depends = []
        if pkg[0] in self.bioc_data:
            pkg_ver = self.bioc_data[pkg[0]]['Version']
            dep_temp = []
            if 'Depends' in self.bioc_data[pkg[0]]:
                depends = [s.split(' ')[0] for s in self.bioc_data[pkg[0]]['Depends']]
        else:
            pkg_ver = "not found"
        return pkg_ver, depends

    def check_package(self, pkg):
        if pkg[0] in self.exts_processed:  # remove dupicates
            if pkg[0] == self.pkg_top:
                pkg.append('duplicate')
            return
        if self.bioconductor:
            pkg_ver, depends = self.check_BioC(pkg)
            pkg[2] = 'bioconductor_options'
            if pkg_ver == 'not found':
                pkg_ver, depends = self.check_CRAN(pkg)
                pkg[2] = 'ext_options'
        else:
            pkg_ver, depends = self.check_CRAN(pkg)
            pkg[2] = 'ext_options'

        if pkg_ver == "error" or pkg_ver == 'not found':
            if pkg[0] == self.pkg_top:
                pkg.append('remove')
            return

        if pkg[0] == self.pkg_top:
            if pkg[1] == pkg_ver:
                pkg.append('keep')
            else:
                pkg[1] = pkg_ver
                pkg.append('update')
        else:
            pkg.append('new')

        for depend in depends:
            if depend not in self.depend_exclude:
                self.check_package([depend, "x", "source_url"])
        self.new_exts.append(pkg)
        self.exts_processed.append(pkg[0])
        if self.verbose:
            if 'new' == pkg[-1]:
                print "%20s : %-8s (%s-%s)" % (pkg[0], pkg[1], pkg[-1],pkg[2])
            else:
                print "%20s : %-8s (%s)" % (pkg[0], pkg[1], pkg[-1])


import xmlrpclib


class Python_exts(ExtsList):
    def __init__(self, file_name):
        ExtsList.__init__(self, file_name, 'Python')
        self.pkg_dict = None

    def parse_pypi_requires(self, requires):
        if ';' in requires:
            name = requires.split(';')[0]
        elif '(' in requires:
            name = requires.split('(')[0]
        else:
            name = requires

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
    #r = R('R-bundle-Bioconductor-3.3-foss-2016b-R-3.3.1-fh1.eb', verbose=True)
    #r.update_exts()
    #r.print_update()

    r = Python_exts('R-3.3.1-foss-2016b.eb')
    r.update_exts()
    r.print_update()
