#!/usr/bin/python
# -*- coding: utf-8 -*-

import codecs
from copy import copy
import re
from collections import OrderedDict
from itertools import groupby
import sys
from GlobalGrammar import *

class Executor():
    """Put words through phonological grammar to get their surface representations"""

    def __init__(self, grammar):
        self.grammar = grammar

    def getPhoneUR(self, char):        
        """Get Phone matching character"""
        return Phone(copy(self.grammar.phones[self.grammar.phone_char_mappings[char]]), char, False)

    def getUR(self, flat_word):
        """Get underlying representation of word in Phones"""
        center = [self.getPhoneUR(char) for char in flat_word.decode("utf-8")]
        ends = [Phone(copy(self.grammar.phones[self.grammar.phone_char_mappings["#"]]), "#", False)]*PADDING*2
        ends[PADDING:PADDING] = center
        return ends

    def segs_match(self, segments, sylls, piv_index, word, syll_aware, is_prefix, offsets = None):
        """try matching environment of a segment
        may be syllable-aware (syllabification) or not"""
        if is_prefix:
            potential = [phone.features for phone in word[piv_index-len(segments):]]
            potential_sylls = sylls[piv_index-len(segments):]
        else:
            potential = [phone.features for phone in word[piv_index+1:]]
            potential_sylls = sylls[piv_index+1:]
        for i,feats in enumerate(segments):
            match = False
            for seg in segments[i]:
#                if offsets:
#                    print len(segments),potential[i], seg
                if match_features(potential[i], seg) and (not syll_aware or (potential_sylls[i] < 0 and (not offsets or seg['break'] == TRUE)) or (offsets and offsets[i] + sylls[piv_index] == potential_sylls[i])):
                    match = True
            if not match:
                return False
        return True

    def clean_len(self, segment):
        """Find the length of word minus padding"""
        return len(segment) - segment.count("#")

    def syllabify(self, word):
        """Syllabify given word"""
        sylls = [-1]*len(word)
        moras = [False]*len(word)
        count = 0
        for i, phone in enumerate(word):
            if match_features(phone.features, {"syll":TRUE}):
                sylls[i] = count
                moras[i] = True
                count += 1                
        nuclei = [i for i, mora in enumerate(moras) if mora == True]
        # find onsets
        for nucleus in nuclei:
            matched = ''
            for onset in self.grammar.syllables["onsets"]:
                if self.segs_match([[self.grammar.phones[phone]] for phone in onset],sylls,nucleus,word,True,True):
                    if self.clean_len(onset) > self.clean_len(matched):
                        matched = onset
            for i in range(nucleus-self.clean_len(matched),nucleus):
                sylls[i] = sylls[nucleus]
        # find codas
        for nucleus in nuclei:
            matched = ''
            for coda in self.grammar.syllables["codas"]:
                if self.segs_match([[self.grammar.phones[phone]] for phone in coda],sylls,nucleus,word,True,False):
                    if self.clean_len(coda) > self.clean_len(matched):
                        matched = coda
            for i in range(nucleus+1,nucleus+self.clean_len(matched)+1):
                moras[i] = True
                sylls[i] = sylls[nucleus]
        # apply findings
        for i, phone in enumerate(word):
            phone.syll = sylls[i]
            phone.mora = moras[i]
        return word

    def match_env(self, rule, word, index):
        """given location of a matching phone  and a rule, check if the phone is in the environment"""
        if not rule.has_env():
            return True
        sylls = [phone.syll for phone in word]
        pre_index = index
        post_index = index
        if [None] in rule.seg_match:
            pre_index += 1
#            post_index -= 1
        if not self.segs_match(rule.pre_env,sylls,pre_index,word,rule.pre_syll_aware,True,offsets=rule.pre_env_sylls):
            return False
        if not rule.post_env:            
            return True
        if self.segs_match(rule.post_env,sylls,post_index,word,rule.post_syll_aware,False,offsets=rule.post_env_sylls):
            return True
        return False
    
    def match_rule_seg(self, rule, seg):
        """determine if this phone matches the rule"""
        if [None] in rule.seg_match:
            return True
        for option in rule.seg_match:
            if match_features(seg.features,option):
                    return True
        return False

    def change_features(self,rule, seg): 
        """change features of matched phone"""
        if None in rule.seg_change: #mark this segment for deletion if this is a deletion rule
            seg.to_delete = True
            return
        if [None] in rule.seg_match: #mark this for insertion if this is an insertion rule
            seg.add_here = True
            return
        for feat in rule.seg_change.keys():
            if rule.seg_change[feat] != UNDEF:
                seg.features[feat] = rule.seg_change[feat]

    def apply_rule(self, rule, word):
        """Apply ordered rule to word.
        Only a few types of rules currently supported
        no deletions or insertions
        not all expressions of environments are permissible yet
        no syllable-aware rule environments"""
        changed = False
        for i, phone in enumerate(word):
            if self.match_rule_seg(rule,phone):
                if self.match_env(rule,word,i):
                    changed = True
                    self.change_features(rule,phone)
        #filter out segments meant for deletion
        word =  filter(lambda x: x.to_delete == False, word)
        #Add new phones
        for i, phone in reversed(list(enumerate(word))):
            if phone.add_here:
                phone.add_here = False
                word.insert(i+1, self.getPhoneUR(rule.seg_change_str.strip()))
        return word, changed

    def get_char_representation(self, seg):
        """Determine character representation of phone"""
        char_rep = seg.features.__str__()
        best = len(seg.features)
        for phone in self.grammar.phones.keys():
            errors = 0
            for feat in self.grammar.phones[phone].keys():
                if seg.features[feat] != self.grammar.phones[phone][feat]:
                    errors += 1
            if errors < best:
                best = errors
                char_rep = self.grammar.phone_char_mappings[phone]
        if char_rep != "#":
            return char_rep
        return ''

    def get_word_representation(self, word):
        """Output list of phones in readable format"""
        return "".join([self.get_char_representation(seg) for seg in word])

    def apply_to_inputs(self, filename):
        with open(filename, "r") as inputfile:
            URstrs = inputfile.read().split("\n")
#            URstrs = [line.strip() for line in inputfile]
        for name, rules in self.grammar.rules:
            print name.strip() + ":"
            for rule in rules:
                print "\t", rule.rule_str
        print '\n---\n---\n'
        for URstr in URstrs:
            phones = self.syllabify(self.getUR(URstr.strip()))
            lens = len(self.grammar.rules[0][0])
            print "UR".ljust(lens), " |  /"+self.get_word_representation(phones)+"/"
            for name, rules in self.grammar.rules:
                updated = False
                for rule in rules:
                    phones, updated_this_time = self.apply_rule(rule,phones)
                    updated = updated or updated_this_time
                new_phones = self.get_word_representation(phones)
                if updated:
                    print rule.rule_name, " |  ", new_phones
                else:
                    print rule.rule_name, " |  ", "-"
                phones = self.syllabify(phones)
            print "SR".ljust(lens), " |  ["+self.get_word_representation(phones)+"]"
            print '\n---\n'

