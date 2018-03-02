#!/usr/bin/env python
import os
import sys
import getopt
import json
import ssl
from datetime import datetime
import requests
try:
    import xmlrpclib
    import urllib2
except ImportError:
    import xmlrpc.client
    import urllib

__author__ = "John Dey"
__version__ = "1.0.1"
__email__ = "jfdey@fredhutch.org"


""" Easy Anotate is a utilty program for documenting Python builds 
    Convert the output of Pip to an html file. 
    This program creates html documentation of extension list.
"""


class pip2html():

    def __init__(self, infile, out, title):
        self.infile = infile
        self.out = out
        self.title = title
        self.mod_list = []
        self.pkg_name = title

        self.html_header()
        self.parse_pip()
        self.write_html_list()

    def parse_pip(self):
        """read pip file and create array of module names"""
        for line in infile:
            name, version = line.split('==')
            url, description = self.get_package_url(name)
            self.mod_list.append({'name': name,
                                  'version': version,
                                  'url': url,
                                  'description': description})
            print('%15s %s' % (name, description))


    def html_header(self):
        """write html head block
        All custom styles are defined here.  No external css is used.
        """
        block = """<!DOCTYPE html>
<html>
<head>
  <title>Fred Hutchinson Cancer Research Center</title>
  <title>EasyBuild Annotate extension list for R, Biocondotor and
 Python easyconfig files</title>
  <style>
    body {font-family: Helvetica,Arial,"Calibri","Lucida Grande",sans-serif;}
    .ext_list a {color: black; text-decoration: none; font-weight: bold;}
    .ext_list li:hover a:hover {color: #89c348;}
    span.fh_green {color: #89c348;}  <!-- Hutch Green -->
  </style>
</head>
<body>
"""
        self.out.write(block)
        self.out.write('<h2><span class="fh_green">%s</span></h2>\n' %
                       self.pkg_name)
        self.out.write('<h3>Package List</h3>\n<div class="ext_list">\n')

    def get_package_url(self, pkg_name):
        client = xmlrpc.client.ServerProxy('https://pypi.python.org/pypi')
        xml_vers = client.package_releases(pkg_name)
        url = description = ''
        if xml_vers:
            version = xml_vers[0]
        else:
            return url, description 
        pkg_data = client.release_data(pkg_name, version)
        if pkg_data and 'summary' in pkg_data:
            description = pkg_data['summary']
        if pkg_data and 'package_url' in pkg_data:
            url = pkg_data['package_url']
        return url, description

    def write_html_list(self):
        self.out.write('  <ul style="list-style-type:none">\n')
        pkg_info = {}
        for pkg in self.mod_list:
            name = pkg['name']
            version = pkg['version']
            url = pkg['url']
            description = pkg['description']
            #if pkg_info[key]['url'] == 'not found':
            #    self.out.write('    <li>%s&emsp;%s</li>\n' %
            #                   (key, pkg_info[key]['version']))
            #else:
            self.out.write('    <li><a href="%s">%s-%s</a>&emsp;%s</li>\n'
                               % (url, name, version, description))
        self.out.write('  </ul>\n</div>\n')
        self.out.write('  updated: %s\n' %
                       "{:%B %d, %Y}".format(datetime.now()))
        self.out.write('</body></html>\n')


def help():
    print('--title Module Name')
    print('--out OutputFileName')

if __name__ == '__main__':
    myopts, args = getopt.getopt(sys.argv[1:], "",
                                 ['verbose',
                                  'title=',
                                  'out=',
                                  ])
    if len(args) == 0:
        print('must speicify an input file name')
        sys.exit(1)

    title = ''
    outfile = sys.stdout
    for opt, arg in myopts:
        if opt == "--help":
            help()
            sys.exit(0)
        elif opt == "--title":
            title = arg
        elif opt == "--out":
            try:
                outfile = open(arg, 'w')
            except:
                print('open file failed: %s' % arg)
                sys.exit(1)

    infile = open('/home/jfdey/requirements.txt', 'r')
    method = pip2html(infile, outfile, title)
