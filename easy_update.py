#!/usr/bin/env python

import re
import os
import sys
import argparse
import imp
import json
import requests
from pprint import pprint
from pprint import pformat

"""
update to use pypi.org JSON API
  Project API:  GET /pypi/<project_name>/json
  Release API: GET /pypi/<project_name>/<version>/json
"""

__version__ = '1.3.0'
__author__ = 'John Dey jfdey@fredhutch.org'
__date__ = 'Jul 11, 2018'

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
        self.code = None
        self.biocver = None 
        self.ext_counter = 0
        self.pkg_update = 0
        self.pkg_new = 0
        self.pkg_duplicate = 0

        self.ext_list_len = 1 
        self.exts_processed = []  # single list of package names
        self.depend_exclude = []  # built in packages not be added to exts_list
        self.bioc_data = {}
        self.prolog = '## remove ##\n'
        self.ptr_head = 0
        self.indent_n = 4
        self.indent = ' ' * self.indent_n

        # update easyconfig exts_list or check single package
        if args.easyconfig:
            eb = self.parse_eb(args.easyconfig, primary=True)
            self.search_pkg = None 
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
            except (AttributeError, NameError):
                print('versionsuffix not defined')
            try: 
                self.biocver = eb.biocver
                if self.debug: print('biocver: %s' % self.biocver)
            except:
                pass
            self.pkg_version = eb.version
            self.check_eb_package_name(args.easyconfig)
            if args.add_pkg:
                self.get_package_list(args.add_pkg) 
            self.out = open(self.eb_filename + ".update", 'w')
        elif args.search_pkg:
            self.search_pkg = args.search_pkg
            if args.biocver: self.biocver = args.biocver
            if args.pyver:
                self.name = "Python"
                self.version = args.pyver
            elif args.rver:
                self.name = "R"
                self.version = args.rver
            else:
                print('Languange and version must be specified with ' +
                      '[--pyver x.x | --rver x.x | --biocver x.x]')
            sea_pkg = {'name': args.search_pkg, 'version': 'x', 'type': 'add',
                       'spec': {}, 'meta': {}
                       }
            self.search_ext = sea_pkg


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
                d = {'type': 'add', 'spec': {}}
                self.exts_orig.append((pkg, 'x', d))


    def check_eb_package_name(self, easyconfig):
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


    def processed(self, pkg):
        """ save Processed packages
        save a normalize version of packae name to <exts_search> for Python
        updated July 2018
        """
        pkg['processed'] = True 
        pkg2 = dict(pkg)
        self.exts_processed.append(pkg2)


    def is_processed(self, pkg):
        """ check if package has been previously processed 
            if package exists AND is in the original exts_lists
                Mark as 'duplicate' 
        updated July 2018
        """
        name = pkg['name']
        for p_pkg in self.exts_processed:
            if 'spec' in p_pkg and 'modulename' in p_pkg['spec']:
                modulename = p_pkg['spec']['modulename']
            else:
                modulename = ''
            if (str(name) == str(p_pkg['name'])) or (name == modulename): 
                if pkg['type'] == 'orig':
                    pkg['action'] = 'duplicate'
                    self.pkg_duplicate += 1
                    self.processed(pkg)
                    if self.verbose:
                        self.print_status(pkg)
                return True
        return False


    def get_package_info(self, pkg):
        """base class 
        subclasses of <get_package_info> search CRAN, Pypi or Bioconductor
        based on easyconfig.
        input: pkg - dict['name', 'version', 'spec': dict]
        return: status ['ok', 'error', 'not found'] 
        pkg['meta'] is populated from package repository.
        Pypi.org and CRAN have very different metadata. These fields will be
        standardized:
        pkg['meta']['url', 'version', 'description']

        pkg['meta']['requires'] list of package names that are dependancies
        look hard for dependant packages, try to match different cases
        and interchange underscore and dash.  If input package_name
        does not match rewrite pkg[0] with name found from repository.
        """
        pass


    def print_status(self, pkg):
        """ print one line status for each package if --verbose
        updated July 2018
        """
        if pkg['action'] == 'update':
            version = '%s -> %s' % (pkg['orig_ver'], pkg['version'])
        else:
            version = pkg['version']
        action = '(%s)' % pkg['action']
        tmpl = "%20s : %-20s %12s [%2d, %d]"
        print(tmpl % (pkg['name'], version, action,
                      self.ext_list_len, self.ext_counter))

    def print_meta(self, info):
        """ print meta data from repository
        this is broken for R 
        """
        pass
       
    def check_package(self, pkg):
        """query package authority [Pypi, CRAN, Bio] to get the latest version
        information for a package. This is the heart of the program.

        input: pkg{}
        check that all dependancies are meet for each package.
        check_package can be called recursivly.
        pkg['type'] is used to track status.
          - 'orig' is also used to track recursion
          - 'dep' package that is added as result of dependancy
          - 'add' packages read from file
        pkg['action'] What action will be take to exts_list.
          - 'add'; new package
          - 'keep'; no update required
          - 'update'; version change
          - 'duplicate' package appears twice
        """
        if self.debug: print('check_package: %s' % pkg['name'])
        if self.is_processed(pkg):
            return
        status = self.get_package_info(pkg)
        if status in ["error", 'not found']:
            if pkg['type'] == 'orig':
                pkg['action'] = 'keep'
                self.processed(pkg)
                return
            else:
                msg = "Warning: %s is dependency, but can't be found!"
                print(msg % pkg['name'])
                return
        version = pkg['meta']['version']
        if pkg['version'] == version:
            pkg['action'] = 'keep'
        else:
            pkg['orig_ver'] = pkg['version']
            pkg['version'] = pkg['meta']['version']
            self.pkg_update += 1
            if pkg['type'] == 'orig': 
                pkg['action'] = 'update'
            elif pkg['type'] in ['dep', 'add']:
                if self.debug: print('check_package; dep or add')
                pkg['action'] = 'add'
                self.pkg_new += 1

        if 'requires' in pkg['meta']:
            for depend in pkg['meta']['requires']:
                if depend not in self.depend_exclude:
                    depPkg = {'name': depend, 'version': 'x', 'type': 'dep',
                              'spec': {}, 'meta': {}}
                    self.check_package(depPkg)
        else:
            print('No requires!: %s' % pkg['name'])
        self.processed(pkg)
        self.ext_counter += 1
        if self.search_pkg:
            output = self.output_module(pkg)
            print(output)
        if self.verbose:
            self.print_status(pkg)
        if self.meta:
            self.print_meta(pkg['meta'])
          

    def update_exts(self):
        """Loop through exts_list and check which packages need to be updated.
        this is an external method for the class
        """
        if self.search_pkg:
            self.check_package(self.search_ext)
        else:
            self.ext_list_len = len(self.exts_orig)
            for ext in self.exts_orig:
                if isinstance(ext, tuple):
                    pkg = {'name': ext[0], 'version': ext[1], 'spec': ext[2],
                           'type': 'orig'}
                    pkg['meta'] = {}
                    self.check_package(pkg)
                else:
                    self.processed({'name': ext, 'type': 'base'})

    def write_chunk(self, indx):
        self.out.write(self.code[self.ptr_head:indx])
        self.ptr_head = indx

    def rewrite_extension(self, pkg):
        name = pkg['name']
        name_indx = self.code[self.ptr_head:].find(name)
        name_indx += self.ptr_head + len(name) + 1
        indx = self.code[name_indx:].find("'") + name_indx + 1
        self.write_chunk(indx)
        self.out.write("%s'," % pkg['version'])
        self.ptr_head = self.code[self.ptr_head:].find(',') + self.ptr_head + 1
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
            name = extension['name']
            if 'action' not in extension:
                print('No action: %s' % name)
                extension['action'] = 'keep'

            if extension['type'] == 'base': # base library with no version
                indx = self.code[self.ptr_head:].find(name)
                indx += self.ptr_head + len(name) + 2
                self.write_chunk(indx)
            elif extension['action'] in ['keep', 'update']:
                self.rewrite_extension(extension)
                # sys.exit(0)
            elif extension['action'] == 'duplicate':
                print('Duplicate: %s' % name)
                name_indx = self.code[self.ptr_head:].find(name)
                name_indx += self.ptr_head + len(name)
                indx = self.code[name_indx:].find('),') + name_indx + 3
                self.ptr_head = indx
                continue
            elif extension['action'] in ['add','dep']:
                output = self.output_module(extension)
                self.out.write("%s\n" % output) 
        self.out.write(self.code[self.ptr_head:])
        print("Updated Packages: %d" % self.pkg_update)
        print("New Packages: %d" % self.pkg_new)
        print("Dropped Packages: %d" % self.pkg_duplicate)


    def download_url(self, filename, url):
        print('downloading: %s' % filename)
        #handle = open(self.source_dir + filename, "w")
        response = requests.get(url, stream=True)
        if response.status_code < 200 or response.status_code > 299:
            sys.stderr.write('download failed: %s filename: %s' % (
                resp.status_code, filename))
            return
        with open(self.source_dir + filename, "wb") as handle:
            for data in tqdm(response.iter_content()):
                handle.write(data)
        handle.close()
        

    def unpack_package(self, filename):
        content = None
        print('unpack: %s' % self.source_dir + filename)
        tar = tarfile.open(self.source_dir + filename, "r:gz")
        for member in tar.getmembers():
            f = tar.extractfile(member)
            print('extract: %s' % f)
            if f is not None and f == 'setup.py':
                content = f.read()
                break
        if content and 'install_requires' in content:
            print(content)
        


