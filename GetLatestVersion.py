#!/usr/bin/env python
import re
import urllib2.request
from html.parser import HTMLParser
# sys.version_info >= (2, 6)


class RParser(HTMLParser):
    """Parse home page of Python.org and search for the latest release"""
    def __init__(self ):
        HTMLParser.__init__(self)
        self.R_re = re.compile('R version (\d*).(\d*).(\d*)')
        self.RversionSting = ''
        self.Rversion = 0
        self.r_data = ''
        self.in_li  = False     # Paragraph tag
        self.found  = False

    def handle_starttag(self, tag, attrs):
        if tag == 'li':
            self.in_li = True

    def handle_data(self, data):
        if self.in_li:
            if 'has been released' in data:
                self.found = True 
            self.r_data += data
        if self.found:
            # MAJOR.MINOR.PATCH
            try:
                (string,major,minor,patch) = self.R_re.match(self.r_data).group(0,1,2,3)
                version = (int(major) * 10000) + (int(minor) * 100) + int(patch)
                if version > self.Rversion:
                     self.Rversion = version
                     self.RversionSting = string
            except AttributeError:
                pass

    def handle_endtag(self, tag):
        if tag == 'li':
            self.in_li = False
            self.found = False
            self.r_data = ''

class PythonParser(HTMLParser):
    """Parse home page of Python.org and search for the latest release"""
    def __init__(self ):
        HTMLParser.__init__(self)
        self.Python2_re = re.compile('Python\s+(2).(\d*).(\d*)')
        self.Python3_re = re.compile('Python\s+(3).(\d*).(\d*)')
        self.Python2version = '' 
        self.Python3version = '' 
        self.in_p  = False     # Paragraph tag
        self.latest = False

    def handle_starttag(self, tag, attrs):
        if tag == 'p':
            self.in_p = True

    def handle_data(self, data):
        if self.in_p:
            if data[:7] == 'Latest:': 
                self.latest = True 
        if self.latest:
            try:
                (string,major,minor,patch) = self.Python2_re.match(data).group(0,1,2,3)
                self.Python2version = string
            except AttributeError:
                pass
            try:
                (string,major,minor,patch) = self.Python3_re.match(data).group(0,1,2,3)
                self.Python3version = string
            except AttributeError:
                pass

    def handle_endtag(self, tag):
        if tag == 'p':
            self.in_p = False
            self.latest = False

p = PythonParser()
f = urllib.request.urlopen("https://python.org")
html = str(f.read())
p.feed(html)
print("Latest: %s" % p.Python2version)
print("Latest: %s"  %p.Python3version)
p.close()

r = RParser()
f = urllib.request.urlopen('https://www.r-project.org/')
html = str(f.read())
r.feed(html)
print("Latest: %s" % r.RversionSting)
r.close
