#!/usr/bin/env python3

import os
import sys
import types
import logging
from templates import TEMPLATE_CONSTANTS
from constants import EASYCONFIG_CONSTANTS
# from easybuild.tools.toolchain.constants import ALL_MAP_CLASSES
# from easybuild.framework.easyconfig.templates import TEMPLATE_CONSTANTS

"""
    1.0.5 Oct 11, 2024 - Add back in the ability to read the EasyConfig file
    to determine the language.
    - Enable the "description" feature

    1.0.4 Nov, 2022
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

__version__ = '1.0.5'
__maintainer__ = 'John Dey jfdey@fredhutch.org'
__date__ = 'Oct 10, 2024'

logging.basicConfig(format='%(levelname)s [%(filename)s:%(lineno)-4d] %(message)s',
                    level=logging.WARN)
#logging.getLogger().setLevel(logging.DEBUG)

class FrameWork:
    """provide access to EasyBuild Config file variables
    name, version, toolchain, eb.exts_list, dependencies, modulename, biocver,
    """
    def __init__(self, easyconfig, verbose, no_dependencies):
        self.easyconfig = easyconfig
        self.verbose = verbose
        self.language = None
        self.code = None
        self.pyver = None
        self.rver = None
        self.search_pkg = None
        self.indent_n = 4
        self.indent = ' ' * self.indent_n
        self.ptr_head = 0
        self.modulename = None
        self.dep_exts = []
        self.exts_list = []
        self.find_easyconfig_paths(easyconfig)
        logging.debug("EasyConfig search paths: {}".format(self.base_paths))

        # update EasyConfig exts_list

        eb = self.parse_eb(easyconfig, primary=True)
        self.exts_list = eb.exts_list
        self.toolchain = eb.toolchain
        self.name = eb.name
        self.version = eb.version
        self.pyver = self.rver = None
        self.find_language_version(eb)
        self.interpolate = {'name': eb.name, 'namelower': eb.name.lower(),
                            'version': eb.version,
                            'pyver': self.pyver,
                            'rver': self.rver,
                            'cudaver': ""}
        if no_dependencies:
            return
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
            logging.WARN('WARNING: no dependencies defined!')
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
            header += '{} = "{}"\n'.format(constant, EASYCONFIG_CONSTANTS[constant])
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
            logging.error(f'interperting EasyConfig error: {err}')
            sys.exit(1)
        if primary:     # save original text of source code
            self.code = code
        return eb

    def find_language_version(self, eb):
        """ find the language and version from the EasyConfig file """
        if (eb.name == 'Python' or
            ('easyblock' in eb.__dict__ and eb.easyblock == 'PythonBundle' or eb.easyblock == 'PythonPackage') or
            ('exts_defaultclass' in eb.__dict__ and eb.exts_defaultclass == 'PythonPackage')
            ):
            print('== Python EasyConfig')
            self.language = 'Python'
            if self.name == 'Python':
                self.pyver = eb.version
            else:
                for dep in eb.dependencies:
                    if dep[0] == 'Python':
                        self.pyver = dep[1]
                        break
        elif (eb.name == 'R' or
              ('easyblock' in eb.__dict__ and eb.easyblock == 'RPackage') or
              ('exts_defaultclass' in eb.__dict__ and eb.exts_defaultclass == 'RPackage')
              ):
            self.language = 'R'
            if self.name == 'R':
                self.rver = eb.version
            else:
                for dep in eb.dependencies:
                    if dep[0] == 'R':
                        self.rver = dep[1]
                        break
        else:
            msg = """Unknown language exts_list type. Expecting Python or R based easyconfig
    easyblock: ['PythonBundle', 'RPackage'] or
    exts_defaultclass: ['PythonPackage', 'RPackage']"""
            print('Error: {} {}'.format(eb.name, msg))

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
            ['foss-2023a', 'GCCcore-12.3.0', 'GCC-12.3.0', 'gompi-2023a', 'gfbf-2023a'],
            ['foss-2023b', 'GCCcore-13.2.0', 'GCC-13.2.0', 'gompi-2023b', 'gfbf-2023b'],
        ]
        tc_versions = {
            '8.2.0': toolchains[0], '2019a': toolchains[0],
            '8.3.0': toolchains[1], '2019b': toolchains[1],
            '9.3.0': toolchains[2], '2020a': toolchains[2],
            '10.2.0': toolchains[3], '2020b': toolchains[3],
            '10.3.0': toolchains[4], '2021a': toolchains[4],
            '11.2.0': toolchains[5], '2021b': toolchains[5],
            '11.3.0': toolchains[6], '2022a': toolchains[6],
            '12.2.0': toolchains[7], '2022b': toolchains[7],
            '12.3.0': toolchains[8], '2023a': toolchains[8],
            '13.2.0': toolchains[9], '2023b': toolchains[9],
        }
        prefix = dep[0] + '-' + dep[1]
        if (len(dep)) == 4 and dep[3] == 'System toolchain':
            dep_filenames = prefix + '.eb'
            return [dep_filenames]
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
        print('== searching dependencies')
        try:
            dependencies = eb.dependencies
        except NameError:
            return None
        for dep in dependencies:
            dep_filenames = self.build_dep_filename(eb, dep)
            easyconfig_filename = self.find_easyconfig(dep[0], dep_filenames)
            if not easyconfig_filename:
                print('== dependency Not Found: {}'.format(dep_filenames[0]))
                continue
            logging.debug('dependency file name: {}'.format(dep_filenames))
            dep_eb = self.parse_eb(str(easyconfig_filename), False)
            if self.language == 'Python':
                if dep[0] == 'Python' and self.pyver is None:
                    self.interpolate['pyver'] = dep[1]
                    self.pyver = dep[1]
                self.add_to_python_dep_exts(dep_eb, easyconfig_filename, self.dep_exts)
            elif self.language == 'R':
                if dep[0] == 'R' and self.rver is None:
                    self.interpolate['rver'] = dep[1]
                    self.rver = dep[1]
                    if 'exts_list' in dep_eb.__dict__:
                        self.dep_exts.extend(dep_eb.exts_list)
            if self.verbose:
                print('== adding dependencies: {}'.format(os.path.basename(easyconfig_filename)))
            
    def add_to_python_dep_exts(self, dep_eb, easyconfig_filename, dep_exts):
        """ Python Dependants have many ways to specify the module name.
            add package to dep_exts if not already in list
            - PythonPackage does not have exts_list. Add name and verstion to dep_exts
        """
        base_name = os.path.basename(easyconfig_filename)
        if 'easyblock' in dep_eb.__dict__ and dep_eb.easyblock == 'PythonPackage':
            self.dep_exts.append([dep_eb.name, dep_eb.version, {'module': base_name}])
            if '-' in dep_eb.name:
                self.dep_exts.append([dep_eb.name.replace('-', '_'), dep_eb.version, {'module': base_name}])
            if 'options' in dep_eb.__dict__ and 'modulename' in dep_eb.options:
                self.dep_exts.append([dep_eb.options['modulename'], dep_eb.version,
                                     {'module': os.path.basename(base_name)}])
        if 'exts_list' in dep_eb.__dict__:
            for ext in dep_eb.exts_list:
                if ext not in self.dep_exts:
                    if len(ext) > 2 and 'module' in ext[2]:
                        self.dep_exts.append([(ext[0], ext[1], {'module': ext[2]['module']})])
                    else:
                        self.dep_exts.append([ext[0], ext[1], {'modulename': base_name}])
            
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
