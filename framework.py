#!/usr/bin/env python

import re
import os
import sys
import argparse
import types 
import requests

""" 1.0.1 Aug, 15, 2019
    fix parse_dependencies
    For the case of reading Python dependancies, conver the
    case of 'Biopython-1.74-foss-2016b-Python-3.7.4'
    Search dependcies for versionsuffix == '-Python-%(pyver)s'
    add dep_exts are exts_list from dependent packages

    - remove the variable dep_eb
    - All to resolve dependancie in the FrameWork, FrameWork only
      needs a single argument. It had three.

    1.0.0 July 8, 2019
    framework.py becomes seperate package. Share code
    between easy_update and easy_annotate

    Read exts_list for R and Python listed in dependencies.
"""

__version__ = '1.0.1'
__maintainer__ = 'John Dey jfdey@fredhutch.org'
__date__ = 'July 9, 2019'


class FrameWork:
    """provide access to EasyBuild Config file variables
    name, version, toolchain, eb.exts_list, dependencies, modulename, biocver,
    methods:
        print_update()
    """
    def __init__(self, args):
        self.debug = False
        self.code = None
        self.pyver = None
        self.rver = None
        self.search_pkg = None
        self.lang = None
        self.indent_n = 4
        self.indent = ' ' * self.indent_n
        self.ptr_head = 0
        self.modulename = None
        self.dep_exts = []

        full_path = os.path.dirname(args.easyconfig)
        if full_path == '.' or full_path == '':
            self.base_path = '.'
        else:
            (head, tail) = os.path.split(full_path)
            while tail:
                if 'easyconfig' in tail:
                    self.base_path = os.path.join(head, tail)
                    break
                (head, tail) = os.path.split(head)

        # update EasyConfig exts_list or check single package
        if args.easyconfig:
            eb = self.parse_eb(args.easyconfig, primary=True)
            self.exts_list = eb.exts_list
            self.toolchain = eb.toolchain
            self.name = eb.name
            self.version = eb.version
            self.interpolate = {'name': eb.name, 'namelower': eb.name.lower(),
                                'version': eb.version,
                                'pyver': None,
                                'rver': None}
            try:
                self.defaultclass = eb.exts_defaultclass
            except AttributeError:
                self.defaultclass = None
            self.parse_dependencies(eb, self.lang)
            try:
                self.versionsuffix = eb.versionsuffix % self.interpolate
            except AttributeError:
                self.versionsuffix = "" 
            self.detect_language(eb)
            if not self.lang:
                print('Wow language is unknown!')

            self.modulename = eb.name + '-' + eb.version
            self.modulename += '-' + eb.toolchain['name']
            self.modulename += '-' + eb.toolchain['version']
            self.modulename += self.versionsuffix
            if self.debug:
                sys.stderr.write('debug - modulename: %s\n' % self.modulename)
                sys.stderr.write('debug -       file: %s\n' % filename[:-3])
            self.dependencies = None
            if 'eb.dependancies'.isidentifier():
                self.dependencies = eb.dependencies
            self.biocver = None
            if 'eb.biocver'.isidentifier():
                self.biocver = eb.biocver
            self.check_eb_package_name(args.easyconfig)
            self.out = open(args.easyconfig[:-3] + ".update", 'w')

    def parse_eb(self, file_name, primary):
        """ interpret EasyConfig file with 'exec'.  Interperting fails if
        constants that are not defined within the EasyConfig file.  Add
        undefined constants to <header>.
        """
        header = 'SOURCE_TGZ  = "%(name)s-%(version)s.tgz"\n'
        header += 'SOURCE_TAR_GZ = "%(name)s-%(version)s.tar.gz"\n'
        header += 'SOURCELOWER_TAR_GZ = "%(namelower)s-%(version)s.tar.gz"\n'
        header += 'SOURCELOWER_TAR_BZ2 = "%(namelower)s-%(version)s.tar.bz2"\n'
        header += 'SOURCELOWER_TAR_XZ = "%(namelower)s-%(version)s.tar.xz"\n'
        header += 'SHLIB_EXT = ".so"\n'
        header += ('PYPI_SOURCE = "https://pypi.python.org/packages/' +
                   'source/%(nameletter)s/%(name)s"\n')
        header += ('SOURCEFORGE_SOURCE = "https://download.sourceforge.net/' +
                   '%(namelower)s"\n')
        eb = types.ModuleType("EasyConfig")
        try:
            with open(file_name, "r") as f:
                code = f.read()
        except IOError as err:
            print("opening %s: %s" % (file_name, err))
            sys.exit(1)
        try:
            exec (header + code, eb.__dict__)
        except Exception as err:
            print("interperting EasyConfig error: %s" % err)
            sys.exit(1)
        if primary:     # save original text of source code
            self.code = code
        
        # R module might have been installed without extensions.
        # Start with an empty list if it is the case.
        if 'exts_list' not in eb.__dict__:
            eb.exts_list = []

        return eb

    def detect_language(self, eb):
        """ R or Python? EasyConfig parameters: easyblock, name, versionsuffix
        """
        if eb.name == 'Python':
            self.lang = str(eb.name)
            self.interpolate['pyver'] = eb.version
            return
        if eb.name == 'R':
            self.lang = str(eb.name)
            self.interpolate['rver'] = eb.version
            return
        if 'Python' in self.versionsuffix:
            self.lang = 'Python'
            return
        if '-R' in self.versionsuffix:
            self.lang = 'R'
            return
        if self.defaultclass:
            self.lang = eb.exts_defaultclass.replace('Package', '')

    def build_dep_filename(self, eb, dep):
        """build a filename from a dependencie object"""
        dep_filename = '{}-{}'.format(dep[0], dep[1])
        if len(dep) == 4:
            dep_filename += dep[2] + '.eb'
            return dep_filename
        dep_filename += '-{}-{}'.format(eb.toolchain['name'],eb.toolchain['version'])
        if self.pyver and len(dep) > 2:
            versionsuffix = dep[2] % {'pyver': self.pyver}
            dep_filename += '{}'.format(versionsuffix)
        if self.rver and len(dep) > 2:
            versionsuffix = dep[2] % {'rver': self.rver}
            dep_filename += '{}'.format(versionsuffix)
        dep_filename += '.eb'
        return dep_filename

    def find_easyconfig(self, easyconfig):
        """ search base_path for easyconfig filename """
        found = None
        sys.stderr.write(" - reading dependency: {}\n".format(easyconfig))
        for r,d,f in os.walk(self.base_path):
            for filename in f:
                 if filename == easyconfig:
                      found = os.path.join(r,filename)
                      break
        return found

    def parse_dependencies(self, eb, lang):
        """ inspect dependencies for R and Python easyconfigs,
        if found add the exts_list to the list of dependent
        exts  <dep_exts>
        """
        try:
            dependencies = eb.dependencies
        except NameError:
            return None
        for dep in dependencies:
            easyconfig = None
            if dep[0] in ['R', 'Python']:
                if dep[0] == 'Python':
                    self.interpolate['pyver'] = dep[1]
                    self.pyver = dep[1]
                if dep[0] == 'R':
                    self.interpolate['rver'] = dep[1]
                    self.rver = dep[1]
                dep_filename = self.build_dep_filename(eb, dep)
                easyconfig = self.find_easyconfig(dep_filename)
            else:
                dep_filename = self.build_dep_filename(eb, dep)
                if '-R-' in dep_filename or '-Python-' in dep_filename:
                    easyconfig = self.find_easyconfig(dep_filename)
            if easyconfig:
                eb = self.parse_eb(str(easyconfig), False)
                try:
                    self.dep_exts.extend(eb.exts_list)
                except (AttributeError, NameError):
                    self.dep_exts.extend([dep])

    def parse_python_deps(self, eb):
        """ Python EasyConfigs can have other Python packages in the
        dependancy field. check 3rd element for -Python-%(pyver)s"
        """
        try:
            dependencies = eb.dependencies
        except NameError:
            return None
        for dep in eb.dependencies:
            pass

    def check_eb_package_name(self, filename):
        """" check that easybuild filename matches package name
        easyconfig is original filename
        """
        eb_name = os.path.basename(filename)[:-3]
        if eb_name != self.modulename:
            sys.stderr.write("Warning: file name does not match easybuild " +
                             "module name\n"),
        if eb_name != self.modulename or self.debug:
            sys.stderr.write("   file name: %s\n module name: %s\n" % (
                eb_name, self.modulename))

    def write_chunk(self, indx):
        self.out.write(self.code[self.ptr_head:indx])
        self.ptr_head = indx

    def rewrite_extension(self, pkg):
        name = pkg['name']
        name_indx = self.code[self.ptr_head:].find(name)
        name_indx += self.ptr_head + len(name) + 1
        indx = self.code[name_indx:].find("'") + name_indx + 1
        self.write_chunk(indx)
        self.out.write("%s'" % pkg['version'])
        self.ptr_head = self.code[self.ptr_head:].find("'") + self.ptr_head + 1
        indx = self.code[self.ptr_head:].find('),') + self.ptr_head + 3
        self.write_chunk(indx)


    def output_module(self, lang, pkg):
        """write exts_list entry
        """
        output = None
        if lang == 'R':
            output = "%s('%s', '%s')," % (self.indent, pkg['name'], pkg['version'])
        elif lang == 'Python':
            # TODO all the python should should be in UpdatePython
            # from easy_update import UpdatePython # static method
            # UpdatePython.output_module(pkg)
            output = self.python_output_module(pkg)
        return output

    def python_output_module(self, pkg):
        """Python version"""
        pkg_fmt = self.indent + "('{}', '{}', {{\n"
        item_fmt = self.indent + self.indent + "'%s': %s,\n"
        if 'spec' in pkg:
            output = pkg_fmt.format(pkg['name'], pkg['version'])
            for item in pkg['spec'].keys():
                output += item_fmt % (item, pkg['spec'][item])
            output += self.indent + "}),"
        else:
            output = "('{}', '{}),".format(pkg['name'], pkg['version'])
        return output

    def print_update(self, lang, exts_list):
        """ this needs to be re-written in a Pythonesque manor
        if module name matches extension name then skip
        """
        indx = self.code.find('exts_list')
        indx += self.code[indx:].find('[')
        indx += self.code[indx:].find('\n') + 1
        self.write_chunk(indx)

        for extension in exts_list:
            name = extension['name']
            if 'action' not in extension:
                sys.stderr.write('No action: %s\n' % name)
                extension['action'] = 'keep'

            if lang.lower() == lang:
                # special case for bundles, if "name" is used in exts_list
                indx = self.code[self.ptr_head:].find('),') + 2
                indx += self.ptr_head
                self.write_chunk(indx)
            elif extension['from'] == 'base':  # base library with no version
                indx = self.code[self.ptr_head:].find(name)
                indx += self.ptr_head + len(name) + 2
                self.write_chunk(indx)
            elif extension['action'] in ['keep', 'update']:
                self.rewrite_extension(extension)
            elif extension['action'] == 'duplicate':
                print('Duplicate: %s' % name)
                name_indx = self.code[self.ptr_head:].find(name)
                name_indx += self.ptr_head + len(name)
                indx = self.code[name_indx:].find('),') + name_indx + 3
                self.ptr_head = indx
                continue
            elif extension['action'] in ['add', 'dep']:
                output = self.output_module(lang, extension)
                self.out.write("%s\n" % output)
        self.out.write(self.code[self.ptr_head:])


if __name__ == '__main__':
    """ create unit test """
    print('none') 
