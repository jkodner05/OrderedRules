#!/usr/bin/python
# -*- coding: utf-8 -*-

import codecs
from copy import copy
import re
from collections import OrderedDict
from itertools import groupby
import sys
from Phone import *
from Globals import *


class Rule(object):
    """Representation of ordered rule"""

    def __init__(self, rule_str, features, abbrevs):
        self.raw_rule = rule_str
        self.rule_name = self.raw_rule.split(":")[0]
        self.rule_str = self.raw_rule.split(":")[1].strip()
#        print rule_str
        self.features = features
        self.abbrevs = abbrevs
        rule_list = re.split('[/>_]',self.rule_str)
#        self.seg_match = [self.get_seg_feats(match) for match in self.divide_segs(rule_list[0].strip())][0] # A
        self.seg_match = self.divide_segs(rule_list[0].strip()) #A
#        print "sm\t", self.seg_match
#        self.seg_match = [self.get_seg_feats(match) for match in self.divide_segs(rule_list[0].strip())][0] # A
        self.seg_change = self.get_seg_feats(rule_list[1].strip()) # B
#        print "sc\t",self.seg_change
#        self.seg_change = self.get_seg_feats([rule_list[1].strip()])[0] # B
        self.pre_env = self.divide_segs(rule_list[2].strip()) if len(rule_list) > 2 else None # C
#        print "pre env", self.pre_env
        self.post_env = self.divide_segs(rule_list[3].strip()) if len(rule_list) > 2 else None # D


#        print "\tseg   match:", self.seg_match
#        print "\tseg  change:", self.seg_change

#        print "\tpre    env:", self.pre_env

#        print "\tpost   env:", self.post_env
#        print ""
#        print self.seg_match
        self.seg_match = map(lambda y: [self.get_seg_feats(char) for char in y],filter(lambda x: x != [SYLL], self.seg_match))[0]
        if self.pre_env:
            self.pre_env_sylls = self.count_syll_offsets(self.pre_env, pre=True)
            self.pre_env = map(lambda y: [self.get_seg_feats(char) for char in y],filter(lambda x: x != [SYLL], self.pre_env))
            self.pre_syll_aware = SYLL in rule_list[2]
        else:
            self.pre_env_sylls = None
            self.pre_syll_aware = False
        if self.post_env:
            self.post_env_sylls = self.count_syll_offsets(self.post_env, pre=False)
            self.post_env = map(lambda y: [self.get_seg_feats(char) for char in y],filter(lambda x: x != [SYLL], self.post_env))
            self.post_syll_aware = SYLL in rule_list[3]
        else:
            self.post_env_sylls = None
            self.post_syll_aware = False

#        print "\tseg   match:", self.seg_match
#        print "\tseg  change:", self.seg_change
#        print "\tpre    env:", self.pre_env
#        print "\tpre  sylls:", self.pre_env_sylls
#        print "\tpost   env:", self.post_env
#        print "\tpost sylls:", self.post_env_sylls
#        print "\n\n"

        self.seg_match_str = rule_list[0]
        self.seg_change_str = rule_list[1]

    def count_syll_offsets(self, env, pre):
        acc = 0
        sylls = []
        if pre:
            inc = lambda a : a-1
            env.reverse()
        else:
            inc = lambda a : a+1
        for seg in env:
#            print "abc", seg
            if seg == [SYLL]:
                acc = inc(acc)
#                print "acc",acc
            else:
                sylls.append(acc)
        if pre:
            sylls.reverse()
            env.reverse()
        return sylls

    def divide_segs(self, segs):

        def split_sets(raw_str):
            return filter(None, re.split("[{}]",raw_str))

        def split_comma(seg):
            return re.sub("\[","{\[",re.sub("\]","\]}",seg)).split(",")

        def split_options(seg):
            return [split_chars(filter(None,re.split("[{}]", seg.strip()))) for seg in re.sub("\[","{[",re.sub("\]","]}",seg)).split(",")]

        def split_chars(options):
            return unnest([[char for char in option.strip()] if '[' not in option else [option] for option in options])

        def unnest(seg):
            return [option for options in seg for option in options]

        def flatten(segs):
            def rectify_sets(segs):
                return [[[char] for option in seg for char in option] if len(seg) <= 1 else [[char.encode("utf-8") for option in seg for char in option]] for seg in segs]

#            print "unfeated",[char for seg in rectify_sets(segs) for char in seg]
#            print ""
            return [char for seg in rectify_sets(segs) for char in seg]
#            return [[self.get_seg_feats(char)] for seg in rectify_sets(segs) for char in seg]

        return flatten(map(split_options, split_sets(segs)))

    def get_seg_feats(self, match_str):
        if NULL in match_str.encode("utf-8"):
            return [None]
        elif match_str not in self.abbrevs:
#            print "MATCH_STR   ", match_str
#            print "MATCH_STR[0]", match_str[0]
            return get_features(self.features, re.sub("[\[|\]]","",match_str.strip()))
        else:
            return self.abbrevs[match_str]
#        return [None] if NULL in match_str else [get_features(self.features, re.sub("[\[|\]]","",match.strip())) if match not in self.abbrevs else self.abbrevs[match] for match in match_str]
        
    def has_env(self):
        return (self.pre_env or self.post_env)

