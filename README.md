OrderedRules
============

Apply ordered rule phonology

Class Global grammar contains static information on language's grammar
Class Phone contains dynamic information for a given segment in word
Class Rule contains static representation of an ordered rule
Class Executor carries out ordered rule transformation on input


Input file:

Sections may be in any order

  !FEATURE //must include ...: break
    (feature_name: feature_abbreviation)+

  !PHONEMES //phonemes and surface phones, for display purposes
    char_representation single_char_representation(optional): (±feature_abbreviation )*
  
  !ABBREVIATIONS //must include #: +break, abbreviations like C,V...
    char_representation: (±feature_abbreviation )*
  
  !SYLLABIFICATION
    #?char_representation+#?
    
  !RULES
  .+ > .+ (/ (.+)?_(.+)?)
  
  
  TODO:
    * refactoring
    * syllable boundary-aware rules
    * stress patterns
    * two-level rule representation
