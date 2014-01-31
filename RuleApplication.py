# -*- coding: utf-8 -*-
import codecs
from copy import copy
import re

TRUE = 1
FALSE = 0
UNDEF = 2

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
        center = [self.getPhoneUR(char) for char in flat_word]
        ends = [Phone(self.grammar.features,"#",boundary=True)]*PADDING*2
        ends[PADDING:PADDING] = center
        return ends

    def segs_match(self, segments, sylls, piv_index, word, syll_aware, is_prefix):
        """try matching environment of a segment
        may be syllable-aware (syllabification) or not"""
        if is_prefix:
            potential = [phone.features for phone in word[piv_index-len(segments):]]
            potential_sylls = sylls[piv_index-len(segments):]
        else:
            potential = [phone.features for phone in word[piv_index+1:]]
            potential_sylls = sylls[piv_index+1:]
        for i,feats in enumerate(segments):
            for seg in segments[i]:
                if not match_features(potential[i], grammar.grammar.phones[seg]) or (syll_aware and potential_sylls[i] >= 0):
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
                if self.segs_match(onset,sylls,nucleus,word,True,True):
                    if self.clean_len(onset) > self.clean_len(matched):
                        matched = onset
            for i in range(nucleus-self.clean_len(matched),nucleus):
                sylls[i] = sylls[nucleus]
        # find codas
        for nucleus in nuclei:
            matched = ''
            for coda in self.grammar.syllables["codas"]:
                if self.segs_match(coda,sylls,nucleus,word,True,False):
                    if self.clean_len(coda) > self.clean_len(matched):
                        matched = coda
            for i in range(nucleus+1,nucleus+self.clean_len(matched)+1):
                moras[i] = True
                sylls[i] = sylls[nucleus]
        # apply findings
        for i, phone in enumerate(word):
            phone.syll = sylls[i]
            phone.mora = moras[i]
        return

    def match_env(self, rule, word, index):
        """given location of a matching phone  and a rule, check if the phone is in the environment"""
        if not rule.has_env():
            return True
        sylls = [phone.syll for phone in word]
        matched = False
        for env in rule.pre_env:
            if self.segs_match(env,sylls,index,word,False,True):
                matched = True
        if not matched:
            return False
        matched = False
        for env in rule.post_env:
            if self.segs_match(env,sylls,index,word,False,False):
                matched = True
        return matched
    
    def match_rule_seg(self, rule, seg):
        """determine if this phone matches the rule"""
        for option in rule.seg_match:
            matched = True
            for feat in option.keys():
                if not match_features(seg.features,option):
                    matched = False
                    break
            if matched == True:
                return True
        return False

    def change_features(self,rule, seg): 
        """change features of matched phone"""
        for feat in rule.seg_change.keys():
            if rule.seg_change[feat] != UNDEF:
                seg.features[feat] = rule.seg_change[feat]

    def apply_rule(self, rule, word):
        """Apply ordered rule to word.
        Only a few types of rules currently supported
        no deletions or insertions
        not all expressions of environments are permissible yet
        no syllable-aware rule environments"""
        for i, phone in enumerate(word):
            if self.match_rule_seg(rule,phone):
                if self.match_env(rule,word,i):
                    self.change_features(rule,phone)
        return word

    def get_char_representation(self, seg):
        """Determine character representation of phone"""
        char_rep = seg.features.__str__()
        for phone in self.grammar.phones.keys():
            match = True
            for feat in self.grammar.phones[phone].keys():
                if seg.features[feat] != self.grammar.phones[phone][feat]:
                    match = False
                    continue
            if match:
                char_rep = self.grammar.phone_char_mappings[phone]
        if char_rep != "#":
            return char_rep
        return ''

    def get_word_representation(self, word):
        """Output list of phones in readable format"""
        return "".join([self.get_char_representation(seg) for seg in word])
                    
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
        full = f.read().split("!")
        sec_filter = lambda x, sec: filter(lambda y: sec in y, x)[0]
        self.features = self.read_features(sec_filter(full, "FEATURE"))
        self.phones = self.map_phones(sec_filter(full, "PHONEME"),sec_filter(full, "ABBREV"))
        self.phone_char_mappings = self.map_phone_chars(sec_filter(full, "PHONEME"), sec_filter(full, "ABBREV"))
        self.syllables = self.read_syllables(sec_filter(full, "SYLL"))
        self.rules = self.parse_rules(sec_filter(full, "RULE"))
        for rule in self.rules:
        return full

    def read_features(self, feature_sec):
        """remove character names from list of binary features"""
        return [line.split(":")[1].strip() for line in 
                filter(lambda x:
                           x and "FEATURE" not in x, feature_sec.split("\n"))]

    def map_phones(self, phone_sec, abbrev_sec):
        """map phonemes, abbreviations, and word boundary (#) characters to dictionaries of binary feature values"""
        combined = phone_sec + abbrev_sec + "#: "
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

        rules = [line.strip() for line in 
                filter(lambda x:
                           x and "RULE" not in x, rule_sec.split("\n"))]
        return [Rule(rule,self.features,self.phones) for rule in rules]


class Rule(object):
    """Representation of ordered rule"""

    def __init__(self, rule_str, features, abbrevs):
        self.rule_str = rule_str
        self.features = features
        self.abbrevs = abbrevs
        rule_list = re.split('[/>_]',rule_str)
        self.seg_match = self.get_seg_feats(self.divide_segs(rule_list[0].strip())) # A
        self.seg_change = self.get_seg_feats([rule_list[1].strip()])[0] # B
        self.pre_env = self.divide_segs(rule_list[2].strip()) if len(rule_list) > 2 else None # C
        self.post_env = self.divide_segs(rule_list[3].strip()) if len(rule_list) > 2 else None # D

    def divide_segs(self, segs):
        return re.sub("[{}]", "", segs).split(",")

    def get_seg_feats(self, match_str):
        return [get_features(self.features, re.sub("[\[|\]]","",match.strip())) if match not in self.abbrevs else self.abbrevs[match] for match in match_str]
        
    def has_env(self):
        return (self.pre_env and self.post_env)

class Phone(object):
    """Representation of phone. Contains feature information, character representation information, and syllabification related information"""

    def __init__(self, features=None, phone=None, boundary=False):
        if not boundary:
            self.syll = -1
            self.mora = False
            self.mapped = phone
            self.name = phone
            self.features = features
        else:
            self.syll = -1
            self.mora = False
            self.mapped = '#'
            self.name = '#'
            self.features = get_features(features, None)

    def __str__(self):
        """Don't use this. Unicode mess"""
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
    print grammar.get_word_representation(phones)
    print grammar.apply_rule(rule,phones)
    print grammar.get_word_representation(phones)
#for phone in phones:
#    print phone.name, phone.features
