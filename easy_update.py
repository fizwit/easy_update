#!/usr/bin/env python

import re
import os
import sys
import argparse
import imp
import json
import requests
import urllib2
try:
    import xmlrpclib
except ImportError:
    import xmlrpc.client as xmlrpclib

"""
"""

__version__ = '1.1.0'
__author__ = 'John Dey jfdey@fredhutch.org'
__date__ = 'Mar 2, 2018'

class ExtsList(object):
    """ Extension List Update is a utilty program for maintaining EasyBuild
    easyconfig files for R, Python and Bioconductor.  R, Python and
    Bioconductor langueges support package extensions.  Easyconfig supports
    the building of the language with a list of extions. This program
    automates the the updating of extension lists for R and Python by using
    API for resolving current version for each package.

    command line arguments -> arguments
    --add [file] ->add_packages. add_packages is a list of package names to
          be added to exts_list.
    --check [package name] -> package.  If package is not None just check
            this one package and exit.

    Note: At the FredHutch BioCondutor packages are merged with R.
    An earlier version of easy_update built BioCondutor in a seperate package.

    Issues
       There are many small inconsistancies with PyPI which make it difficult
       to fully automate building of easyconfig files.
       - dependancy checking - check for extras=='all'
       - pypi projects names do not always match module names and or file names
         project: liac-arff, module: arff,  file name: liac_arff.zip
    """
    def __init__(self, args):  # Old:  file_name, add_packages, package, verbose
        self.verbose = args.verbose
        self.debug = False 
        self.meta = args.meta
        self.pkg_top = None 
        self.code = None
        self.ext_list_len = 0
        self.ext_counter = 0
        self.pkg_update = 0
        self.pkg_new = 0
        self.pkg_drop = 0

        self.exts_processed = []  # single list of package names
        self.depend_exclude = []  # built in packages not be added to exts_list
        self.prolog = '## remove ##\n'
        self.ptr_head = 0
        self.indent_n = 4
        self.indent = ' ' * self.indent_n
        self.biocver = None 
        self.checkpackage = False 

        # update easyconfig exts_list or check single package
        if args.easyconfig:
            eb = self.parse_eb(args.easyconfig, primary=True)
            self.exts_orig = eb.exts_list
            self.toolchain = eb.toolchain
            self.version = eb.version
            self.name = eb.name
            self.eb_filename = eb.name + '-' + eb.version
            self.dependencies = eb.dependencies
            self.eb_filename += '-' + eb.toolchain['name']
            self.eb_filename += '-' + eb.toolchain['version']
            try:
                self.eb_filename += eb.versionsuffix
            except NameError:
                print('versionsuffix not defined')
            self.pkg_version = eb.version
            self.check_package_name(args.easyconfig)
            try: 
                self.biocver = eb.biocver
                print('biocver: %s' % self.biocver)
            except:
                pass
            if args.add_pkg:
                self.get_package_list(args.add_pkg) 
            self.out = open(self.eb_filename + ".update", 'w')
        elif args.pkg_name:
            if args.pyver:
                self.name = "Python"
                self.version = args.pyver
            elif args.rver:
                self.name = "R"
                self.version = args.rver
            else:
                print('Languange and version must be specified with ' +
                      '[--pyver x.x | --rver x.x | --biocver x.x]')
            if args.biocver:
                self.biocver = args.biocver
            self.checkpackage = True
            d = {'state': 'top', 'action': 'add'}
            self.exts_orig = [(args.pkg_name, 'x', d)]


    def parse_eb(self, file_name, primary):
        """ interpret easyconfig file with 'exec'.  Interperting fails if
        constants that are not defined within the easyconfig file.  Add
        undefined constants to <header>.
        """
        header = 'SOURCE_TGZ  = "%(name)s-%(version)s.tgz"\n'
        header += 'SOURCE_TAR_GZ = "%(name)s-%(version)s.tar.gz"\n'
        header += self.prolog
        code = header

        eb = imp.new_module("easyconfig")
        with open(file_name, "r") as f:
            code += f.read()
        try:
            exec (code, eb.__dict__)
        except Exception as err:
            print("interperting easyconfig error: %s" % err)
            sys.exit(1)
        if primary:     # save original text of source code
            self.code = code
            self.ptr_head = len(header)
        return eb

    def get_package_list(self, fname):
        """read package names from <fname>
        add packages to exts_list to be checked. 
        """
        with open(fname, "r") as pkg_file:
            for pkg in pkg_file:
                d = {'state': 'top', 'action': 'add'}
                self.exts_orig.append((pkg, 'x', d))


    def check_package_name(self, easyconfig):
        """" check that easybuild filename matches package name
        easyconfig is filename of easyconfig file
        """
        f_name = os.path.basename(easyconfig)[:-3]
        if f_name != self.eb_filename:
            sys.stderr.write("Warning: file name does not match easybuild " +
                             "module name\n"),
            sys.stderr.write(" file name: %s, module name: %s\n" % (
                             f_name, self.eb_filename))
            sys.stderr.write('Writing output to: %s' % self.eb_filename +
                             '.update\n')


    def get_package_info(self, pkg):
        """base class 
        subclasses of <get_package_info> search CRAN, Pypi or Bioconductor
        based on easyconfig.
        input: pkg - list [pkg_name, pkg_version, dict]
        return: msg, tuble[pkg name, version, dict], depends[]
        <depends> list of package names that are dependancies
        look hard for dependant packages, try to match different cases
        and interchange underscore and dash.  If input package_name
        does not match rewrite pkg[0] with name found from repository.
        """
        pass

    def is_processed(self, pkg_name):
        if pkg_name in [i[0] for i in self.exts_processed] or (
           pkg_name in self.depend_exclude):
            return True
        else:
            return False

    def check_package(self, pkg):
        """query package authority [Pypi, CRAN, Bio] to get the latest version
        information for a package. This is heart of the program.

        input: pkg - list [pkg_name, pkg_version, dict]
        check that all dependancies are meet for each package.
        check_package can be called recursivly.
        dict['state'] is used to track status.
          - 'top' is also used to track recursion
          - 'dep' package that is added as result of dependancy
        dict['action'] What action will be take to exts_list.
          - 'add'; new package
          - 'keep'; no update required
          - 'update'; version change
          - 'duplicate' package appears twice
          - 'dep' or 'add' write new record to exts_list
        """
        if self.debug: print('check_package: %s: %s' % (pkg[0], json.dumps(pkg[2])))
        if self.is_processed(pkg[0]):
            if pkg[2]['state'] == 'top':
                pkg[2]['action'] = 'duplicate'
                self.exts_processed.append(pkg)
            return
        msg, result, depends = self.get_package_info(pkg)
        if self.debug: print('check_package; msg: %s result: %s' % (msg, result))
        if msg == "error" or msg == 'not found':
            if pkg[2]['state'] == 'top':
                pkg[2]['action'] = 'keep'
                self.exts_processed.append(pkg)
                return
            else:
                #self.pkg_drop += 1
                msg = "Warning: package %s is a dependency of %s, but "
                msg += "can't be found!"
                print(msg % (pkg[0], self.pkg_top))
                return

        if pkg[0] != result[0]:  # name mismatch, this is a Python issue
            print("Warning: name mismatch %s -> %s" % (pkg[0], result[0]))
            if self.is_processed(result[0]):
                 return

        if pkg[1] == result[1]:
            pkg[2]['action'] = 'keep'
        else:
            orig_ver = pkg[1]
            pkg[1] = result[1] 
            self.pkg_update += 1
            if pkg[2]['action'] == 'orig': 
                pkg[2]['action'] = 'update'
            elif pkg[2]['action'] == 'dep' or pkg[2]['action'] == 'add':
                if self.debug: print('check_package; dep or add')
                if self.name == "Python":
                    templ = "['https://pypi.python.org/packages/source/%s/%s']"
                    url = templ % (result[0][0], result[0])
                    pkg[2]['source_urls'] = url
                    self.pkg_new += 1

        for depend in depends:
            if depend not in self.depend_exclude:
                d = {'state': 'dep', 'action': 'dep'}
                self.check_package([depend, 'x', d])
        self.exts_processed.append(pkg)
        self.ext_counter += 1
        if self.debug: print('check_package; checkpackage:', self.checkpackage)
        if self.checkpackage:
            output = self.output_module(pkg)
            print(output)
        if self.verbose:
            if pkg[2]['action'] == 'update':
                version = '%s -> %s' % (orig_ver, pkg[1])
            else:
                version = pkg[1]
            action = '(%s)' % pkg[2]['action']
            tmpl = "%20s : %-20s %12s [%2d, %d]"
            print(tmpl % (pkg[0], version, action,
                          self.ext_list_len, self.ext_counter))

    def update_exts(self):
        """Loop through exts_list and check which packages need to be updated.
        this is an external method for the class
        """
        self.ext_list_len = len(self.exts_orig)
        for pkg in self.exts_orig:
            if isinstance(pkg, tuple):
                pkg[2]['state'] = 'top'
                if 'action' not in pkg[2]:
                    pkg[2]['action'] = 'orig'
                self.check_package(list(pkg))
            else:
                self.exts_processed.append(pkg)

    def write_chunk(self, indx):
        self.out.write(self.code[self.ptr_head:indx])
        self.ptr_head = indx

    def rewrite_extension(self, pkg):
        name_indx = self.code[self.ptr_head:].find(pkg[0])
        name_indx += self.ptr_head + len(pkg[0]) + 1
        indx = self.code[name_indx:].find("'") + name_indx + 1
        self.write_chunk(indx)
        self.out.write("%s'," % pkg[1])  # write version Number
        self.ptr_head = self.code[self.ptr_head:].find(',') + (
                        self.ptr_head + 1)
        indx = self.code[self.ptr_head:].find('),') + self.ptr_head + 3
        self.write_chunk(indx)


    def output_module(self, pkg):
        """
        """
        
    def print_update(self):
        """ this needs to be re-written in a Pythonesque manor
        """
        indx = self.code.find('exts_list')
        indx += self.code[indx:].find('[')
        indx += self.code[indx:].find('\n') + 1
        self.write_chunk(indx)

        for extension in self.exts_processed:
            if isinstance(extension, str):  # base library with no version
                indx = self.code[self.ptr_head:].find(extension)
                indx += self.ptr_head + len(extension) + 2
                self.write_chunk(indx)
                continue
            action = extension[2]['action'] 
            # del extension[2]['action']
            # del extension[2]['state'] 
            if action == 'keep' or action == 'update':
                self.rewrite_extension(extension)
                # sys.exit(0)
            elif action == 'duplicate':
                print("duplicate: %s" % extension[0])
                name_indx = self.code[self.ptr_head:].find(extension[0])
                name_indx += self.ptr_head + len(extension[0])
                indx = self.code[name_indx:].find('),') + name_indx + 3
                self.ptr_head = indx
                continue
            elif action == 'add' or action == 'dep':
                output = self.output_module(extension)
                self.out.write("%s\n" % output) 
        self.out.write(self.code[self.ptr_head:])
        print("Updated Packages: %d" % self.pkg_update)
        print("New Packages: %d" % self.pkg_new)
        print("Dropped Packages: %d" % self.pkg_drop)


