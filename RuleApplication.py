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

class Executor():

    def __init__(self, grammar):
        self.grammar = grammar

    def getPhoneUR(self, char):
        return deepcopy(self.grammar.phones[char])

    def getUR(self, flat_word):
        center = [self.getPhoneUR(char) for char in flat_word]
        ends = [Phone(self.grammar.features,boundary=True)]*PADDING*2
        ends[PADDING:PADDING] = center
        return ends

    def match(self, segments, types, sylls, nuc_index, is_onset):
        if is_onset:
            potential = types[nuc_index-len(segments):]
            potential_sylls = sylls[nuc_index-len(segments):]
        else:
            potential = types[nuc_index+1:]
            potential_sylls = sylls[nuc_index+1:]
        for i, seg in enumerate(segments):
            if seg not in potential[i] or potential_sylls[i] >= 0:
                return False
        return True

    def clean_len(self, segment):
        return len(segment) - segment.count("#")

    def syllabify(self, word):
        types = [phone.abbrevs for phone in word]
        sylls = [-1]*len(types)
        moras = [False]*len(types)
        count = 0
        # find nuclei
        for i, type_set in enumerate(types):
            if(self.grammar.rev_abbrevs["+syll"] in type_set):
                sylls[i] = count
                moras[i] = True
                count += 1
        nuclei = [i for i, mora in enumerate(moras) if mora == True]
        # find onsets
        for nucleus in nuclei:
            matched = ''
            for onset in self.grammar.syllables["onsets"]:
                if self.match(onset,types,sylls,nucleus,is_onset=True):
                    if self.clean_len(onset) > self.clean_len(matched):
                        matched = onset
            for i in range(nucleus-self.clean_len(matched),nucleus):
                sylls[i] = sylls[nucleus]
        # find codas
        for nucleus in nuclei:
            matched = ''
            for coda in self.grammar.syllables["codas"]:
                if self.match(coda,types,sylls,nucleus,is_onset=False):
                    if self.clean_len(coda) > self.clean_len(matched):
                        matched = coda
            for i in range(nucleus+1,nucleus+self.clean_len(matched)+1):
                moras[i] = True
                sylls[i] = sylls[nucleus]
        # apply findings
        for i, phone in enumerate(word):
            phone.syll = sylls[i]
            phone.mora = moras[i]
            print phone.syll, phone.mora
        print sylls
        print moras
        
        return
    
    def match_rule_seg(self, rule, seg):
        for feat in rule.seg_match.keys():
            if seg.features[feat] != rule.seg_match[feat] and rule.seg_match[feat] != UNDEF:
#                print feat, seg.features[feat], self.seg_match[feat]
                return False
        return True

    def apply_rule(self, rule, word):
        for phone in word:
            print self.match_rule_seg(rule,phone)

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
        self.abbrevs = self.map_abbrevs(sec_filter(full, "ABBREV"))
        self.rev_abbrevs = self.reverse_abbrevs()
        self.phones = self.map_phones(sec_filter(full, "PHONEME"))
        self.syllables = self.read_syllables(sec_filter(full, "SYLL"))
        self.rules = self.parse_rules(sec_filter(full, "RULE"))
        return full

    def map_abbrevs(self, abbrev_sec):
        return {line.split(":")[0].strip() : line.split(":")[1].strip() for line in 
                filter(lambda x:
                           x and "ABBREV" not in x, abbrev_sec.split("\n"))}

    def reverse_abbrevs(self):
        revs = {}
        for key in self.abbrevs.keys():
            revs[self.abbrevs[key]] = key
        return revs

    def read_features(self, feature_sec):
        return [line.split(":")[1].strip() for line in 
                filter(lambda x:
                           x and "FEATURE" not in x, feature_sec.split("\n"))]

    def map_phones(self, phone_sec):
        phones = [Phone(self.features, line.split(":"), rev_abbrevs=self.rev_abbrevs) for line in phone_sec.decode("utf-8").split("\n") if ":" in line]
        return {phone.name : phone for phone in phones}

    def read_syllables(self, syll_sec):
        syllables = set([line.strip() for line in 
                filter(lambda x:
                           x and "SYLL" not in x, syll_sec.split("\n"))])
        onsets = set([syll.split(self.rev_abbrevs["+syll"])[0] for syll in syllables])
        codas = set([syll.split(self.rev_abbrevs["+syll"])[1] for syll in syllables])
        nuclei = set(self.rev_abbrevs["+syll"])
        return {'syllables':syllables,'onsets':onsets,'codas':codas}

    def parse_rules(self, rule_sec):
        rules = set([line.strip() for line in 
                filter(lambda x:
                           x and "RULE" not in x, rule_sec.split("\n"))])
        return [Rule(rule,self.features,self.abbrevs) for rule in rules]


class Rule(object):

    def __init__(self, rule_str, features, abbrevs):
        self.rule_str = rule_str
        self.features = features
        self.abbrevs = abbrevs
        print rule_str
        rule_list = re.split('[/>_]',rule_str)
        print rule_list
        self.seg_match = self.get_seg_match(rule_list[0].strip())
        self.seg_change = rule_list[1]
        self.pre_env = rule_list[2]
        self.post_env = rule_list[3]

    def get_seg_match(self, match_str):
        self.seg_match = match_str.strip()
        if self.seg_match in self.abbrevs.keys():
            self.seg_match = self.abbrevs[self.seg_match]
        return get_features(self.features, re.sub("[\[|\]]","",self.seg_match))
        

class Phone(object):

    def __init__(self, features=None, phone=None, boundary=False, rev_abbrevs=None):
        if not boundary:
            self.syll = -1
            self.mora = False
            self.mapped = None
            self.name = phone[0]
            self.abbrev_list = rev_abbrevs
            if ' ' in phone[0]:
                self.mapped = phone[0].split(" ")[1]
                self.name = phone[0].split(" ")[0]
            self.abbrevs = set([self.abbrev_list[feat] for feat in self.abbrev_list if feat in phone[1]])
            self.features = get_features(features, phone[1])
        else:
            self.syll = -1
            self.mora = False
            self.mapped = '#'
            self.name = '#'
            self.abbrev_list = {}
            self.features = get_features(features, None)
            self.abbrevs = ['#']


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

for phone in phones:
    print phone.mora, phone.abbrevs

for rule in grammar.grammar.rules:
    print rule.rule_str
    print grammar.apply_rule(rule,phones)
