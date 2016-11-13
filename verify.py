#!/usr/bin/env python

import sys
import imp
import json
import os
import requests
import urllib2
import xmlrpclib

def verifyName(file_name ):
        eb = imp.new_module("easyconfig")
        """ interpreting easyconfig files fail due to missing constants that are not defined within the
            easyconfig file.  Add undefined constants here.
        """
        header = 'SOURCE_TGZ  = "%(name)s-%(version)s.tgz"\n'
        header += 'SOURCE_TAR_GZ = "%(name)s-%(version)s.tar.gz"\n'
        header += 'SOURCELOWER_TAR_GZ = "%(name)s-%(version)s.tar.gz"\n'
        ptr_head = len(header)
        code = header

        try:
            f = open(file_name, "r")
        except IOError as e:
            sys.exit(e)
        else:
            with f:
                code += f.read()

        try:
            exec (code, eb.__dict__)
        except Exception, e:
            print "interperting easyconfig error: %s" % e

        pkg_name = eb.name + '-' + eb.version
        if eb.toolchain['name'] != 'dummy':
            pkg_name += '-' + eb.toolchain['name'] + '-' + eb.toolchain['version']
        try:
            pkg_name += eb.versionsuffix
        except (AttributeError, NameError):
            pass
        return pkg_name

if __name__ == '__main__':
    if len(sys.argv) != 2:
        print "usage: %s [easybuild easyconfig]" % sys.argv[0]
        sys.exit(0)

    file_name = os.path.basename(sys.argv[1])[:-3]
    module_name = verifyName(sys.argv[1])
    if module_name != file_name: 
        print "Module names do not match"
    else:
        print "match!"
    print "Module name: ", module_name
    print "File name:   ", file_name
