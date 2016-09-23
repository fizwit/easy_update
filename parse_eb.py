#!/usr/bin/env python

import imp
import sys 

def read_easyconfig(file):
    eb = imp.new_module("easyconfig")

    with open(file, "r") as f:
        code = f.read() 

    exec(code, eb.__dict__)
    return eb, code

              
class exts(object):

    def __init__(self,lang,eb,source):
        self.lang = lang
        self.pkg_dict = {}
 
    def rewrite_easyconfig(exts, code):
        not_exts_list=True
        dump = True 

        for line in code.split("\n"):
            if not_exts_list:
                if "exts_list" in line:
                    not_exts_list=False
                print line
            else:
               if "]" in  line:
                  not_exts_list=True
               elif dump:
                   for p in exts:
                       print "('%s', '%s')" % (p[0], p[1]) 
                   dump = False

class R(exts):

    def __init__(self,eb,source):
        exts.__init__(self,'R',eb,source)

    def check_package(pkg_name):
        pass

class Python_exts(exts):
    
    def __init__(self,eb,source):
        exts.__init__(self,'R',eb,source)

    
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

def main(eb_file):
    (eb, source) = read_easyconfig(eb_file)
    if eb.name == 'R-bundle-Bioconductor'
       type = 'R'
    elif eb.name == 'R'
       type = 'R'
    elif eb.name == 'Python'
       type = 'Python'
       p = Python_exts()
    pkgs = p.check_exts(eb.exts_list)
 
if __name__ == "__main__":
    if len(sys.argv) < 2:
       print "usage: %s easyconfig.eb" % sys.argv[0]
    else:
       main(sys.argv[1])
