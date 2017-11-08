#!/usr/bin/env python

import re
import os
import sys
import imp
import json
import urllib2
import xmlrpclib
from argparse import ArgumentParser
import sys


installed = []

def http_get(URL, file_name):
    """ download URL save to filename"""
    u = urllib2.urlopen(URL)
    meta = u.info()
    f = open(file_name, 'wb')
    file_size = int(meta.getheaders("Content-Length")[0])
    print "Downloading: %s Bytes: %s" % (file_name, file_size)
    
    file_size_dl = 0
    block_sz = 8192
    while True:
        buffer = u.read(block_sz)
        if not buffer:
            break
    
        file_size_dl += len(buffer)
        f.write(buffer)
    f.close()


def parse_pypi_requires(pkg_name, requires, args):
    """ pip requirement specifier is defined in full in PEP 508
        The project name is the only required portion of a requirement string. 

        Test that <python_version> and <sys_platform> conform.
        If <extra> is present and required check that extra is contained in "exts_list".
        
        We only care about the package name so ignore all version information
        input: 'numpy (>=1.7.1)'  output: ['numpy', '']
        badness:
            psutil (<2.0.0,>=1.1.1)
            netaddr (!=0.7.16,>=0.7.13)
            requests>=2.0    # no delimiters at all
            apscheduler  != APScheduler
    """
    python_version = '2.7'
    sys_platform = 'Linux'
    extra = ''
    require_re = '^([A-Za-z0-9_\-\.]+)(?:.*)$'
    extra_re =   "and\sextra\s==\s'([A-Za-z0-9_\-\.]+)'"  # only if the 
    targets = ['python_version', 'sys_platform', 'extra'] 
    ans = re.search(require_re, requires)
    name = ans.group(1)
    test = False    # do we need to test extra requires field?
    state = True

    version = requires.split(';')
    if len(version) > 1:
        for target in targets:
            if target in version[1]:
                 test = True
                 if target == 'extra':
                     extra = re.search(extra_re, version[1])
                     extra = extra.group(1) if extra else None
        if test:
            state = eval(version[1])
    if state:
        if name in installed:
           return None
        installed.append(name)
        if args.verbose:
            print('depend: package: %s, eval: %r, Expression: %s' % (
                  name, state, requires) )
        return name
    else:
        if args.verbose:
            print('No install: depend: package: %s, eval: %r, Expression: %s' % (
                  name, state, requires) )
        return None

def get_pypi_info(client, pkg_name):
    """Python pypi API for package version and dependancy list 
       pkg is a list; ['package name', 'version', 'other stuff']
       return the version number for the package and a list of dependancie
    """
    ver_list = client.package_releases(pkg_name)
    if len(ver_list) == 0:
        search_list = client.search({'name': pkg_name})
        for info in search_list:
            if pkg_name.lower() == info['name'].lower():
                 pkg_name = info['name']
                 break
            if pkg_name.replace('-','_') == info['name'].lower() or (
               pkg_name.replace('_','-') == info['name'].lower() ):
                 pkg_name = info['name']
                 break
        ver_list = client.package_releases(pkg_name)
        if len(ver_list) == 0:
            return pkg_name, 'not found', None, None 
    version = ver_list[0]
    xml_info = client.release_data(pkg_name, version)
    url_info = client.release_urls(pkg_name, version)
    return pkg_name, version, xml_info, url_info

def get_package_info(client, pkg_name, args):
    indent4 = '    '
    depends = []
    (pkg_name, pkg_ver, xml_info, url_info) = get_pypi_info(client, pkg_name)
    if not xml_info:
        print("# Warning: %s Not in PyPi. No depdancy checking performed" % pkg_name)
        return
    source_tmpl = None
    URL = None
    for url in url_info:
        file_name = url['filename']
        if url['filename'].endswith('tar.gz'):
            URL = url['url']
            break
        if url['filename'].endswith('.zip'): 
            URL = url['url']
            source_tmpl = url['filename'].replace(pkg_name, '%(name)s') 
            source_tmpl = source_tmpl.replace(pkg_ver, '%(version)s') 
            break
    if not URL:
        #  whl could be for any OS.  need to check version and os
        for url in url_info:
            if url['url'].endswith('whl'):
                URL = url['url']
                file_name = url['filename']
        else:
            source_tmpl = None
    if args.wget: 
        print('wget %s' % URL)
        http_get(URL, file_name)
        return
    if args.meta:
        print('Keys: %s' % xml_info.keys() )
    if 'requires_dist' in xml_info.keys():
        for requires in xml_info['requires_dist']:
            pkg_requires = parse_pypi_requires(pkg_name, requires, args)
            if pkg_requires:
                if args.deps:
                    get_package_info(client, pkg_requires, args)
                else:
                    print("  required: %s" % pkg_requires) 
    if args.abs_url:
        url = URL
    else:
        url = "https://pypi.python.org/packages/"
        url += "%s/%s" % (pkg_name[0], pkg_name)
    print("%s('%s', '%s', {" % (indent4, pkg_name, pkg_ver))
    print("%s%s'source_url': ['%s']," % (indent4, indent4, url))
    if source_tmpl:
        print("%s%s'source_tmpl': '%s'," % (indent4, indent4, source_tmpl))
    print("%s})," % indent4 )


if __name__ == '__main__':
    parser = ArgumentParser(description='use Pypi to print dependency list',
                            usage='%(prog)s [options] module_name')
    parser.add_argument('-v', '--verbose', dest='verbose', required=False, 
                        action='store_true',
                        help='Verbose; print lots of extra stuff, (default: false)')
    parser.add_argument('--deps', dest='deps', required=False, 
                        action='store_true',
                        help='resolve all dependencies, (default: false)')
    parser.add_argument('--abs_url', dest='abs_url', required=False, 
                        action='store_true',
                        help='output the full URL from pypi, (default: false)')
    parser.add_argument('--wget', dest='wget', required=False, 
                        action='store_true',
                        help='output the wget command to retrive source package, (default: false)')
    parser.add_argument('--meta', dest='meta', required=False, 
                        action='store_true',
                        help='output all meta data keys from Pypi, (default: false)')
    parser.add_argument('modulename')

    args = parser.parse_args()

    client = xmlrpclib.ServerProxy('https://pypi.python.org/pypi')
    get_package_info(client, args.modulename, args)
