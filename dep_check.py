#!/usr/bin/env python

import os
import sys
import argparse
import json
import pygraphviz as dot 

""" Easybuild dependancy checker. Scan output of eb --dep-graph.
check for duplicate modules with different versions.
report duplicates and there source package
"""

__version__ = '1.0.0'
__author__ = 'John Dey jfdey@fredhutch.org'
__date__ = 'Jan 25, 2018'


def find_duplicate(G):
    """ scan nodes for duplicate modules
    input: <G> graphviz
    """
   pass

def main():
    """ main """

    parser = argparse.ArgumentParser(description='Update easyconfig extslist')
    parser.add_argument('--version', action='version',
                        version='%(prog)s ' + __version__)
    parser.add_argument('-v', '--verbose', dest='verbose', required=False,
                        action='store_true',
                        help='Verbose; print lots of extra stuff, (default: false)')
    parser.add_argument('dotfile')
    args = parser.parse_args()

    G = dot.AGraph(args.dotfile)
    find_duplicate(G)

if __name__ == '__main__':
    main()
