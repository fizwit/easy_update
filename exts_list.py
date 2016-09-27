#!/usr/bin/env python

import imp
import sys
import json, requests


class exts_list(object):
    def __init__(self, file_name, lang, verbose=False):
        self.lang = lang
        self.verbose = verbose
        self.indent_n = 4

        self.new_exts = []
        self.exts_remove = []
        self.new_list = [] #single list of package names
        self.prolog = '## remove ##\n'
        self.indent = ' ' * self.indent_n
        eb = imp.new_module("easyconfig")

        self.code = 'SOURCE_TGZ  = "%(name)s-%(version)s.tgz"\n\
SOURCE_TAR_GZ = "%(name)s-%(version)s.tar.gz"\n' + self.prolog

        with open(file_name, "r") as f:
            self.code += f.read()
        try:
            exec (self.code, eb.__dict__)
        except  Exception, e:
            print "interperting easyconfig error: %s" % (e)

        self.exts_orig = eb.exts_list
        self.exts_orig2 = [item[0] for item in self.exts_orig]
        self.pkg_name = eb.name + '-' + eb.version + '-' + eb.toolchain['name'] + '-' + eb.toolchain['version']
        # Add extension if exists
        print "Package:", self.pkg_name

    def print_code(self):
        print self.code

    def update_exts(self):
        for pkg in self.exts_orig:
            if isinstance(pkg, tuple):
                self.check_package(pkg[0])
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
        i = 0
        for new_p in self.new_exts:
            indx = self.code[ptr_head:].find(new_p[0])
            if isinstance(new_p, str):  # base library with no version
                i += 1
                ptr_head = self.write_chunk(ptr_head,indx,len(new_p[0]))
                continue
            if new_p[0] == self.exts_orig[i][0]:
                ptr_head = self.write_chunk(ptr_head, indx, len(new_p[0]))
                indx = self.code[ptr_head:].find(self.exts_orig[i][1])
                if new_p[1] == self.exts_orig[i][1]:
                    ptr_head = self.write_chunk(ptr_head,indx,len(self.exts_orig[i][1]))
                else:
                    self.out.write(self.code[ptr_head:ptr_head + indx])
                    self.out.write(new_p[1])
                    ptr_head += (indx +len(new_p[1]))
                if i < len(self.exts_orig2):
                    i += 1
            elif self.exts_orig[i][0] in self.new_list and (  # duplicate case
                new_p[0] in self.exts_orig2[i:]):
                i += 1
                ptr_head = self.write_to_eol(ptr_head)
            else: # new package
                ptr_head = self.write_to_eol(ptr_head)
                self.out.write("%s('%s', '%s', ext_options),\n" % (self.indent, new_p[0], new_p[1]))
        self.out.write(self.code[ptr_head:])

    def test_pkg(self,indx, new_p):
        if new_p[0] == self.exts_orig[indx][0]:
            if new_p[1] != self.exts_orig[indx][1]:
                print ">%20s %-15s | %20s %s" % (self.exts_orig[indx][0], self.exts_orig[indx][1],
                                                 new_p[0], new_p[1])
            else:
                print " %20s %-15s | %20s %s" % (self.exts_orig[indx][0], self.exts_orig[indx][1],
                                                 new_p[0], new_p[1])
            return True
        else:
            return False

    def print_diff(self):
        i = 0
        for new_p in self.new_exts:
            if isinstance(new_p, str):  #remove base libraries
                i += 1
                continue
            if self.test_pkg(i, new_p):
                if i < len(self.exts_orig):
                    i += 1
            elif self.exts_orig[i][0] not in self.new_list:  # remove
                print "-%20s %-15s | %20s %s" % (self.exts_orig[i][0], self.exts_orig[i][1], '', '')
                if self.test_pkg(i+1, new_p):
                    i += 2
                else:
                    i += 1  # badness
            elif self.exts_orig[i][0] in self.new_list and (  # duplicate case
                new_p[0] in self.exts_orig2[i:]):
                next_ext = self.exts_orig2[i:].index(new_p[0])
                for j in range(i,i+next_ext):
                    print "*%20s %-15s | %20s %s" % (self.exts_orig[i][0], self.exts_orig[i][1],'','')
                if self.test_pkg(i+1, new_p):
                    if i+1 < len(self.exts_orig):
                        i += 2
            else:  # new package
                print "+%20s %-15s | %20s %s" % ('', '', new_p[0], new_p[1])

class R(exts_list):
    cran_list = "http://crandb.r-pkg.org/"
    depend_exclude = ['R', 'parallel', 'methods', 'utils', 'stats', 'stats4','graphics', 'grDevices',
                      'tools', 'tcltk']

    def __init__(self, file_name, verbose=False):
        exts_list.__init__(self, file_name, 'R', verbose)
        exts_list.url_list = R.cran_list

    def check_package(self, pkg_name):
        if pkg_name in self.new_list:
            return
        resp = requests.get(url=self.cran_list + pkg_name)
        cran_info = json.loads(resp.text)
        if 'error' in cran_info and cran_info['error'] == 'not_found':
            self.exts_remove.append(pkg_name)
            return
        try:
            pkg_ver = cran_info[u'Version']
        except KeyError, e:
            self.exts_remove.append(pkg_name)
            return
        if u"Depends" in cran_info:
            for depend in cran_info[u'Depends'].keys():
                if depend not in self.depend_exclude:
                    self.check_package(depend)
        self.new_exts.append([pkg_name, pkg_ver])
        self.new_list.append(pkg_name)
        if self.verbose:
            print "%20s : %s" % (pkg_name, pkg_ver)

class Python_exts(exts_list):
    def __init__(self, file_name):
        exts_list.__init__(self, file_name, 'Python')

    def check_package(self, pkg_name):
        if pkg_name in self.pkg_dict:
            return []
        client = xmlrpclib.ServerProxy('https://pypi.python.org/pypi')
        xml_vers = client.package_releases(package)
        if xml_vers:
            self.pkg_dict[package] = [xml_vers[0]]
            xml_info = client.release_data(package, xml_vers[0])
            if 'requires_dist' in xml_info:
                req = parse_pypi_requires(xml_info['requires_dist'])
                if req:
                    py_dict[package].append(req)
                    # print("requires_dist:",req)
        else:
            print("Warning: could not find Python package:", package)
            py_dict[package] = []
