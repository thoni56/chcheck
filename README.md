# chcheck
Check if all externally visible definitions in a .c file have a
declaration in the .h file and vice versa

## Problem

In a large C project you often want to see you C files as
modules/units with externally visible interfaces.  That interface
should be declared in the header file for the module. Over time the
content of the body (.c) and the header (.h) might diverge, so the
problem becomes to ensure that for each module these match.

You get some help from the compiler that checks for missing
declarations, mismatched signatures etc. But it does not care from
which file the definition comes. So if you refactor and move and
rename a function you might end up with incorrect "interface"
declarations.

I asked a question on Stack Overflow but got no good answers (the
question seems to be hard to understand, probably because I'm bad at
explaining, or others just don't think like I do about keeping things
tidy...).

So this is my own tool to find if a header file contains all the
external symbols (for now, functions) from the corresponding C file
and nothing else.

## Solution

I jumped at [`pycparser`](https://github.com/eliben/pycparser), which
is an extremely handy tool when it comes to doing various things with
C code, such as the `cgreen-mocker` for the
[`cgreen`](https://github.com/cgreen-devs/cgreen) unittesting and
mocking framework. Thanks @eliben!
