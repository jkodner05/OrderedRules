#!/usr/bin/python
# -*- coding: utf-8 -*-

import codecs
from copy import copy
import re
from collections import OrderedDict
from itertools import groupby
import sys
from Rule import *

TRUE = 1
FALSE = 0
UNDEF = 2

NULL = "∅"
SYLL = "σ".decode("utf-8")


PADDING = 2
                    
class GlobalGrammar():
    """Processes config file to represent phonological grammar"""

    def __init__(self, filename):
        self.features = None
        self.phones = None
        self.syllables = None
        self.rules = None
        self.sections = self.section_file(filename)


    def section_file(self, filename):
        """Divide config file into sections, parse each section"""
        f = open(filename, "r")
        in_feat = True
        full = f.read().decode("utf-8").split("!")
        sec_filter = lambda x, sec: filter(lambda y: sec in y, x)[0]
        self.features = self.read_features(sec_filter(full, "FEATURE"))
        self.phones = self.map_phones(sec_filter(full, "PHONEME"),sec_filter(full, "ABBREV"))
        self.phone_char_mappings = self.map_phone_chars(sec_filter(full, "PHONEME"), sec_filter(full, "ABBREV"))
        self.syllables = self.read_syllables(sec_filter(full, "SYLL"))
        self.rules = self.parse_rules(sec_filter(full, "RULE"))
        return full

    def read_features(self, feature_sec):
        """remove character names from list of binary features"""
        return [line.split(":")[1].strip() for line in 
                filter(lambda x:
                           x and "FEATURE" not in x, feature_sec.split("\n"))]

    def map_phones(self, phone_sec, abbrev_sec):
        """map phonemes, abbreviations, and word boundary (#) characters to dictionaries of binary feature values"""
        combined = phone_sec + abbrev_sec
        return {line.split(":")[0].split()[-1].strip() : get_features(self.features,line.split(":")[1].strip()) for line in 
                filter(lambda x:
                           x and "ABBREV" not in x and "PHONE" not in x, combined.split("\n"))}        

    def map_phone_chars(self, phone_sec, abbrev_sec):
        """Some phones are represented by 2+ characters. Map those to single characters as specified in config file"""
        combined = phone_sec + abbrev_sec
        return {line.split(":")[0].split()[-1].strip() : line.split(":")[0].split()[0].strip() for line in 
                filter(lambda x:
                            x and "ABBREV" not in x and "PHONE" not in x, combined.split("\n"))}        

    def read_syllables(self, syll_sec):
        """Read syllable formats, decompose into sets of nuclei (the vowel, probably), onsets (before the nucleus), and codas (after the nucleus)"""
        syllables = set([line.strip() for line in 
                filter(lambda x:
                           x and "SYLL" not in x, syll_sec.split("\n"))])

        nuclei = set([phone for phone in self.phones.keys() if self.phones[phone]["syll"] == TRUE])
        onsets = set([re.split("["+"".join(nuclei)+"]",syll)[0] for syll in syllables])
        codas = set([re.split("["+"".join(nuclei)+"]",syll)[1] for syll in syllables])
        return {'syllables':syllables,'onsets':onsets,'codas':codas}

    def parse_rules(self, rule_sec):
        """Create a new rule for each rule line:
        format:
        A > B
        A > B / C_
        A > B / _D
        A > B / C_D
        Read as "The features of B are applied to any phone matching A in the environment after C and before D"
        A, C, D may be phones, abbreviations, or sets of features
        B may be a phone or set of features"""

        rulestrs = [line.strip().split(":") for line in 
                filter(lambda x:
                           x and "RULE" not in x, rule_sec.split("\n"))]
        max_len = len(max(rulestrs, key=lambda x: len(x[0].strip()))[0].strip())
        rulestrs = [rule[0].strip().ljust(max_len)+":"+rule[1] for rule in rulestrs]
        rule_list = [Rule(rule,self.features,self.phones) for rule in rulestrs]
        
        #group rules by name
        return [(key, list(group)) for key, group in groupby(rule_list, lambda x: x.rule_name)]
