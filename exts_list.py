#!/usr/bin/env python

import imp
import json
import requests
import urllib2

"""
R-bundle-Bioconductor-3.3-foss-2016b-R-%(rver)s-fh1.update
R-bundle-Bioconductor-3.3-foss-2016b-R-3.3.1-fh1.eb
"""


class ExtsList(object):
    def __init__(self, file_name, lang, verbose=False):
        self.debug = True
        self.lang = lang
        self.verbose = verbose
        self.indent_n = 4

        self.new_exts = []
        self.exts_remove = []
        self.exts_processed = []  # single list of package names
        self.exts_dict = {}  # 'action'
        self.prolog = '## remove ##\n'
        self.indent = ' ' * self.indent_n
        self.pkg_top = None
        eb = imp.new_module("easyconfig")

        """ interpreting easyconfig files fail due to missing constants that are not defined within the
            easyconfig file.  Add undefined constants here. """
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
        for item in self.exts_orig:
            self.exts_dict[item[0]] = {}
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
            if self.debug:
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
                self.check_package(pkg)
            else:
                self.new_exts.append(pkg)

    def pkg_match(self, indx, new_p):
        if new_p[0] == self.exts_orig[indx][0]:
            return True
        else:
            return False

    def write_to_eor(self):
        indx = self.code[self.ptr_head:].find('),\n')
        ptr_tail = self.ptr_head + indx + 1
        self.out.write(self.code[self.ptr_head:ptr_tail])
        return ptr_tail

    def skip_extension(self, indx):
        """ indx points to head of extension name; ASUME: exts_list entry ends with '),\n'
        """
        back = self.code.rfind('),\n', 0, indx) + 3
        self.out.write(self.code[self.ptr_head:back] + '<-')
        return self.code[indx:].find('),\n') + indx + 3

    def write_chunk(self, indx, obj_len):
        ptr_tail = indx + obj_len
        self.out.write(self.code[self.ptr_head:ptr_tail])
        return ptr_tail

    def source_url(self, pkg_name):
        """ determin which source_url should be used for a "new" module. """
        if self.exts_dict[pkg_name]['source'] == 'cran':
            options = 'ext_option'
        elif self.exts_dict[pkg_name]['source'] == 'biocondutor':
            options = 'bioconductor_options'
        elif self.exts_dict[pkg_name]['source'] == 'pypi':
            options = "{'source_urls': ['https://pypi.python.org/packages/source/%s/%s/']}" % (
                pkg_name[:1], pkg_name)
        else:
            options = "{'source_urls': ['unknow']}"
        return options

    def print_update(self):
        """ this needs to be re-written correctly
            use source text as pattern
        """
        self.out = open(self.pkg_name + ".update", 'w')
        indx = self.code.find('exts_list')
        self.ptr_head = self.write_chunk(indx, len('exts_list'))
        for new_p in self.new_exts:
            if isinstance(new_p, str):  # base library with no version
                self.ptr_head = self.write_chunk(indx, len(new_p[0]))
                continue
            action = self.exts_dict[new_p[0]]['action']
            print "processing: " + new_p[0] + " - " + action
            if action == 'keep' or action == 'update':
                indx = self.code[self.ptr_head:].find(new_p[0])
                self.ptr_head = self.write_chunk(indx, len(new_p[0]))
                indx = self.code[self.ptr_head:].find(new_p[1])
                if self.exts_dict[new_p[0]]['action'] == 'update':
                    self.out.write(self.code[self.ptr_head:self.ptr_head + indx])
                    self.out.write(new_p[1])
                    self.ptr_head += (indx + len(new_p[1]))
            elif action == 'duplicate':
                indx = self.code[self.ptr_head:].find(new_p[0])
                self.ptr_head = self.skip_extension(indx)
                print " Duplicate: ", new_p[0]
            elif action == 'new':
                self.ptr_head = self.write_to_eor()
                options = self.source_url(new_p[0])
                if self.bioconductor and self.exts_dict[new_p[0]]['source'] == 'cran':
                    print " CRAN depencancy: " + new_p[0]
                else:
                    extension = "%s('%s', '%s', %s),\n" % (self.indent, new_p[0], new_p[1], options)
                    self.out.write(extension)
                    self.ptr_head += len(extension)
        self.out.write(self.code[self.ptr_head:])

    def check_package(self, pkg):
        pass


class R(ExtsList):
    depend_exclude = {'R', 'parallel', 'methods', 'utils', 'stats', 'stats4', 'graphics', 'grDevices',
                      'tools', 'tcltk'}

    def __init__(self, file_name, verbose=False):
        ExtsList.__init__(self, file_name, 'R', verbose)

    def check_CRAN(self, pkg):
        if self.debug:
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
                self.exts_dict[pkg[0]]['action'] = 'duplicate'
            return
        if self.bioconductor:
            pkg_ver, depends = self.check_BioC(pkg)
            source = 'bioconductor'
            if pkg_ver == 'not found':
                pkg_ver, depends = self.check_CRAN(pkg)
                source = 'cran'
        else:
            pkg_ver, depends = self.check_CRAN(pkg)
            source = 'cran'

        if pkg_ver == "error" or pkg_ver == 'not found':
            if pkg[0] == self.pkg_top:
                self.exts_dict[pkg[0]]['action'] = 'remove'
            return

        if pkg[0] == self.pkg_top:
            if pkg[1] == pkg_ver:
                self.exts_dict[pkg[0]]['action'] = 'keep'
            else:
                self.exts_dict[pkg[0]]['action'] = 'update'
        else:
            self.exts_dict[pkg[0]] = {}
            self.exts_dict[pkg[0]]['action'] = 'new'
            self.exts_dict[pkg[0]]['source'] = source

        for depend in depends:
            if depend not in self.depend_exclude:
                self.check_package([depend, ''])
        self.new_exts.append([pkg[0], pkg_ver])
        self.exts_processed.append(pkg[0])
        if self.verbose:
            if self.exts_dict[pkg[0]]['action'] == 'new':
                print "%20s : %-8s (%s-%s)" % (pkg[0], pkg_ver, self.exts_dict[pkg[0]]['action'],
                                                  self.exts_dict[pkg[0]]['source'])
            else:
                print "%20s : %-8s (%s)" % (pkg[0], pkg_ver, self.exts_dict[pkg[0]]['action'])


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
    # r = R('R-3.3.1-test.eb', verbose=True)
    # r.update_exts()
    # r.print_update()

    r = R('R-bundle-Bioconductor-3.3-foss-2016b-R-3.3.1-fh1.eb', verbose=True)
    r.update_exts()
    r.print_update()
