#!/usr/bin/env python

import sys
#
# verify syntax and module location of Python modules
# Use PyPi API to track Python modules
#
# Helper routine for building Python-X.X.X easyconfigs
#
# copy Python easyconfig to local directory and rename easyconfig.py
#
# Pip XML API docs https://warehouse.pypa.io/api-reference/xml-rpc/ 

import xmlrpclib

# return highest version level of package
# Package name must be correct and existist, package names are case sensitive
# if Package name does not exist return Null else return string containing version

client = xmlrpclib.ServerProxy('https://pypi.python.org/pypi')

def get_version(name):
     version = client.package_releases(name)
     if not version:
        print '# ', name, ' is not found'
        return '' 
     return version[0]

def get_release(name, version):
    info = client.release_data(name, version)
    if not info:
        print '# Error release data not found: ', name    
    else:
        print '================  ', name, '  ================'
        print 'summary: ', info['summary']
        print 'description: ', info['description']

def get_url(name, version):
     info = client.release_urls(name, version)
     found = False
     for url in info:
         if url['url'].endswith('.gz'):
             print 'wget ', url['url']
             found = True
             break
     if not found:
        print '# Error url not found! ',name, ': ',version
        return {}
     else:
        return url


def main():
    if len(sys.argv) < 2:
       print "usage package name"
       sys.exit()
    package = sys.argv[1]
    version = get_version(package)
    url = get_url(package, version)
    print "%s (%s)" % (package, version )

if __name__ == "__main__":
    main()
