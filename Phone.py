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

TRUE = 1
FALSE = 0
UNDEF = 2

NULL = "∅"
SYLL = "σ".decode("utf-8")



class Phone(object):
    """Representation of phone. Contains feature information, character representation information, and syllabification related information"""

    def __init__(self, features=None, phone=None, boundary=False):
        self.syll = -1
        self.mora = False
        self.mapped = phone
        self.name = phone
        self.features = features
        self.to_delete = False
        self.add_here = False

    def __str__(self):
        """Don't use this. Unicode mess"""
        mapped = self.mapped
        if not mapped:
            mapped = ""
        title = mapped + " " 
#        print self.features
        return title
