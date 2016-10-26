#!/usr/bin/env python

import imp
import sys
import json, requests
import urllib2


class exts_list(object):
    def __init__(self, file_name, lang, verbose=False):
        self.debug = True
        self.lang = lang
        self.verbose = verbose
        self.indent_n = 4

        self.new_exts = []
        self.exts_remove = []
        self.exts_processed = [] #single list of package names
        self.exts_dict = {}  # 'action'
        self.prolog = '## remove ##\n'
        self.indent = ' ' * self.indent_n
        eb = imp.new_module("easyconfig")

        self.code = 'SOURCE_TGZ  = "%(name)s-%(version)s.tgz"\n'
        self.code += 'SOURCE_TAR_GZ = "%(name)s-%(version)s.tar.gz"\n'
        self.code += self.prolog
        self.head_ptr = len(self.code)

        with open(file_name, "r") as f:
            self.code += f.read()
        try:
            exec (self.code, eb.__dict__)
        except  Exception, e:
            print "interperting easyconfig error: %s" % (e)

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
            self.bioc_data = []
            if self.debug:
                bioc_files = ['packages.json', 'annotation.json', 'experiment.json']
                for file in bioc_files:
                    json_data = open(file).read()
                    self.bioc_data.append(json.loads(json_data))
            else:
                bioc_urls = {'https://bioconductor.org/packages/json/3.3/bioc/packages.json',
                            'https://bioconductor.org/packages/json/3.3/data/annotation/packages.json',
                            'https://bioconductor.org/packages/json/3.3/data/experiment/packages.json'}
                self.bioc_data = []
                for url in bioc_urls:
                    response = urllib2.urlopen(url)
                    self.bioc_data.append(json.loads(response.read()))




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

    def write_to_eol(self,ptr_head):
        indx = self.code[ptr_head:].find('\n')
        ptr_tail = ptr_head + indx + 1
        self.out.write(self.code[ptr_head:ptr_tail])
        return ptr_tail

    def write_chunk(self,ptr_head, indx, obj_len):
        ptr_tail = ptr_head + indx + obj_len
        self.out.write(self.code[ptr_head:ptr_tail])
        return ptr_tail

    def print_update(self):
        """ this needs to be re-written correctly
            use source text as pattern
        """
        self.out = open(self.pkg_name + ".update", 'w')
        indx = self.code.find(self.prolog)
        ptr_head = indx + len(self.prolog)
        exts_cnt = len(self.exts_orig)
        i = 0
        for new_p in self.new_exts:
            indx = self.code[ptr_head:].find(new_p[0])
            if isinstance(new_p, str):  # base library with no version
                i += 1
                ptr_head = self.write_chunk(ptr_head,indx,len(new_p[0]))
                continue
            if i < exts_cnt and new_p[0] == self.exts_orig[i][0]:  # adds stuff to bottom
                ptr_head = self.write_chunk(ptr_head, indx, len(new_p[0]))
                indx = self.code[ptr_head:].find(self.exts_orig[i][1])
                if self.exts_dict[new_p[0]]['action'] == 'keep':
                    ptr_head = self.write_chunk(ptr_head,indx,len(self.exts_orig[i][1]))
                else:
                    self.out.write(self.code[ptr_head:ptr_head + indx])
                    self.out.write(new_p[1])
                    ptr_head += (indx +len(new_p[1]))
                if i < len(self.exts_orig):
                    i += 1
            elif i < exts_cnt and self.exts_orig[i][0] in self.exts_processed and (  # duplicate case
                new_p[0] in self.exts_orig[i:]):
                i += 1
                ptr_head = self.write_to_eol(ptr_head)
            else: # new package
                ptr_head = self.write_to_eol(ptr_head)
                if self.exts_dict[new_p[0]]['action'] == 'new':
                    if self.exts_dict[new_p[0]]['source'] == 'cran':
                        options = 'ext_option'
                    else:
                        options = 'bioconductor_options'
                else:
                    options = 'new'
                self.out.write("%s('%s', '%s', %s),\n" % (self.indent, new_p[0], new_p[1], options))
        self.out.write(self.code[ptr_head:])

class R(exts_list):
    depend_exclude = {'R', 'parallel', 'methods', 'utils', 'stats', 'stats4', 'graphics', 'grDevices',
                      'tools', 'tcltk'}

    def __init__(self, file_name, verbose=False):
        exts_list.__init__(self, file_name, 'R', verbose)

    def check_CRAN(self,pkg):
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
        pkg_ver = None
        for info in self.bioc_data:
            if pkg[0] in info:
                pkg_ver = info[pkg[0]]['Version']
                dep_temp = []
                if 'Depends' in info[pkg[0]]:
                    dep_temp = info[pkg[0]]['Depends']
                break
        if not pkg_ver:
            print pkg[0], " Not found at BioCondutor"
            return "not found", []
        depends = [s.split(' ')[0] for s in dep_temp]
        self.new_exts.append([pkg[0], pkg_ver])
        self.exts_processed.append(pkg[0])
        return pkg_ver, depends

    def check_package(self, pkg):
        if pkg[0] in self.exts_processed:  # remove dupicates
            return
        if self.bioconductor:
            exts_list = 'bioconductor_options'
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

class Python_exts(exts_list):
    def __init__(self, file_name):
        exts_list.__init__(self, file_name, 'Python')

    def parse_pypi_requires(self,requires):
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
    #r = R('R-3.3.1-test.eb', verbose=True)
    #r.update_exts()
    #r.print_update()

    r = R('R-bundle-Bioconductor-3.3-foss-2016b-R-3.3.1-fh1.eb', verbose=True)
    r.update_exts()
    r.print_update()