class R(ExtsList):
    """extend ExtsList class to update package names from CRAN and BioCondutor
    """
    def __init__(self, args):
        ExtsList.__init__(self, args)
        self.depend_exclude = ['R', 'base', 'compiler', 'datasets', 'graphics',
                               'grDevices', 'grid', 'methods', 'parallel', 
                               'splines', 'stats', 'stats4', 'tcltk', 'tools',
                               'utils',] 
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
        for url in bioc_urls:
            resp = requests.get(url)
            if resp.status_code != 200: 
                print('Error: %s %s' % (resp.status_code, url))
                sys.exit(1)
            self.bioc_data.update(resp.json())
            if self.debug:
                print('reading Bioconductor Package inf: %s' % url)
                pkgcount = len(self.bioc_data.keys())
                print('size: %s' % pkgcount)
             

    def get_CRAN_info(self, pkg):
        """ MD5sum, Description, Package, releases[]
        """
        cran_list = "http://crandb.r-pkg.org/"
        resp = requests.get(url=cran_list + pkg['name'])
        if resp.status_code != 200:
            return "not found"
        cran_info = resp.json()
        pkg['meta']['version'] = cran_info['Version']
        if u'License' in cran_info and u'Part of R' in cran_info[u'License']:
            return 'base package'
        pkg['meta']['requires'] = []
        if u"Depends" in cran_info:
            pkg['meta']['requires'].extend(cran_info[u"Depends"].keys())
        if u"Imports" in cran_info:
            pkg['meta']['requires'].extend(cran_info[u"Imports"].keys())
        return 'ok'


    def get_BioC_info(self, pkg):
        """Extract <Depends> and <Imports> from BioCondutor json metadata
        Example:
        bioc_data['pkg']['Depends']
                    [u'R (>= 2.10)', u'BiocGenerics (>= 0.3.2)', u'utils']
        interesting fields from BioCoductor:
        bioc_data['pkg']['Depends', 'Imports', 'Biobase', 'graphics', 'URL']
        """
        status = 'ok'
        if pkg['name'] in self.bioc_data:
            pkg['meta']['version'] = self.bioc_data[pkg['name']]['Version']
            if 'Depends' in self.bioc_data[pkg['name']]:
                pkg['meta']['requires'].extend([re.split('[ (><=,]', s)[0]
                           for s in self.bioc_data[pkg['name']]['Depends']])
            if 'Imports' in self.bioc_data[pkg['name']]:
                pkg['meta']['requires'].extend([re.split('[ (><=,]', s)[0]
                           for s in self.bioc_data[pkg['name']]['Imports']])
        else:
            status = "not found"
        return status

    def print_depends(self, pkg):
        """ used for debugging """
        for p in pkg['meta']['requires']:
            if p not in self.depend_exclude:
                print("%20s : requires %s" % (pkg['name'], p))

    def get_package_info(self, pkg):
        """R version, check CRAN and BioConductor for version information
        """
        if self.debug: print('get_package_info: %s' % pkg['name'])
        pkg['meta']['requires'] = []
        status = self.get_BioC_info(pkg)
        if status == 'not found':
            status = self.get_CRAN_info(pkg)
            pkg['R_source'] = 'ext_options'
        else:
            pkg['R_source'] = 'bioconductor_options'
        if self.debug: self.print_depends(pkg)
        return status


    def output_module(self, pkg):
        """R version: format a pkg for output"""
        output = "%s('%s', '%s', %s)," % (self.indent, pkg['name'],
                                            pkg['version'],
                                            pkg['R_source'])
        return output


