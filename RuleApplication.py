# -*- coding: utf-8 -*-
import codecs
from copy import deepcopy
import re

TRUE = 1
FALSE = 0
UNDEF = 2

PADDING = 2

def get_features(feature_list, these_feature):
    features = {}
    def feat_filter(feature, this):
        try:
            mapper = lambda x, feat: filter(lambda y: feat in y, x.split(" "))[0]
            val = mapper(this, feature)
            if '+' in val:
                return TRUE
            return FALSE
        except:
            return UNDEF
    for feat in feature_list:
        features[feat] = feat_filter(feat, these_feature)
    return features

def match_features(phone_feats, other_feats):
    for feat in other_feats.keys():
        if phone_feats[feat] != other_feats[feat] and other_feats[feat] != UNDEF:
            return False
    return True
           

class Executor():

    def __init__(self, grammar):
        self.grammar = grammar

    def getPhoneUR(self, char):        
        return Phone(self.grammar.phones[self.grammar.phone_char_mappings[char]], char, False)

    def getUR(self, flat_word):
        center = [self.getPhoneUR(char) for char in flat_word]
        ends = [Phone(self.grammar.features,"#",boundary=True)]*PADDING*2
#        ends = [Phone(self.grammar.abbrevs,self.grammar.features,boundary=True)]*PADDING*2
        ends[PADDING:PADDING] = center
        return ends

    def syll_match(self, segments, types, sylls, piv_index, is_prefix, word):
        potential = [phone.features for phone in word[piv_index-len(segments):]]
        print segments
        for i,feats in enumerate(segments):
            print i, len(feats), len(segments)
            print grammar.grammar.abbrevs
            print [grammar.grammar.abbrevs[seg] for seg in segments[i]]
            print match_features(feats,[grammar.grammar.abbrevs[seg] for seg in segments[i]])
        if is_prefix:
            potential = types[piv_index-len(segments):]
            potential_sylls = sylls[piv_index-len(segments):]
        else:
            potential = types[piv_index+1:]
            potential_sylls = sylls[piv_index+1:]
        for i, seg in enumerate(segments):
            if seg not in potential[i] or potential_sylls[i] >= 0:
                return False
        return True

    def clean_len(self, segment):
        return len(segment) - segment.count("#")

    def syllabify(self, word):
        sylls = [-1]*len(word)
        moras = [False]*len(word)
        for phone in word:
            print phone.name, phone.features
#        types = [phone.abbrevs for phone in word]
#        sylls = [-1]*len(types)
#        moras = [False]*len(types)
        count = 0
        # find nuclei
        print word
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
                if self.syll_match(onset,types,sylls,nucleus,True,word):
                    if self.clean_len(onset) > self.clean_len(matched):
                        matched = onset
            for i in range(nucleus-self.clean_len(matched),nucleus):
                sylls[i] = sylls[nucleus]
        # find codas
        for nucleus in nuclei:
            matched = ''
            for coda in self.grammar.syllables["codas"]:
                if self.syll_match(coda,types,sylls,nucleus,False,word):
                    if self.clean_len(coda) > self.clean_len(matched):
                        matched = coda
            for i in range(nucleus+1,nucleus+self.clean_len(matched)+1):
                moras[i] = True
                sylls[i] = sylls[nucleus]
        # apply findings
        for i, phone in enumerate(word):
            phone.syll = sylls[i]
            phone.mora = moras[i]
        print sylls
        print moras
        
        return

    def match_env(self, rule, word, index):
        types = [phone.abbrevs for phone in word]
        sylls = [-1]*len(types)
        moras = [False]*len(types)

#        if not self.syll_match(rule.prev_index,types,sylls,word,is_onset=True):
#            return False
#        if not self.syll_match(rule.prev_index,types,sylls,word,is_onset=True):
#            return False
        return True
    
    def match_rule_seg(self, rule, seg):
        for feat in rule.seg_match.keys():
            if not match_features(seg.features,rule.seg_match):
                return False
        return True

    def change_features(self,rule, seg): 
        for feat in rule.seg_change.keys():
            if rule.seg_change[feat] != UNDEF:
                seg.features[feat] = rule.seg_change[feat]

    def apply_rule(self, rule, word):
        for i, phone in enumerate(word):
            if self.match_rule_seg(rule,phone):
                if self.match_env(rule,word,i):
                    self.change_features(rule,phone)

class GlobalGrammar():

    def __init__(self, filename):
        self.features = None
        self.phones = None
        self.syllables = None
        self.rules = None
        self.abbrevs = None
        self.sections = self.section_file(filename)


    def section_file(self, filename):
        f = open(filename, "r")
        in_feat = True
        full = f.read().split("!")
        sec_filter = lambda x, sec: filter(lambda y: sec in y, x)[0]
        self.features = self.read_features(sec_filter(full, "FEATURE"))