class R(ExtsList):
    """extend ExtsList class to update package names from CRAN
    """
    def __init__(self, args):
        ExtsList.__init__(self, args)
        self.bioc_data = {}
        self.depend_exclude = ['R', 'parallel', 'methods', 'utils', 'stats',
                               'stats4', 'graphics', 'grDevices', 'tools',
                               'tcltk', 'grid', 'splines', 'compiler' ]
        if self.biocver:
            self.read_bioconductor_pacakges()
        else:
            print('BioCondutor verserion: biocver not set')

    def read_bioconductor_pacakges(self):
        """ read the Bioconductor package list into bio_data dict
        """
        base_url = 'https://bioconductor.org/packages/json/%s' % self.biocver
        bioc_urls = ['%s/bioc/packages.json' % base_url,
                     '%s/data/annotation/packages.json' % base_url,
                     '%s/data/experiment/packages.json' % base_url]
        self.bioc_data = {}
        for url in bioc_urls:
            try:
                response = urllib2.urlopen(url)
            except IOError as e:
                print 'URL request: ', url
                sys.exit(e)
            self.bioc_data.update(json.loads(response.read()))
            if self.debug:
                print('reading Bioconductor Package inf: %s' % url)
                pkgcount = len(self.bioc_data.keys())
                print('size: %s' % pkgcount)
             

    def get_CRAN_info(self, pkg):
        cran_list = "http://crandb.r-pkg.org/"
        resp = requests.get(url=cran_list + pkg[0])

        cran_info = json.loads(resp.text)
        if 'error' in cran_info and cran_info['error'] == 'not_found':
            return "not found", []
        try:
            pkg_ver = cran_info[u'Version']
        except KeyError:
            return "error", []
        depends = []
        if u'License' in cran_info and u'Part of R' in cran_info[u'License']:
            return 'base package', []
        if u"Depends" in cran_info:
            depends = cran_info[u"Depends"].keys()
        if u"Imports" in cran_info:
            depends += cran_info[u"Imports"].keys()
        if self.meta: print('%s: %s' % (pkg[0], json.dumps(cran_info,indent=4)))
        return pkg_ver, depends


    def get_BioC_info(self, pkg):
        """Extract <Depends> and <Imports> from BioCondutor json metadata
        Example:
        bioc_data['pkg']['Depends']
                    [u'R (>= 2.10)', u'BiocGenerics (>= 0.3.2)', u'utils']
        interesting fields from BioCoductor:
        bioc_data['pkg']['Depends', 'Imports', 'Biobase', 'graphics', 'URL']
        """
        depends = []
        if pkg[0] in self.bioc_data:
            pkg_ver = self.bioc_data[pkg[0]]['Version']
            source_file = self.bioc_data[pkg[0]]['source.ver']
            if 'Depends' in self.bioc_data[pkg[0]]:
                depends = [re.split('[ (><=,]', s)[0]
                           for s in self.bioc_data[pkg[0]]['Depends']]
            if 'Imports' in self.bioc_data[pkg[0]]:
                depends = [re.split('[ (><=,]', s)[0]
                           for s in self.bioc_data[pkg[0]]['Imports']]
            if self.meta: print('%s: %s' % (pkg[0], json.dumps(self.bioc_data[pkg[0]],indent=4)))
        else:
            pkg_ver = "not found"
        return pkg_ver, depends

    def print_depends(self, pkg, depends):
        """ used for debugging """
        for p in depends:
            if p not in self.depend_exclude:
                print("%20s : requires %s" % (pkg, p))

    def get_package_info(self, pkg):
        """R version, check CRAN and BioConductor for version information
        """
        depends = []
        pkg_ver, depends = self.get_BioC_info(pkg)
        if pkg_ver == 'not found':
            pkg_ver, depends = self.get_CRAN_info(pkg)
            if pkg_ver == 'not found':
                return 'not found', [], []
            else:
                pkg[2]['R_source'] = 'ext_options'
        else:
            pkg[2]['R_source'] = 'bioconductor_options'
        if self.debug:
            for p in depends:
                print("    %s requires: %s" % (pkg[0], p))
        return 'ok', [pkg[0], pkg_ver], depends


    def output_module(self, pkg):
        """R version: format a pkg for output"""
        output = "%s('%s', '%s', " % (self.indent, pkg[0], pkg[1])
        for source in pkg[2].keys():
           if source == 'R_source': 
               output += pkg[2]['R_source'] 
           elif source == 'ext_options':
               output += 'ext_options),'
           elif source == 'bioconductor_options':
               output += 'bioconductor_options),'
        output += '),'
        return output


