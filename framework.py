#!/usr/bin/env python

import re
import os
import sys
import shutil
import argparse
import types
import requests
import logging

""" 1.0.3 Dec 16, 2020 (Beethoven's 250th birthday)
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

__version__ = '1.0.3'
__maintainer__ = 'John Dey jfdey@fredhutch.org'
__date__ = 'Nov 21, 2020'

logging.basicConfig(format='%(levelname)s [%(filename)s:%(lineno)-4d] %(message)s',
    level=logging.WARN)

class FrameWork:
    """provide access to EasyBuild Config file variables
    name, version, toolchain, eb.exts_list, dependencies, modulename, biocver,
    methods:
        print_update()
    """
    def __init__(self, args):
        if args.debug:
            logging.getLogger().setLevel(logging.DEBUG)
            logging.debug('debug enabled')
        self.verbose = args.verbose
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

        self.find_easyconfig_paths(args.easyconfig)
        logging.debug("EasyConfig search paths: {}".format(self.base_paths))

        # update EasyConfig exts_list

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
        self.detect_language(eb)
        self.search_dependencies(eb, self.lang)
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
        if self.lang == 'R':
            try:
                self.biocver = eb.local_biocver
            except AttributeError:
                self.biocver = None
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
        header += 'GITHUB_SOURCE = "https://github.com/%(github_account)s/%(name)s"\n'
        header += 'GITHUB_LOWER_SOURCE = "https://github.com/%(github_account)s/%(namelower)s"\n'
        header += ('PYPI_SOURCE = "https://pypi.python.org/packages/' +
                   'source/%(nameletter)s/%(name)s"\n')
        header += ('SOURCEFORGE_SOURCE = "https://download.sourceforge.net/' +
                   '%(namelower)s"\n')
        header += ("OS_PKG_OPENSSL_DEV = (('openssl-devel', 'libssl-dev', 'libopenssl-devel'),\n" +
                   '                      "OS packages providing openSSL developement support")\n')
        header += 'SOURCE_WHL = "%(name)s-%(version)s-py2.py3-none-any.whl"\n'
        header += 'SOURCE_PY3_WHL = "%(name)s-%(version)s-py3-none-any.whl"\n'
        header += 'SYSTEM = {"name": "system", "version": "system"}\n'
        eb = types.ModuleType("EasyConfig")
        try:
            with open(file_name, "r") as f:
                code = f.read()
        except IOError as err:
            logging.debug("opening %s: %s" % (file_name, err))
            sys.exit(1)
        try:
            exec (header + code, eb.__dict__)
        except Exception as err:
            logging.debug("interperting EasyConfig error: %s" % err)
            sys.exit(1)
        if primary:     # save original text of source code
            self.code = code

        # R module might have been installed without extensions.
        # Start with an empty list if it is the case.
        if 'exts_list' not in eb.__dict__:
            eb.exts_list = []

        return eb

    def detect_language(self, eb):
        """ R or Python? EasyConfig parameters: easyblock or name
        Test Case: CNVkit
        """
        if eb.name == 'Python':
            self.lang = str(eb.name)
            self.interpolate['pyver'] = eb.version
        elif eb.name == 'R':
            self.lang = str(eb.name)
            self.interpolate['rver'] = eb.version
        elif eb.easyblock == 'PythonPackage' or eb.easyblock == 'PythonBundle':
            self.lang = 'Python'
        elif eb.easyblock == 'RPackage':
            self.lang = 'R'
        elif self.defaultclass:
            self.lang = eb.exts_defaultclass.replace('Package', '')
        else:
            logging.warn('Can not determine languge of module. R or Python?')

    def find_easyconfig_paths(self, filename):
        """find the paths to EasyConfigs, search within the path given by the easyconfig
        given to update. Search for eb command
        """
        userPath = os.path.expanduser(filename)
        fullPath = os.path.abspath(userPath)
        (head, tail) = os.path.split(fullPath)
        self.base_paths = []
        while tail:
            if 'easyconfig' in tail:
                self.base_paths.append(os.path.join(head, tail))
                logging.debug('local path to easyconfigs: {}'.format(self.base_paths[-1]))
                break 
            (head, tail) = os.path.split(head)
        eb_path = os.getenv('EBROOTEASYBUILD') 
        if eb_path:
            self.base_paths.append(os.path.join(eb_path, 'easybuild/easyconfigs'))
        else:
            sys.stderr.writelines('Could not find path to EasyBuild, EasyBuild module must be loaded')
            sys.exit(1)
        logging.debug('easyconfig search paths: {}'.format(eb_path))


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
            ['fosscuda-2021b', 'foss-2021b', 'GCCcore-11.2.0', 'GCC-11.2.0', 'gompi-2021b'],
        ]
        tc_versions = {
            '8.2.0': toolchains[0], '2019a': toolchains[0],
            '8.3.0': toolchains[1], '2019b': toolchains[1],
            '9.3.0': toolchains[2], '2020a': toolchains[2],
            '10.2.0': toolchains[3], '2020b': toolchains[3],
            '10.3.0': toolchains[4], '2021a': toolchains[4],
            '11.2.0': toolchains[5], '2021b': toolchains[5],
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


    def search_dependencies(self, eb, lang):
        """ inspect dependencies for R and Python easyconfigs,
        if found add the exts_list to the list of dependent
        exts  <dep_exts>
        """
        try:
            dependencies = eb.dependencies
        except NameError:
            return None
        for dep in dependencies:
            if self.pyver is None and dep[0] == 'Python':
                self.interpolate['pyver'] = dep[1]
                self.pyver = dep[1]
                logging.debug('primary language Python {}'.format(self.pyver))
            if self.rver is None and dep[0] == 'R':
                self.interpolate['rver'] = dep[1]
                self.rver = dep[1]
                logging.debug('primary language R-{}'.format(self.rver))
            dep_filenames = self.build_dep_filename(eb, dep)
            logging.debug('dependency file names: {}'.format(dep_filenames))
            easyconfig = self.find_easyconfig(dep[0], dep_filenames)
            for dep_filename in dep_filenames:
                easyconfig = self.find_easyconfig(dep[0], dep_filenames)
                if easyconfig:
                    if self.verbose:
                        print('== reading extensions from: {}'.format(os.path.basename(easyconfig)))
                    eb = self.parse_eb(str(easyconfig), False)
                    if hasattr(eb, 'easyblock') and eb.easyblock in ['PythonBundle', 'PythonPackage']:
                        self.dep_exts.extend([eb.name, eb.version])
                        print('== adding {}'.format(eb.name))
                    try:
                        self.dep_exts.extend(eb.exts_list)
                    except (AttributeError, NameError):
                        self.dep_exts.extend([dep])
                    break
                else:
                    print('== Not Found: {}'.format(dep_filename))


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