#        self.abbrevs = self.map_abbrevs(sec_filter(full, "ABBREV"),sec_filter(full, "PHONEME"))
#        self.rev_abbrevs = self.reverse_abbrevs()
        self.phones = self.map_phones(sec_filter(full, "PHONEME"),sec_filter(full, "ABBREV"))
        self.phone_char_mappings = self.map_phone_chars(sec_filter(full, "PHONEME"))
        self.syllables = self.read_syllables(sec_filter(full, "SYLL"))
        self.rules = self.parse_rules(sec_filter(full, "RULE"))
        return full

#    def map_abbrevs(self, abbrev_sec, feature_sec):
#        combined = abbrev_sec + feature_sec
#        return {line.split(":")[0].split()[-1].strip() : get_features(line.split(":")[1].strip() for line in 
#                filter(lambda x:
#                           x and "ABBREV" not in x and "PHONE" not in x, combined.split("\n"))}

    def reverse_abbrevs(self):
        revs = {}
        for key in self.abbrevs.keys():
            revs[self.abbrevs[key]] = key
        return revs

    def read_features(self, feature_sec):
        return [line.split(":")[1].strip() for line in 
                filter(lambda x:
                           x and "FEATURE" not in x, feature_sec.split("\n"))]

    def map_phones(self, phone_sec, abbrev_sec):
#        phones = [Phone(self.abbrevs, self.features, line.split(":"), rev_abbrevs=self.rev_abbrevs) for line in phone_sec.decode("utf-8").split("\n") if ":" in line]
#        return {phone.name : phone for phone in phones}
        combined = phone_sec + abbrev_sec
        return {line.split(":")[0].split()[-1].strip() : get_features(self.features,line.split(":")[1].strip()) for line in 
                filter(lambda x:
                           x and "ABBREV" not in x and "PHONE" not in x, combined.split("\n"))}        

    def map_phone_chars(self, phone_sec):
        return {line.split(":")[0].split()[0].strip() : line.split(":")[0].split()[-1].strip() for line in 
                filter(lambda x:
                            x and "PHONE" not in x, phone_sec.split("\n"))}        

    def read_syllables(self, syll_sec):
        syllables = set([line.strip() for line in 
                filter(lambda x:
                           x and "SYLL" not in x, syll_sec.split("\n"))])

        nuclei = set([phone for phone in self.phones.keys() if self.phones[phone]["syll"] == TRUE])
        onsets = set([re.split("["+"".join(nuclei)+"]",syll)[0] for syll in syllables])
        codas = set([re.split("["+"".join(nuclei)+"]",syll)[1] for syll in syllables])
        return {'syllables':syllables,'onsets':onsets,'codas':codas}

    def parse_rules(self, rule_sec):
        rules = set([line.strip() for line in 
                filter(lambda x:
                           x and "RULE" not in x, rule_sec.split("\n"))])
        return [Rule(rule,self.features,self.phones) for rule in rules]


class Rule(object):

    def __init__(self, rule_str, features, abbrevs):
        self.rule_str = rule_str
        self.features = features
        print rule_str
        rule_list = re.split('[/>_]',rule_str)
        print rule_list
        self.seg_match = self.get_seg_feats(rule_list[0].strip())
        self.seg_change = self.get_seg_feats(rule_list[1].strip())
        self.pre_env = rule_list[2] if len(rule_list) > 2 else None
        self.post_env = rule_list[3] if len(rule_list) > 2 else None

    def get_seg_feats(self, match_str):
        return get_features(self.features, re.sub("[\[|\]]","",match_str.strip()))
        
    def has_env(self):
        return not (self.pre_env and self.post_env)

class Phone(object):

    def __init__(self, features=None, phone=None, boundary=False):
        if not boundary:
            self.syll = -1
            self.mora = False
            self.mapped = phone
            self.name = phone
#            self.abbrev_list = abbrevs
#            if ' ' in phone[0]:
#                self.mapped = phone[0].split(" ")[1]
#                self.name = phone[0].split(" ")[0]
#            self.abbrevs = set([rev_abbrevs[feat] for feat in rev_abbrevs])
#            self.abbrevs = set([rev_abbrevs[feat] for feat in rev_abbrevs if feat in phone[1]])
#            self.abbrevs = set([self.abbrev_list[feat] for feat in self.abbrev_list if feat in phone[1]])
#            self.features = get_features(features, phone[1], self.abbrev_list)
            self.features = features
        else:
            self.syll = -1
            self.mora = False
            self.mapped = '#'
            self.name = '#'
#            self.abbrev_list = abbrevs
#            self.abbrevs = ['#']
            self.features = get_features(features, None)
#            self.abbrevs = ['#']


    def __str__(self):
        mapped = self.mapped
        if not mapped:
            mapped = ""
        title = mapped + " " 
        print self.features
        return title


grammar = Executor(GlobalGrammar(u'ulsanna_config.txt'))
phones = grammar.getUR(u'arnirn')   
grammar.syllabify(phones)

for rule in grammar.grammar.rules:
    print rule.rule_str
    print grammar.apply_rule(rule,phones)

#for phone in phones:
#    print phone.name, phone.features
