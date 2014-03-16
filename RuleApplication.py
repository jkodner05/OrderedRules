#!/usr/bin/python
# -*- coding: utf-8 -*-

import codecs
from copy import copy
import re
from collections import OrderedDict
from itertools import groupby
import sys
from Executor import *
from GlobalGrammar import *

def main(args):
    grammar = Executor(GlobalGrammar(args[0]))
    grammar.apply_to_inputs(args[1])


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise ValueError("Correct Usage: python RuleApplication.py <config file> <input file>")
    main(sys.argv[1:])