class PythonExts(ExtsList):
    """extend ExtsList class to update package names from PyPI
    """
    def __init__(self, args):
        ExtsList.__init__(self, args)
        self.pkg_dict = None
        self.client = xmlrpclib.ServerProxy('https://pypi.python.org/pypi')
        (nums) = self.version.split('.')
        self.python_version = "%s.%s" % (nums[0], nums[1])
        # Python >3.3 has additional built in modules
        if nums[0] == 3 and nums[1] > 3:
            self.depend_exclude = ['argparse', 'asyncio', ]

    def parse_pypi_requires(self, eb_filename, requires):
        """pip requirement specifier is defined in full in PEP 508
        The project name is the only required portion of a requirement string.

        Only install the latest version so ignore all version information
        input: 'numpy (>=1.7.1)'  output: 'numpy'

        Test that <python_version> and <sys_platform> conform.
        If <extra> is present and required check that extra is contained
        in "exts_list".
        wincertstore (==0.2); sys_platform=='win32' and extra == 'ssl'
        futures (>=3.0); (python_version=='2.7' or python_version=='2.6')
        requests-kerberos (>=0.6); extra == 'kerberos'
        trollius; python_version == "2.7" and extra == 'asyncio'
        asyncio; python_version == "3.3" and extra == 'asyncio'
        """
        sys_platform = 'Linux'
        python_version = self.python_version
        extra = ''
        platform_python_implementation = 'CPython'
        require_re = '^([A-Za-z0-9_\-\.]+)(?:.*)$'
        extra_re = "and\sextra\s==\s'([A-Za-z0-9_\-\.]+)'"  # only if the
        targets = ['python_version', 'sys_platform', 'extra']
        ans = re.search(require_re, requires)
        name = ans.group(1)
        state = True    # result of eval(requires)

        version = requires.split(';')
        if len(version) > 1:
            for target in targets:
                if target in version[1]:
                    # eval Example: python_version == "3.3" and sys_platform == 'Linux'
                    try:
                        state = eval(version[1])
                    except NameError:
                        print('Error: NameError on eval, ignoring')
                    except SyntaxError:
                        pass
                    if target == 'extra':
                        extra = re.search(extra_re, version[1])
                        extra = extra.group(1) if extra else None
                        if extra not in [i[0] for i in self.exts_processed]:
                            extra = None
        if state:
            if self.verbose > 1:
                if name not in [i[0] for i in self.exts_processed] and (
                   name not in self.depend_exclude):
                    print('Add dependent package: %s ' % name),
                    print('for: %s, Expression: %s' % (pkg_name, requires))
            return name
        else:
            if self.verbose > 1:
                print('Do not install: %s, ' % name +
                      'for package: %s, Expression: %s' % (pkg_name, requires))
            return None

    def get_package_info(self, pkg):
        """Python version
           Get package version and dependency list via PyPi API.
           pkg is a list; ['package name', 'version', dict]
           return the version number for the package and a list of dependencies

           TODO; whl file should check versions. Output for whl should also
           set 'usepip: True' 
           if version == '3.6':
               pyver = 'cp36'
               arch = 'linux' ['manylinux', 'anylinux', 'linux']
           if arch == url_info['python_version']:
               use whl
        """
        depends = []
        (pkg_name, pkg_ver, xml_info, url_info) = self.get_pypi_info(pkg[0])
        if not xml_info:
            print("Warning: %s Not in PyPi. " % pkg[0])
            print("No dependency checking performed")
            return 'not found', [], []
        URL = None
        source_tmpl = None
        for idx, url in enumerate(url_info):
            file_name = url['filename']
            if 'python_version' in url:
                #print('version: %s index: %d' % (url['python_version'], idx))
                pass
            if url['filename'].endswith('tar.gz'):
                URL = url['url']
                break
            if url['filename'].endswith('.zip'):
                URL = url['url']
                source_tmpl = url['filename'].replace(pkg_name, '%(name)s')
                source_tmpl = source_tmpl.replace(pkg_ver, '%(version)s')
                break
        # if no URL is found use whl
        if not URL:
            for idx, url in enumerate(url_info):
                if url['url'].endswith('whl'):
                    URL = url['url']
                    file_name = url['filename']
            else:
                source_tmpl = None
        if 'requires_dist' in xml_info.keys():
            for requires in xml_info['requires_dist']:
                pkg_requires = self.parse_pypi_requires(pkg_name, requires)
                if pkg_requires:
                    depends.append(pkg_requires)
        else:
            self.depend_exclude.append(pkg[0])

        # checkpage should print from print_update()
        #if self.checkpackage:
        #    for dep_pkg in depends:
        #        d = {'state': 'dep'}
        #        self.get_package_info((dep_pkg, '', d))
        #    self.print_python_exts_list(pkg[0], pkg_ver, source_tmpl,
        #                                url_info[idx])
        return 'ok', (pkg_name, pkg_ver), depends


    def print_python_exts_list(self, pkg, ver, source_tmpl, url_info):
        """ output <pkg> information in easyconfig exts_list format
            Used when <self.checkpage> is True; for checking a single
            package; Used with flag --pyver
        """
        indent = self.indent
        url = "https://pypi.python.org/packages/source/"
        url += "%s/%s" % (pkg[0], pkg)
        print("%s('%s', '%s', {" % (indent, pkg, ver))
        print("%s%s'source_urls': ['%s']," % (indent, indent, url))
        if source_tmpl:
            print("%s%s'source_tmpl': '%s'," % (indent, indent, source_tmpl))
        print("%s})," % indent )
        if self.meta:
            print('# Package Meta Data')
            for item in url_info.keys():
                print('# %-35s: %s' % (item, url_info[item]))

    def get_pypi_info(self, pkg_name):
        """get version information from pypi.  If <pkg_name> is not found seach
        pypi. if <pkg_name> matches search results case; use the new value of
        pkg_name""" 
        client = xmlrpclib.ServerProxy('https://pypi.python.org/pypi')
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
                return pkg_name, 'not found', {}, {} 
        version = ver_list[0]
        xml_info = client.release_data(pkg_name, version)
        url_info = client.release_urls(pkg_name, version)
        return pkg_name, version, xml_info, url_info


    def output_module(self, pkg):
        """Python version: format a pkg for output"""
        output = "%s('%s', '%s', {\n" % (self.indent, pkg[0], pkg[1])
        for item in pkg[2].keys():
           if item == 'action' or item == 'state':
               print('%s: %s' % (item, pkg[2][item]))
           output += "%s%s'%s': %s,\n" % (self.indent, self.indent, item, pkg[2][item])
        output += "%s})," % self.indent
        return output