class PythonExts(ExtsList):
    """extend ExtsList class to update package names from PyPI
    """
    def __init__(self, args):
        ExtsList.__init__(self, args)
        self.pkg_dict = None
        (nums) = self.version.split('.')
        self.python_version = "%s.%s" % (nums[0], nums[1])
        # Python >3.3 has additional built in modules
        if nums[0] == 3 and nums[1] > 3:
            self.depend_exclude = ['argparse', 'asyncio', ]
        if self.debug and self.search_pkg:
            print('Python Search PyPi: %s' % self.search_pkg)

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
        for req in requires:
            try:
                dep, version = req.split()
                req = dep
            except ValueError:         
                pass


    def print_meta(self, meta):
        """ Display meta from pypi.org
        """
        tags = ['filename', 'packagetype', 'url', 'python_version',
                'requires_dist', 'summary', 'requires_python']
        for tag in tags:
            if tag in meta:
                print("%s'%s': '%s'" % (self.indent, tag, meta[tag]))

    def get_package_depends(self, filenam, url):
        """ inspect setup.py for requires_dist and install_requires"""
        if not os.path.isfile(self.source_dir + filename):
            self.download_url(filename, url)
        self.unpack_package(filename)
        # do more stuff

    def get_package_info(self, pkg):
        """Python version
           Get package meta data via PyPi.org
           pkg is a dict; {'name', 'version', 'spec'}
           return metadata as hash 
             pkg['meta']['version']
           if source package is not found look for whl
           if pyver == ['3.5, '3.6', '3.7']:
               arch = 'linux' ['manylinux', 'anylinux', 'linux']
        """
        status = self.get_pypi_info(pkg)
        return status


    def get_pypi_release(self, pkg, version):
        """ if source dist is not available from pypi search
        the release for for a whl file.
        """
        req = 'https://pypi.org/pypi/%s/%s/json' % (pkg['name'], version)
        resp = requests.get(req)
        if resp.status_code != 200:
            msg = "API error: %s GET release %s"
            sys.stderr.write(msg % (resp.status_code, pkg['name'])) 
            return 'not found'
        release = resp.json()
        cplist = ['cp35', 'cp36', 'cp37']
        for rel in release['releases'][version]:
            if any(cver in rel['python_version'] for cver in cplist):
                if 'manylinux' in rel['filename']:
                    pkg['meta'].update(rel)
                    return 'ok'
        return 'not found'


    def get_pypi_info(self, pkg):
        """get version information from pypi.  If <pkg_name> is not processed
           seach pypi. pkg_name is now case sensitive and must match  
           info['digests']['sha256'], 'summary', 'url', 'filename', 'home_page'
        """
        status = 'not found'
        pkg['meta'] = {}
        resp = requests.get('https://pypi.org/pypi/%s/json' % pkg['name'])
        if resp.status_code != 200:
                msg = "API error: %s GET %s" % (resp.status_code, pkg['name'])
                sys.stderr.write(msg)
                return 'not found', {}
        project = resp.json()
        version = project['info']['version']
        pkg['meta'].update(project['info'])
