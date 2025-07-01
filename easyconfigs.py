#!/usr/bin/env python3
# -*- coding: utf-8 -*-
""" Walk the easyconfigs directory and generate a list of all easyconfig files. Based on toolchain.

    Use the environment variable EBROOTEASYBUIILD to find the easyconfigs directory.

    Usage:
        easyconfigs.py [--toolchain=<toolchain>] [--easyconfig-path=<easyconfig_path>]
        easyconfigs.py (-h | --help)

    Options:
        -h --help                   Show this help message.
        --toolchain=<toolchain>     Toolchain to filter by. toolchain is mandatory.
        --robot=<path>    Path to the easyconfig directory.
"""
import os
import sys
import argparse
import logging
import json
from toolchains import Toolchain
from framework import FrameWork

py_modules = {}
ec_modules = {}
primary_ec_modules = [
    'SciPy-bundle',
]


def parse_args():
    parser = argparse.ArgumentParser(description='Generate a list of easyconfig files based on toolchain.')
    parser.add_argument('--verbose', action='store_true', help='Enable verbose output.')
    parser.add_argument('--toolchain', type=str, required=True, help='Toolchain to filter by. toolchain is mandatory.')
    parser.add_argument('--robot', type=str, help='Path to the easyconfigs directory.')
    return parser.parse_args()


def collect_python_modules_from_exts(eb_module_name, exts_list, primary_module):
    """ Collect the python modules from the exts list.
    Args:
        exts (list): List of extensions.
    Returns:
        list: List of python modules.
    """
    for mod in exts_list:
        module_name = mod[0]
        if len(mod) > 2 and 'modulename' in mod[2] and mod[2]['modulename']:
            module_name = mod[2]['modulename']
        if module_name not in py_modules:
            py_modules[module_name] = list([{'version': mod[1],
                                             'project_name': mod[0],
                                             'ec_module_name': eb_module_name,
                                             'primary_module': primary_module}])
        else:
            py_modules[module_name].append({'version': mod[1],
                                            'project_name': mod[0],
                                            'ec_module_name': eb_module_name,
                                            'primary_module': primary_module})
        ec_modules[eb_module_name]['extensions'].append(module_name)


def collect_python_modules(eb, eb_module_name):
    """ Collect the python modules from the exts list.
    Args:
        exts (list): List of extensions.
    """
    primary_module = False

    if eb.easyblock == 'PythonPackage' or (
       eb.exts_defaultclass == 'PythonPackage'):
        primary_module = True
    if eb.exts_list:
        exts = eb.exts_list
    if eb.py_module_name:
        exts = [(eb.name, eb.version, {'modulename': eb.py_module_name})]
    else:
        exts = [(eb.name, eb.version)]

    if 'versionsuffix' in eb.__dict__ and eb.versionsuffix:
        suffix = eb.versionsuffix
    else:
        suffix = ''
    ec_modules[eb_module_name] = {'ec_name': eb.name,
                                  'ec_version': eb.version,
                                  'ec_suffix': suffix,
                                  'ec_module_name': eb_module_name,
                                  'extensions': []}
    collect_python_modules_from_exts(eb_module_name, exts, primary_module)


def find_python_modules(easyconfig_path):
    """ read the easyconfig file and find the python modules used in the easyconfig file.
    Args:
        easyconfig_path (str): Path to the easyconfig file.
    Returns:
        list: List of python modules used in the easyconfig file.
    """
    eb = FrameWork(easyconfig_path, verbose=False, no_dependencies=True)
    if eb.language == 'Python':
        eb_module_name = os.path.basename(easyconfig_path)[:-3]
        collect_python_modules(eb, eb_module_name)


def find_easyconfigs(toolchains, easyconfig_path):
    """ Walk the EasyBuild easyconfigs directory and generate a list of
    easyconfig files that match a given toolchain. Toolchains is a list
    of toolchains to filter by.
    Args:
        toolchains (list): List of toolchains to filter by.
        easyconfig_path (str): Path to the easyconfigs directory.
    Returns:
        list: List of easyconfig files.
    """
    fcounter = 0
    ecounter = 0
    easyconfigs = []
    for root, dirs, files in os.walk(easyconfig_path):
        for file in files:
            if file.endswith('.eb'):
                for tc in toolchains:
                    if tc in file:
                        easyconfigs.append(os.path.join(root, file))
                        ecounter += 1
                        break
            fcounter += 1
            if fcounter % 500 == 0:
                print(".", end='', flush=True)
    print(f"\nFound {ecounter} Python easyconfig files in {fcounter} files for Toolchain {toolchains}")
    return easyconfigs


def get_easyconfig_path_from_env():
    """ Get the toolchain from the environment variable EBROOTEASYBUIILD. """
    ebroot = os.environ.get('EBROOTEASYBUILD')
    if ebroot:
        return os.path.join(ebroot, 'easybuild/easyconfigs')
    else:
        print("Error: The environment variable EBROOTEASYBUIILD must be set.")
        sys.exit(1)


def main():
    args = parse_args()
    if args.easyconfig_path:
        easyconfig_path = args.easyconfig_path
    else:
        easyconfig_path = get_easyconfig_path_from_env()
    if args.verbose:
        logging.basicConfig(level=logging.INFO)
    else:
        logging.basicConfig(level=logging.DEBUG)
    tc = Toolchain()
    tc.get_toolchains(args.toolchain)
    print(f"Toolchain: {args.toolchain} list: {tc.toolchains}")
    print(f"Easyconfig path: {easyconfig_path}")
    logging.info("Toolchains found: %s", ', '.join(tc.toolchains))
    logging.info("Easyconfig path: %s", easyconfig_path)

    easyconfigs = find_easyconfigs(tc.toolchains, easyconfig_path)
    for easyconfig in easyconfigs:
        find_python_modules(easyconfig)
    for mod in py_modules.keys():
        print(f"{mod}")
        for ext in py_modules[mod]:
            print(f"{ext}")
            # print(f"  - {ext['version']}  {ext['module_name']} {ext['project_name']} {ext['ec']}")
    with open("python_ec.json", "w") as fp:
        json.dump(ec_modules, fp, indent=4)


if __name__ == "__main__":
    main()
