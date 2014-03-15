#!/usr/bin/python
# -*- coding: utf-8 -*-

import codecs
from copy import copy
import re
from collections import OrderedDict
from itertools import groupby
import sys

TRUE = 1
FALSE = 0
UNDEF = 2

NULL = "∅"
SYLL = "σ".decode("utf-8")


PADDING = 2

def get_features(feature_list, these_feature):
    """Translate list of features in format "+/-name1 +/-name2 into
    dictionary of features given full list of possible features"""
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
    """Determine whether two sets of features match.
    A phone is "matched" if every defined feature in the matching environment
    is matches the feature in phone"""
    for feat in other_feats.keys():
        if phone_feats[feat] != other_feats[feat] and other_feats[feat] != UNDEF:
            return False
    return True
           

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
                print seg
                if match_features(potential[i], seg) and (not syll_aware or (potential_sylls[i] < 0 and (not offsets)) or (offsets and offsets[i] + sylls[piv_index] == potential_sylls[i])):
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
            print "UR".ljust(lens), " |  ", self.get_word_representation(phones)
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
            print "SR".ljust(lens), " |  ", self.get_word_representation(phones)
            print '\n---\n'
            
                    
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
        return [(key, set(group)) for key, group in groupby(rule_list, lambda x: x.rule_name)]




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


def main(args):
    grammar = Executor(GlobalGrammar(args[0]))
    grammar.apply_to_inputs(args[1])


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise ValueError("Correct Usage: python RuleApplication.py <config file> <input file>")
    main(sys.argv[1:])

