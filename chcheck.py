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
# Since it uses pycparser it will only handle C and you will
# probably need the pycparsers "fake_libc_include" to avoid parsing
# the whole world of libc headers. To use it, make a soft link with
# the name 'pycparser' in the directory you are running this from, or
# in the directory of 'cgreen-mocker' itself, to the top directory of
# the pycparser source, and cgreen-mocker will pick it up
# automatically. Or you can point to the fake_libc directory using a
# command line 'cpp_directive' arg:
#
#    chcheck -I../pycparser/utils/fake_libc_include ...
#
# This tool was inspired by my StackOverflow question and the cgreen-mocker
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
        self.symbols = []

    def visit_FuncDef(self, node):
        # Only consider definitions that are in the processed file
        if node.coord.file == self.filename:
            # Disregard 'static' declared symbols
            if not 'static' in node.decl.storage:
                self.symbols.append(node.decl.name)


class FuncDeclVisitor(c_ast.NodeVisitor):
    def __init__(self, filename):
        self._types = {}
        self.filename = filename
        self.symbols = []

    def visit_FuncDecl(self, node):
        # Only consider declarations that are in the processed file
        if node.coord.file == self.filename:
            self.symbols.append(self.declname(node))

    def declname(self, node):
        if isinstance(node.type, c_ast.PtrDecl):
            return self.declname(node.type)
        else:
            return node.type.declname


def compare_header_and_body(args):
    # Note that cpp is used. Provide a path to your own cpp or
    # make sure one exists in PATH.

    cpp_args = [  # Add some common GNUisms
        r'-D__gnuc_va_list(x)=',
        r'-D__attribute__(x)=',
        r'-D__extension__=',
        r'-D__restrict=',
        r'-D__inline='
    ]
    if len(args) > 1:
        # Append all command line arguments except the last
        cpp_args.extend(args[:-1])

    # Try to find a fake_libc
    pycparser_path = None
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

    if not pycparser_lib == None:
        cpp_args.append('-I'+pycparser_lib)

    # Module name should be last argument
    module = args[-1]
    try:
        definitions_ast = parse_file(
            module+'.c', use_cpp=True, cpp_args=cpp_args)
    except ParseError as e:
        print("ERROR processing {}: {} - C99 parse error".format(module+'.c', e))
        exit(-1)

    try:
        declarations_ast = parse_file(
            module+'.h', use_cpp=True, cpp_args=cpp_args)
    except ParseError as e:
        print("ERROR processing {}: {} - C99 parse error".format(module+'.h', e))
        exit(-1)

    c_visitor = FuncDefVisitor(module+'.c')
    c_visitor.visit(definitions_ast)
    h_visitor = FuncDeclVisitor(module+'.h')
    h_visitor.visit(declarations_ast)

    without_definition = [
        "  "+symbol for symbol in c_visitor.symbols if symbol not in h_visitor.symbols]
    if len(without_definition) > 0:
        print("Externally visible definitions in '{}.c' that are not in '{}.h':".format(
            module, module))
        print(*without_definition, sep='\n')
        print()
    without_declaration = [
        "  "+symbol for symbol in h_visitor.symbols if symbol not in c_visitor.symbols]
    if len(without_declaration) > 0:
        print("Declarations in '{}.h' that have no externally visible definition in '{}.c':".format(
            module, module))
        print(*without_declaration, sep='\n')
    if len(without_declaration) == 0 and len(without_definition) == 0:
        return 0
    return -1


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

    NOTE: you should give the module name, not a filename with '.c' or
    '.h' extension. It is assumed that both exists and they are
    checked against each other.

    If chcheck encounters parse errors and they look like gnu-isms you
    should get a copy of the source for pycparser (on which
    cgreen-mocker is built). In it you will find a 'fake_libc_include'
    which helps. Create a symbolic link named 'pycparser' that links to
    the root of pycparser source and chcheck will find it by
    itself.

    You can find pycparser at https://github.com/eliben/pycparser

""")


if __name__ == "__main__":
    if not len(sys.argv) > 1:
        usage()
        exit(-1)

    # Is the last argument a .c or .h filename? Should be a module name
    possible_extension = sys.argv[-1][-2:]
    if possible_extension == '.c' or possible_extension == '.h':
        usage()
        exit(-1)

    module = sys.argv[-1]
    # Check that both <module>.h and <module>.c exists
    if not os.path.exists(module+'.c') or not os.path.exists(module+'.h'):
        print("ERROR: both '{}.c' and '{}.h' must exist".format(module, module))
        exit(-1)

    # Send all arguments to the main function except the first
    error_code = compare_header_and_body(sys.argv[1:])
    exit(error_code)
