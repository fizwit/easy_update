#!/usr/bin/env python

import imp
import sys 
import json,requests

class exts_list(object):

    def __init__(self, file_name, lang):
        self.lang = lang
        self.pkg_dict = {}
 
        self.eb = imp.new_module("easyconfig")

        self.code = 'SOURCE_TGZ  = "{%name}{$version}.tgz"'
        with open(file_name, "r") as f:
            self.code += f.read() 

        try:
            exec(self.code, self.eb.__dict__)
        except  Exception, e:
            print "interperting easyconfig error: %s" % (e)
        self.exts_list = self.eb.exts_list
        
    def print_ext_list(self):
        for pkg in self.exts_list:
            print "%16s %s" % (pkg[0], pkg[1])

class R(exts_list):

    def __init__(self,filename):
        exts_list.__init__(self, file_name, 'R')

    url_list = "http://crandb.r-pkg.org/"
    def check_package(self,pkg_name):
        resp=requests.get(url=cran_url+package)
        data=json.loads(resp.text)
        version = [data[u'Version']]
class Python_exts(exts_list):
    
    def __init__(self,file_name):
        exts_list.__init__(self,file_name, 'Python')
    
    def check_package(self,pkg_name):
        if pkg_name in self.pkg_dict:
            return []
        client=xmlrpclib.ServerProxy('https://pypi.python.org/pypi')
        xml_vers=client.package_releases(package)
        if xml_vers:
           self.pkg_dict[package]=[xml_vers[0]]
           xml_info=client.release_data(package,xml_vers[0])
           if 'requires_dist' in xml_info:
              req=parse_pypi_requires(xml_info['requires_dist'])
              if req:
                 py_dict[package].append(req)
                 #print("requires_dist:",req)
        else:
            print("Warning: could not find Python package:",package)
            py_dict[package]=[]               