def help():
    print("usage: easy_update  easyconfig.eb [flags]")
    print("easy_update Updates ext_list information of EasyBuild"),
    print(" easyconfig files")
    print("easy_update works with R, Python and R-bioconductor"),
    print(" easyconfig files")
    print("  --verbose  diplay status for each package")
    print("  --add [filename]  filename contains list of package"),
    print(" names to add")
    sys.exit() 


def main():
    """ main """
    parser = argparse.ArgumentParser(description='Update easyconfig extslist')
    
    parser.add_argument('--version', action='version',
                        version='%(prog)s ' + __version__)
    parser.add_argument('-v', '--verbose', dest='verbose', required=False,
                        action='store_true',
                        help='Verbose; print lots of extra stuff, (default: false)')
    parser.add_argument('--rver', dest='rver', required=False, action='store',
                        help='Set R version (major.minor) example 3.4')
    bioc_help = 'Set BioConductor version (major.minor) example 3.6. Use with --rver'
    parser.add_argument('--biocver', dest='biocver', required=False, action='store',
                        help=bioc_help)
    parser.add_argument('--pyver', dest='pyver', required=False, action='store',
                        help='Set Python version [2.7 or 3.6]')
    parser.add_argument('--add', dest='add_pkg', required=False, action='store',
                        help='File that contains additional packages to be added')
    sea_help = 'Search for single package. requires --rver or --pyber' 
    parser.add_argument('--search', dest='pkg_name', required=False, action='store',
                        help=sea_help)
    parser.add_argument('--meta', dest='meta', required=False, action='store_true',
                        help='output all meta data keys from Pypi, (default: false)')
    parser.add_argument('easyconfig', nargs='?') 
    args = parser.parse_args()
   
    eb_name = '' 
    if args.easyconfig:
        eb_name = os.path.basename(args.easyconfig)
    elif args.pkg_name:
        pass
    else:
        print('If no easyconfig is given, a module name must be ' +
              'specified with --search pkg_name') 
        sys.exit()


    if args.rver or eb_name[:2] == 'R-':
        module = R(args)
    elif args.pyver or eb_name[:7] == 'Python-':
        module = PythonExts(args)
    else:
        msg = "Module name must begin with R- or Python- OR"
        msg += "  --search argument must be used"
        print(msg)
        sys.exit(1)
    module.update_exts()
    if args.easyconfig:
        module.print_update()

if __name__ == '__main__':
    main()
