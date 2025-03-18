#!/usr/bin/env python

import os
import argparse
from datetime import date
import logging

"""
Easy_Annotate creates Markdown documentation from R and Python easyconfigs.
All exts_list packages are documented. If possible the annotation will link
each package to its project page.
"""

""" Release Notes
    2.1.3  report missing directives as error and not debug.
           annotate python modules names
    2.0.4  python.get_package_url -convert to requests
    Python 3.x updates pkgs.keys()  change to list(pkgs)

    2.0.3 Improve dependent package searches for Python easyconfigs to include
    PythonPackages. framework has been updated to check the dependenices for any
    easyconfig with a version suffix of "Python-%(pyver)s". If found locate the
    easyconfig and add the exts_list to dependend packages. Following depenedencies
    will allow a more acurate package listing with hierarchical package structure. 
    Example: Python 3.7.4 -fh1 -> Python 3.7.4 -> pytest, matplotlib ... etc.

    2.0.2 use FrameWork class from easyupdate. Create single document from R and
    Python Packages. Read Dependent module to append exts_list packages, to
    create a single
    document to describe compound Modules.

    Version 2 create Markdown output

    Version 1.x create HTML output
"""

__author__ = "John Dey"
__version__ = "2.1.3"
__date__ = "Aug 26, 2022"
__email__ = "jfdey@fredhutch.org"


class Annotate():
    """ Easy Anotate is a utilty program for documenting EasyBuild easyconfig
    files for R and Python. Easyconfig files for R and Python can have over
    a hundred modules in an ext_list.  This program creates
    html documentation of extension list.
    """

    def __init__(self, easyconfig, verbose, exts_list, dep_exts):
        self.verbose = verbose
        self.easyconfig = easyconfig
        self.easyconfig_name = os.path.basename(easyconfig)        
        self.exts_list = exts_list
        self.dep_exts = dep_exts

    def create_markdown(self):
        """ Create Markdown output file
        """
        self.out = open(self.easyconfig[:-3] + ".md", 'w')
        self.html_header()
        self.exts2md(self.exts_list)
        self.out.write('### Library List from dependent Modules\n')
        self.exts2md(self.dep_exts)
        self.out.close()

    def html_header(self):
        """write html head block
        All custom styles are defined here.  No external css is used.
        """
        today = date.today() 
        date_string = '%d-%02d-%02d' % (today.year, today.month, today.day) 
        block = '---\ntitle: %s\n' % self.easyconfig_name
        block += 'date: %s\n---\n\n' % date_string
        self.out.write(block)
        self.out.write('### Known Issues\n')
        self.out.write(' * None\n\n')
        self.out.write('### Package List\n')

    def exts2md(self, exts_list):
        """ write the output file in Markdown format"""
        pkg_info = {}
        for pkg in exts_list:
            if isinstance(pkg, tuple):
                pkg_name = pkg[0]
                version = str(pkg[1])
                if 'Module' in pkg:
                    url = 'not found'
                    description = 'Module'
                else:
                    url, description = self.get_package_url({'name': pkg_name, 'version': version})
                if self.verbose:
                    print('{}'.format(pkg_name))
            else:
                pkg_name = pkg
                version = 'built in'
                url, description = 'not found', ''
            if pkg_name in ['LCFdata']:
                # fix Windows quote ``something'' to "something"
                description = description.replace('``', '"')
                description = description.replace("''", '"')
            description = description.replace('*', '&#42;')
            pkg_info[pkg_name] = {}
            pkg_info[pkg_name]['version'] = version
            pkg_info[pkg_name]['url'] = url
            pkg_info[pkg_name]['description'] = description
        pkg_list = list(pkg_info)
        pkg_list.sort()
        for key in pkg_list:
            if pkg_info[key]['url'] == 'not found':
                self.out.write('  * %s %s %s\n' % (key,
                                                   pkg_info[key]['version'],
                                                   pkg_info[key]['description']))
            else:
                msg = '  * [%s-%s](%s) %s\n' % (key,
                                                pkg_info[key]['version'],
                                                pkg_info[key]['url'],
                                                pkg_info[key]['description'])
                self.out.write(msg)