#XX clean up requires
        requires = project['info']['requires_dist']
        self.parse_pypi_requires(pkg['name'], requires)
        pkg['meta']['requires'] = requires 
        pkg['meta']['version'] = version 
        for ver in project['releases'][version]:
            if 'packagetype' in ver and ver['packagetype'] == 'sdist':
                pkg['meta']['url'] = ver['url']
                pkg['meta']['filename'] = ver['filename']
                status = 'ok'
                break
        # one last try to find package release data
        if status != 'ok':
             status = self.get_pypi_release(pkg, version)
        # only set this if not set
        if 'source_urls' not in pkg['spec'] and version != pkg['version']:
            pkg['spec']['source_urls'] = "['PYPI_SOURCE']" 
        return status


    def output_module(self, pkg):
        """Python version: format single pkg for output. 
        Used if --search argument is used.
        if self.search_pkg:
        """
        pkg_fmt = self.indent + "('%s', '%s', {\n"
        item_fmt = self.indent + self.indent + "'%s': %s,\n"
        list_fmt = self.indent + self.indent + "'%s': ['%s'],\n"
        output = pkg_fmt % (pkg['name'], pkg['version'])
        for item in pkg.keys():
           if item in ['name', 'version', 'action', 'type', 'orig_ver',
                       'processed', 'meta', 'spec']:
               continue 
           output += item_fmt % (item, pkg[item])
        for item in pkg['spec'].keys():
           output += item_fmt % (item, pkg['spec'][item])
        output += self.indent + "}),"
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
    parser.add_argument('--search', dest='search_pkg', required=False, action='store',
                        help=sea_help)
    parser.add_argument('--meta', dest='meta', required=False, action='store_true',
                        help='output all meta data keys from Pypi, (default: false)')
    parser.add_argument('easyconfig', nargs='?') 
    args = parser.parse_args()
  
    eb_name = '' 
    if args.easyconfig:
        eb_name = os.path.basename(args.easyconfig)
    elif args.search_pkg:
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
        msg = "EasyConfig file name must begin with R- or Python- OR"
        msg += "  --search argument must be used"
        print(msg)
        sys.exit(1)
    module.update_exts()
    if args.easyconfig:
        module.print_update()

if __name__ == '__main__':
    main()
