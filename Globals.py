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
