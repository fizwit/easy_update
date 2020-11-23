#!/usr/bin/env python

import os
import sys
import argparse
import requests
import logging

""" 
version 1.0.0 Nov 22, 2020
search meta data for Python, R, Biocondutor package

work in progress, 
"""

def main():
    """ main """
    parser = argparse.ArgumentParser(description='Library metadata search')

    parser.add_argument('--version', action='version',
                        version='%(prog)s ' + __version__)
    parser.add_argument(
        '-v', '--verbose', dest='verbose', required=False, action='store_true',
        help='Verbose; print lots of extra stuff, (default: false)')
    parser.add_argument('--rver', dest='rver', required=False, action='store',
                        help='Set R version (major.minor) example 3.6')
    bioc_help = 'Set BioConductor version (major.minor) example 3.9. '
    bioc_help += 'Use with --rver'
    parser.add_argument('--pypisearch', dest='pypisearch', required=False, action='store',
                        help='Search PYPI for package info and dependencies')
    parser.add_argument('--rsisearch', dest='rsearch', required=False, action='store',
                        help='Search CRAN for R libraries')
    parser.add_argument('--meta', dest='meta', required=False, action='store_true',
                        help='output select meta data keys from Pypi, if used with ' +
                             'verbose all metadata is output (default: false)')
    args = parser.parse_args()

    eb = None
    args.lang = None
    args.search_pkg = None
    if args.easyconfig:
        eb = FrameWork(args)
        args.lang = eb.lang
        if eb.lang == 'Python':
            args.pyver = eb.pyver
        if eb.lang == 'R':
            args.rver = eb.rver

    if args.pypisearch:
        args.lang = 'Python'
        args.search_pkg = args.pypisearch
    if args.rsearch:
        args.lang = 'R'
        args.search_pkg = args.rsearch

    if args.lang == 'R':
        UpdateR(args, eb)
    elif args.lang == 'Python':
        UpdatePython(args, eb)
    else:
        print('error: If no EasyConfig or search command:  ' +
              'easy_update --help')
        sys.exit(1)


if __name__ == '__main__':
    main()