#!/usr/bin/env python3

"""
    EasyUpdate performs package version updating for EasyBuild
    easyconfig files. Automates the updating of version information for R,
    Python and bundles that extend R and Python. Package version information
    is updated for modules in exts_list. Use language specific APIs for resolving
    current version for each package.
"""

import sys
import argparse
import logging
from framework import FrameWork
from updateR import UpdateR
from updatePython import UpdatePython

__version__ = '2.3.0'
__date__ = 'March  2025'
__maintainer__ = 'John Dey jfdey@fredhutch.org'

logging.basicConfig(format='%(levelname)s [%(filename)s:%(lineno)-4d] %(message)s',
                    level=logging.DEBUG)
logging.basicConfig(format='%(levelname)s [%(filename)s:%(lineno)-4d] %(message)s',
                    level=logging.WARN)
logging.basicConfig(format='%(message)s', level=logging.INFO)


def setup_parser():
    parser = argparse.ArgumentParser(description='Update EasyConfig exts_list')
    parser.add_argument('--version', action='version', version='%(prog)s ' + 
                        __version__ + '  ' + __date__)
    parser.add_argument('-v', '--verbose', dest='verbose', required=False, 
                        action='store_true',
                        help='Verbose; print lots of extra stuff')
    parser.add_argument('--debug', required=False, action='store_true',
                        help='set log level to debug, (default: false)')
    # Create parent mutually exclusive group
    group = parser.add_mutually_exclusive_group(required=True)

    group.add_argument('--exts-update', dest='operation', action='store_const', const=(True, 'update'),
                       metavar='easyconfig', help='update version info for exts_list in EasyConfig')
    group.add_argument('--exts-annotate', dest='operation', action='store_const', const=(True, 'annotate'),
                       metavar='easyconfig', help='Annotate all extensions from EasyConfig and dependencies')
    group.add_argument('--exts-dep-graph',  dest='operation', action='store_const', const=(True, 'dep_graph'),
                       metavar='easyconfig',  help='print Graph dependancies for exts')
    group.add_argument('--exts-description', dest='operation', action='store_const', const=(True, 'description'),
                       metavar='easyconfig',  help='Output descrption for libraries in exts_list')
    group.add_argument('--exts-search-cran', dest='operation', action='store_const', const=(False, 'search_cran'),
                       metavar='Library', help='output libray metadata from CRAN/BioConductor')
    group.add_argument('--exts-search-pypi', dest='operation', action='store_const', const=(False, 'search_pypi'),
                       metavar='Library', help='output library metadata from PyPi')
    parser.add_argument('value', nargs='?', help='Value for the selected operation')

    return parser


def process_arguments(args):
    """Handle the parsed command line arguments"""
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
    if args.verbose:
        logging.getLogger().setLevel(logging.INFO)
    if not args.operation or not args.value:
        parser.error("A value must be provided for the selected operation")
        sys.exit(1)

    is_file, operation = args.operation
    argument = args.value
    verbose = args.verbose
    return (is_file, operation, verbose, argument)


def main():
    """ main """
    parser = setup_parser()
    args = parser.parse_args()
    return process_arguments(args)


if __name__ == '__main__':
    (is_file, operation, verbose, argument) = main()

    if is_file:
        no_dependencies = False
        if operation in ['dep_graph', 'description']:
            no_dependencies = True
        eb = FrameWork(argument, verbose, no_dependencies)
        if operation in ['update', 'annotate', 'description']:
            if eb.language == 'R':
                UpdateR(argument, operation, verbose, eb)
            elif eb.language == 'Python':
                UpdatePython(argument, operation, verbose, eb)
        elif operation == 'dep_graph':
            if eb.language == 'Python':
                UpdatePython(arg, operation, verbose, eb)
