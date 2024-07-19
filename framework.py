#!/usr/bin/env python3

import re
import os
import sys
import shutil
import argparse
import types
import requests
import logging
from templates import TEMPLATE_CONSTANTS
from constants import EASYCONFIG_CONSTANTS

""" 1.0.4 Nov, 2022
    - no long try to guess the language by reading the EasyConfig. Lang must
      be speicified as a command line argument.
    - remove "detect_language"
    - only call "framework" if an EasyConfig needs updating
    - use "templates.py" from EasyBuild Framework

    1.0.3 Dec 16, 2020 (Beethoven's 250th birthday)
    R does not have an easyblock, so don't check for one.

    1.0.2 Nov 21, 2020
    Fix issue with not being able to read Python dependancies for minimal toolchain.
    Python-3.7.3-foss-2019b.eb should be Python-3.7.4-GCCcore-8.3.0.eb

    Require EasyBuild to be loaded. Use "eb" path to find easybuild/easyconfigs

    <find_easyconfig> now supports a list of paths, $PWD plus EasyBuild easyconfig path
    search easyconfig asumes slphabet soup of directory names.
    ie: SciPy-bundle-2020.06-foss-2020a-Python-3.8.2.eb will be search for in the directory: s/SciPy-bundle
    <build_dep_filename> now supports a list of file names based on minimal toolchain

    add logging.debug()

    1.0.1 Aug, 15, 2019
    fix search_dependencies
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

__version__ = '1.0.4'
__maintainer__ = 'John Dey jfdey@fredhutch.org'
__date__ = 'Nov 2, 2022'

logging.basicConfig(format='%(levelname)s [%(filename)s:%(lineno)-4d] %(message)s',
                    level=logging.WARN)


class FrameWork:
    """provide access to EasyBuild Config file variables
    name, version, toolchain, eb.exts_list, dependencies, modulename, biocver,
    methods:
        print_update()
    """
    def __init__(self, args, easyconfig, lang):
        if args.debug:
            logging.getLogger().setLevel(logging.DEBUG)
            logging.debug('debug enabled')
        self.easyconfig = easyconfig
        self.lang = lang
        self.verbose = args.verbose
        self.code = None
        self.pyver = None
        self.rver = None
        self.search_pkg = None
        self.indent_n = 4
        self.indent = ' ' * self.indent_n
        self.ptr_head = 0
        self.modulename = None
        self.dep_exts = []

        self.find_easyconfig_paths(easyconfig)
        logging.debug("EasyConfig search paths: {}".format(self.base_paths))

        # update EasyConfig exts_list

        eb = self.parse_eb(easyconfig, primary=True)
        self.exts_list = eb.exts_list
        self.toolchain = eb.toolchain
        self.name = eb.name
        self.version = eb.version
        self.pyver = self.rver = None
        if eb.name == 'Python':
            self.pyver = eb.version
        if self.name == 'R':
            self.rver = eb.version
        self.interpolate = {'name': eb.name, 'namelower': eb.name.lower(),
                            'version': eb.version,
                            'pyver': self.pyver,
                            'rver': self.rver,
                            'cudaver': ""}
        try:
            self.defaultclass = eb.exts_defaultclass
        except AttributeError:
            self.defaultclass = None
        self.search_dependencies(eb)
        try:
            self.versionsuffix = eb.versionsuffix % self.interpolate
        except AttributeError:
            self.versionsuffix = ""

        self.modulename = eb.name + '-' + eb.version
        self.modulename += '-' + eb.toolchain['name']
        self.modulename += '-' + eb.toolchain['version']
        self.modulename += self.versionsuffix
        logging.debug('modulename: {}'.format(self.modulename))
        self.dependencies = None
        try:
            self.dependencies = eb.dependencies
        except AttributeError:
            logging.warn('WARNING: no dependencies defined!')
        try:
            self.biocver = eb.local_biocver
        except AttributeError:
            self.biocver = None
        self.check_eb_package_name(easyconfig)
        self.out = open(easyconfig[:-3] + ".update", 'w')

    def parse_eb(self, file_name, primary):
        """ interpret EasyConfig file with 'exec'.  Interperting fails if
        constants that are not defined within the EasyConfig file.  Add
        undefined constants to <header>. Copy templates.py from EasyBuild
        """
        header = ''
        for constant in TEMPLATE_CONSTANTS:
            header += '{} = "{}"\n'.format(constant[0], constant[1])
        for constant in EASYCONFIG_CONSTANTS:
            header += '{} = "{}"\n'.format(constant, EASYCONFIG_CONSTANTS[constant][1])
        eb = types.ModuleType("EasyConfig")
        try:
            with open(file_name, "r") as f:
                code = f.read()
        except IOError as err:
            logging.debug("Error reading %s: %s" % (file_name, err))
            sys.exit(1)
        try:
            exec(header + code, eb.__dict__)
        except Exception as err:
            logging.error("interperting EasyConfig error: %s" % err)
            sys.exit(1)
        if primary:     # save original text of source code
            self.code = code

        # R module might have been installed without extensions.
        # Start with an empty list if it is the case.
        if 'exts_list' not in eb.__dict__:
            eb.exts_list = []

        return eb


    def find_easyconfig_paths(self, filename):
        """find the paths to EasyConfigs, search within the path given by the easyconfig
        given to update. Search for eb command
        """
        userPath = os.path.expanduser(filename)
        fullPath = os.path.abspath(userPath)
        (head, tail) = os.path.split(fullPath)
        self.base_paths = []
        local_path = None
        while tail:
            if 'easyconfigs' in tail:
                self.base_paths.append(os.path.join(head, tail))
                logging.debug('local path to easyconfigs: {}'.format(self.base_paths[-1]))
                local_path = head + '/' + tail
                break
            (head, tail) = os.path.split(head)
        if local_path is None:
            sys.stderr.writelines('You are not working in an EB repository, Quiting because I can not find dependancies.\n')
            sys.exit(1)
        self.base_paths.append(local_path)
        eb_root = os.getenv('EBROOTEASYBUILD')
        if eb_root is None:
            sys.stderr.writelines('Could not find path to EasyBuild Root, EasyBuild module must be loaded\n')
            sys.exit(1)
        else:
            self.base_paths.append(os.path.join(eb_root, 'easybuild/easyconfigs'))
        logging.debug('easyconfig search paths: {}'.format(self.base_paths))


    def find_easyconfig(self, name, easyconfigs):
        """ search base_paths for easyconfig filename """
        found = None
        first_letter = easyconfigs[0][0].lower()
        for easyconfig in easyconfigs:
            for ec_dir in self.base_paths:
                narrow = ec_dir + '/' + first_letter + '/' + name
                logging.debug('find_easyconfig: search for {} in {} '.format(easyconfig, narrow))
                for r,d,f in os.walk(narrow):
                    for filename in f:
                        if filename == easyconfig:
                            found = os.path.join(r,filename)
                            return found
        return None


    def build_dep_filename(self, eb, dep):
        """build a list of possible filenames from a dependency object.
           This is a Hack for minimal toolchain support
           Only supports foss toolchains
        """
        toolchains = [
            ['fosscuda-2019a', 'foss-2019a', 'GCCcore-8.2.0'],
            ['fosscuda-2019b', 'foss-2019b', 'GCCcore-8.3.0'],
            ['fosscuda-2020a', 'foss-2020a', 'GCCcore-9.3.0', 'GCC-9.3.0', 'gompi-2020a'],
            ['fosscuda-2020b', 'foss-2020b', 'GCCcore-10.2.0', 'GCC-10.2.0', 'gompi-2020b'],
            ['fosscuda-2021a', 'foss-2021a', 'GCCcore-10.3.0', 'GCC-10.3.0', 'gompi-2021a'],
            ['foss-2021b', 'GCCcore-11.2.0', 'GCC-11.2.0', 'gompi-2021b'],
            ['foss-2022a', 'GCCcore-11.3.0', 'GCC-11.3.0', 'gompi-2022a'],
            ['foss-2022b', 'GCCcore-12.2.0', 'GCC-12.2.0', 'gompi-2022b', 'gfbf-2022b'],
            ['foss-2023b', 'GCCcore-13.2.0', 'GCC-13.2.0', 'gompi-2023b', 'gfbf-2023b'],
        ]
        tc_versions = {
            '8.2.0': toolchains[0], '2019a': toolchains[0],
            '8.3.0': toolchains[1], '2019b': toolchains[1],
            '9.3.0': toolchains[2], '2020a': toolchains[2],
            '10.2.0': toolchains[3], '2020b': toolchains[3],
            '10.3.0': toolchains[4], '2021a': toolchains[4],
            '11.2.0': toolchains[5], '2021b': toolchains[5],
            '11.3.0': toolchains[5], '2022a': toolchains[6],
            '12.2.0': toolchains[7], '2022b': toolchains[7],
            '13.2.0': toolchains[8], '2023b': toolchains[8],
        }
        prefix = dep[0] + '-' + dep[1]
        tc_version = self.toolchain['version']
        if tc_version not in tc_versions:
            sys.stderr.writelines('Could not figure out what toolchain you are using.')
            sys.exit(1)
        dep_filenames = []
        for tc in tc_versions[tc_version]:
            dep_filenames.append('{}-{}.eb'.format(prefix, tc))
        return dep_filenames

    def search_dependencies(self, eb):
        """ inspect dependencies for R and Python easyconfigs,
        if found add the exts_list to the list of dependent
        exts  <dep_exts>
        """
        try:
            dependencies = eb.dependencies
        except NameError:
            return None
        for dep in dependencies:
            if self.lang == 'Python' and self.pyver is None and dep[0] == 'Python':
                self.interpolate['pyver'] = dep[1]
                self.pyver = dep[1]
            if self.lang == 'R' and self.rver is None and dep[0] == 'R':
                self.interpolate['rver'] = dep[1]
                self.rver = dep[1]
            dep_filenames = self.build_dep_filename(eb, dep)
            logging.debug('dependency file name: {}'.format(dep_filenames))
            easyconfig_filename = self.find_easyconfig(dep[0], dep_filenames)
            if not easyconfig_filename:
                print('== dependency Not Found: {}'.format(dep_filenames[0]))
                continue
            if self.verbose:
                print('== reading dependcy: {}'.format(os.path.basename(easyconfig_filename)))
            dep_eb = self.parse_eb(str(easyconfig_filename), False)
            # Histroicly easyblock PythonPackage does not have an exts_list
            # The filename is the name of the Python Library
            if hasattr(dep_eb, 'easyblock') and dep_eb.easyblock == 'PythonBundle':
                self.dep_exts.extend([(dep_eb.name, dep_eb.version, 'Module')])
                logging.debug('== adding dep {} {}'.format(dep_eb.name, dep_eb.version))
            if 'exts_list' in dep_eb.__dict__:
                self.dep_exts.extend(dep_eb.exts_list)
                if self.verbose:
                    print('== adding dependices: {}'.format(os.path.basename(easyconfig_filename)))


    def check_eb_package_name(self, filename):
        """" check that easybuild filename matches package name
        easyconfig is original filename
        """
        eb_name = os.path.basename(filename)[:-3]
        if eb_name != self.modulename:
            sys.stderr.write("Warning: file name does not match easybuild " +
                             "module name\n"),
        if eb_name != self.modulename:
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
