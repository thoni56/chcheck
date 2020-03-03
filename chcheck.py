#!/usr/bin/env python
# -----------------------------------------------------------------
# chcheck <module>
#
# Checks if the external declarations in a modules .h file
# matches what is in the .c file
#
# Usage:
#   chcheck.py { <cpp_directive> } <module>
#
# <cpp_directive>: any 'cpp' directive but most useful is e.g.
#                  "-I <directory>" to ensure cpp finds files.
# <module>       : filename which will be appended ".h" and ".c"
#
# Simplistically adapted from pycparser example: func_defs.py
#
# Since it uses pycparser it will only handle C functions and you will
# probably need the pycparsers "fake_libc_include" to avoid parsing
# the whole world of libc headers. To use it, make a soft link with
# the name 'pycparser' in the directory you are running this from, or
# in the directory of 'cgreen-mocker' itself, to the top directory of
# the pycparser source, and cgreen-mocker will pick it up
# automatically. Or you can point to it using a command line
# 'cpp_directive' arg.
#
# This was inspired by my StackOverflow question and the cgreen-mocker
# in the cgreen project (https://github.com/cgreen-dev/cgreen).
#
# Thanks to @gardenia for the pointer to pycparser!
#
#    https://github.com/eliben/pycparser
#
# (C) 2020, Thomas Nilefalk
#
# Using pycparser for printing out all the functions defined in a
# C file.
#
# PyCParser - Copyright (C) 2008-2015, Eli Bendersky
# License: BSD
# -----------------------------------------------------------------
from __future__ import print_function
from pycparser.plyparser import ParseError
from pycparser import c_parser, c_ast, parse_file, c_generator
from functools import reduce
import sys
import os

# This is not required if you've installed pycparser into
# your site-packages/ with setup.py
sys.path.extend(['.', '..'])


class FuncDefVisitor(c_ast.NodeVisitor):
    def __init__(self, filename):
        self._types = {}
        self.filename = filename

    def visit_FuncDef(self, node):
        if node.coord.file == self.filename:
            # Only consider definitions that are in the processed file
            print('%s at %s' % (node.decl.name, node.decl.coord))


class FuncDeclVisitor(c_ast.NodeVisitor):
    def __init__(self, filename):
        self._types = {}
        self.filename = filename

    def visit_FuncDecl(self, node):
        # if node.coord.file == self.filename:
        # Only consider declarations that are in the processed file
        print('%s at %s' % (self.declname(node), node.coord))

    def declname(self, node):
        if isinstance(node.type, c_ast.PtrDecl):
            return self.declname(node.type)
        else:
            return node.type.declname


def show_func_defs(args):
    # Note that cpp is used. Provide a path to your own cpp or
    # make sure one exists in PATH.

    pycparser_path = None
    # Try to find a fake_libc
    if os.path.isdir('pycparser'):
        # In current directory
        pycparser_path = r'./pycparser'
    elif os.path.isdir(os.path.dirname(os.path.join(os.path.abspath(__file__),
                                                    'pycparser'))):
        # In the directory of this script
        pycparser_path = os.path.dirname(os.path.join(os.path.abspath(__file__),
                                                      'pycparser'))
    if pycparser_path:
        pycparser_lib = reduce(
            os.path.join, [pycparser_path, 'utils', 'fake_libc_include'])
    else:
        pycparser_lib = None

    # if pycparser_path:
    #    print("/* Generated with cgreen-mocker and pycparser's fake_libc from %s */" %
    #          (pycparser_path))
    try:
        ast = parse_file(args[-1], use_cpp=True,
                         cpp_args=[
                             # Add some common GNUisms
                             r'-D__gnuc_va_list(x)=',
                             r'-D__attribute__(x)=',
                             r'-D__extension__=',
                             r'-D__restrict=',
                             r'-D__inline=',
                             r'-I'+pycparser_lib if pycparser_lib else r''
        ] +
            args[0:-1])
    except ParseError as e:
        print("ERROR: {} - C99 parse error".format(e))
        return

    if args[0][-1] == 'c':
        v = FuncDefVisitor(args[0])
    else:
        v = FuncDeclVisitor(args[0])
    v.visit(ast)


def usage():
    print("""
Usage:
    chcheck.py { <cpp_directive> } <module>

    <cpp_directive>: any 'cpp' directive but most useful are e.g.
                     "-I <directory>" to ensure cpp finds files and
                     "-D <define>" to create an inline define

    <module>:        filename which will be appended with '.c' and '.h'

    chcheck checks the declarations in a C header file and checks them
    against the content of the corresponding '.c' file.

    If chcheck encounters parse errors and they look like gnu-isms you
    should get a copy of the source for pycparser (on which
    cgreen-mocker is built). In it you will find a 'fake_libc_include'
    which helps. Create a symbolic link named 'pycparser' that links to
    the root of pycparser source and chcheck will find it by
    itself.

    You can find pycparser at https://github.com/eliben/pycparser

""")


if __name__ == "__main__":
    if len(sys.argv) <= 1:
        usage()
        exit(-1)
    show_func_defs(sys.argv[1:])
