# Class for Grammar and Style Rules
# (c) 2002,2003 Daniel Naber <daniel.naber@t-online.de>
#$rcs = ' $Id: Rules.py,v 1.6 2003-06-21 19:21:47 dnaber Exp $ ' ;
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or (at
# your option) any later version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307
# USA

import Tools

import copy
import os
import re
import sys
import xml.dom.minidom

class Rules:
	"""All known style and grammar error rules (from XML and from python code)."""

	rules_grammar_file = "rules/grammar.xml"
	
	def __init__(self, max_sentence_length, grammar_rules):
		self.rules = []
		length_rule = SentenceLengthRule()
		if max_sentence_length != None:
			length_rule.setMaxLength(max_sentence_length)
		self.rules.append(length_rule)
		# minidom expects the DTD in the current directory, not in the
		# documents directory, so we have to chdir to 'rules':
		dir_temp = os.getcwd()
		os.chdir(os.path.dirname(self.rules_grammar_file))
		doc = xml.dom.minidom.parse(os.path.basename(self.rules_grammar_file))
		os.chdir(dir_temp)
		rule_nodes = doc.getElementsByTagName("rule")
		for rule_node in rule_nodes:
			rule = PatternRule(rule_node)
			if grammar_rules == None or rule.rule_id in grammar_rules:
				self.rules.append(rule)
		return

class Rule:
	"""Style or grammar rule - quasi virtual class."""
	
	def __init__(self, rule_id, message, false_positives, language):
		self.rule_id = rule_id
		self.message = message
		self.false_positives = false_positives	# percent of sentences that are wrongly tagged as wrong
		self.language = language	# two letter code like "en" or None (= relevant for alle languages)
		return

	def match(self):
		# do nothing (quasi virtual method)
		return

class SentenceLengthRule(Rule):
	"""Check if a sentence is 'too long'. Use setMaxLength() to set the
	maximum length that's still okay. Limit 0 means no limit."""

	max_length = 30
	
	def __init__(self):
		Rule.__init__(self, "SENTENCE_LENGTH", "This sentence is too long.", 0, None)
		return

	def setMaxLength(self, max_length):
		self.max_length = int(max_length)
		return
		
	def match(self, tagged_words, position_fix=0):
		"""Check if a sentence is too long. Put the warning on the first word
		above the limit. Assumes that tagged_words is exactly one sentence."""
		if self.max_length == 0:		# 0 = no limit
			return []
		matches = []
		text_length = 0
		count = 0
		too_long = 0
		too_long_start = 0
		too_long_end = 0
		for (org_word, tagged_word, tagged_tag) in tagged_words:
			text_length = text_length + len(org_word)
			if not tagged_tag or not tagged_word:
				# don't count whitespace etc
				continue
			count = count + 1
			if count > self.max_length and not too_long:
				too_long = 1
				too_long_start = text_length-len(org_word)
				too_long_end = text_length
		if too_long:
			matches.append(RuleMatch("MAX_LEN", too_long_start,
				too_long_end, self.max_length, self.max_length+1,
				"This sentence is %d words long, which exceeds the "
				"configured limit of %d words." % (count, self.max_length)))
		#print "Count=%d (max=%d)" % (count, self.max_length)
		return matches

class PatternRule(Rule):
	"""A rule that can be formalised in the XML configuration file."""
	
	def __init__(self, rule_node):
		"""Parse an XML rule node and init the object with its variables."""
		if rule_node == None:
			# for the test cases. They use setVars().
			return
		self.rule_id = rule_node.getAttribute("id")
		self.pattern = rule_node.getElementsByTagName("pattern")[0].childNodes[0].data
		token_strings = re.split("\s+", self.pattern)
		self.tokens = []
		for token_string in token_strings:
			token = Token(token_string)
			self.tokens.append(token)
		self.language = rule_node.getElementsByTagName("pattern")[0].getAttribute("lang")
		self.case_sensitive = 0
		if rule_node.getElementsByTagName("pattern")[0].getAttribute("case_sensitive") == 'yes':
			#print "*** %s" % rule_node.getElementsByTagName("pattern")[0].getAttribute("case_sensitive")
			self.case_sensitive = 1
		if rule_node.getElementsByTagName("message"):
			self.message = Tools.Tools.getXML(rule_node.getElementsByTagName("message")[0])
		else:
			self.message = Tools.Tools.getXML(rule_node.parentNode.getElementsByTagName("message")[0])
		self.marker_position = int(rule_node.getElementsByTagName("marker")[0].childNodes[0].data)
		example_nodes = rule_node.getElementsByTagName("example")
		self.example_good = ""
		self.example_bad = ""
		for example_node in example_nodes:
			# TODO?: only one good and one bad example currently supported:
			if example_node.getAttribute("type") == 'correct':
				self.example_good = Tools.Tools.getXML(example_node.childNodes[0])
			else:
				self.example_bad = Tools.Tools.getXML(example_node.childNodes[0])
		self.false_positives = rule_node.getElementsByTagName("error_rate")[0].childNodes[0].data
		return

	def setVars(self, rule_id, pattern, message, marker_position, \
			example_good, example_bad, case_sensitive, false_positives, language):
		"""Manually init the pattern rule -- for test cases only."""
		self.rule_id = rule_id
		self.message = message
		self.false_positives = false_positives
		self.language = language
		self.marker_position = marker_position
		self.example_good = example_good
		self.example_bad = example_bad
		self.case_sensitive = case_sensitive
		self.tokens = []
		token_strings = re.split("\s+", pattern)
		for token_string in token_strings:
			token = Token(token_string)
			self.tokens.append(token)
		return
		
	def match(self, tagged_words, position_fix):
		"""Check if there are rules that match the tagged_words. Returns a list
		of RuleMatch objects."""
		matches = []
		ct = 0
		tagged_words_copy = tagged_words		# no copy, just a refernce
		for word_tag_tuple in tagged_words_copy:
			#print word_tag_tuple
			i = ct
			p = 0
			expected_token = None		# expected token if the pattern matches
			found = None
			match = 1
			first_match = ct	
			#print "<br>"
			#print "%s<br>" % str(word_tag_tuple)
			while match:
				try:
					if not tagged_words_copy[i][1] and \
						tagged_words_copy[i][2] != 'SENT_START' and \
						tagged_words_copy[i][2] != 'SENT_END':
						# here's just whitespace or other un-taggable crap:
						i = i + 1
						ct = ct + 1
						#print "CONT"
						continue
				except IndexError:
					# end of tagged words
					break
				try:
					expected_token = self.tokens[p]
				except IndexError:
					# pattern isn't that long
					#print >> sys.stderr, "*** IndexError"
					break
				if tagged_words_copy[i][2] == 'SENT_START':
					found = 'SENT_START'
				elif tagged_words_copy[i][2] == 'SENT_END':
					found = 'SENT_END'
				elif expected_token.is_word:
					# look at the real word:
					try:
						found = tagged_words_copy[i][1]
						#print "F=%s" % found
					except:
						# text isn't that long
						#print >> sys.stderr, "*** IndexError 2"
						break
				else:
					# look at the word's POS tag:
					try:
						found = tagged_words_copy[i][2]
					except:
						#print >> sys.stderr, "*** IndexError 3"
						# text ends here
						break
				if not found:
					#print >> sys.stderr, "*** 'found' undefined (i=%d, %s/%s)" % (i, tagged_words_copy[i][1], tagged_words_copy[i][2])
					break
				#print "exp: %s, found: %s<br>" % (expected_token, found)
				case_switch = re.IGNORECASE
				if self.case_sensitive:
					case_switch = 0
				if expected_token.negation:
					#print " NEG "
					match = re.compile(expected_token.token+"$", case_switch).match(found)
					if not match:
						match = 1
					else:
						match = None
				else:
					match = re.compile(expected_token.token+"$", case_switch).match(found)
					#if match:
					#	print "***"
					# TODO (optimization): test equality for simply cases?:
					#if self.case_sensitive:
					#	match = (expected_token.token == found)
					#else:
					#	match = (expected_token.token.lower() == found.lower())
					#if match:
					#	print "'%s'--'%s' (%s)" % (expected_token.token, found, match)
				i = i + 1
				p = p + 1
				#print "re.compile('%s').match('%s')" % (expected_token, found)
				#print "%d neg=%s" % (p, expected_token.negation)
				#if match: print "MATCH"
				#else: print "NOMATCH"
			if match and p == len(self.tokens):
				ct_tmp = 0
				list_match_from = 0
				list_match_to = 0
				from_pos = 0
				to_pos = 0
				#print "# %d" % first_match
				#print str(tagged_words_copy)+"<br>"
				for tagged_word in tagged_words_copy:
					#print "%s [fm=%d, marker=%d, ct=%d]<br>" % (str(tagged_word), first_match, self.marker_position, ct_tmp)
					# TODO: break
					# fixme: not correct at end of sentence (e.g. "...don't.") etc.??
					#print "####"+str(tagged_word)
					if ct_tmp < first_match+self.marker_position:
						#print "FM: "+tagged_word[0]+"<br>"
						from_pos = from_pos + len(tagged_word[0])
						list_match_from = ct_tmp+1
					if ct_tmp < ct+self.marker_position:
						#print "LM: *"+tagged_word[0]+"<br>"
						##fixme: problem at end...
						#to_pos = to_pos + len(tagged_word[0]) + len(tagged_words_copy[ct_tmp][0])
						to_pos = to_pos + len(tagged_word[0])
						list_match_to = ct_tmp+1
					ct_tmp = ct_tmp + 1
				#print "#####MATCH at first_match=%d p=%d ct=%d i=%d"%(first_match,p,ct,i)
				match = RuleMatch(self.rule_id, \
					from_pos+position_fix, \
					to_pos+position_fix, \
					list_match_from, list_match_to, self.message)
				matches.append(match)
			ct = ct + 1		
		return matches
		
class RuleMatch:
	"""A matching rule, i.e. an error or a warning and from/to positions."""
	
	def __init__(self, rule_id, from_pos, to_pos, list_pos_from, list_pos_to, message):
		self.id = rule_id
		self.from_pos = from_pos
		self.to_pos = to_pos
		self.list_pos_from = list_pos_from
		self.list_pos_to = list_pos_to
		self.message = message
		return

	def __str__(self):
		strng = self.toXML().strip() 
		return strng

	def toXML(self):
		strng = '<error from="%d" to="%d">%s</error>' % (self.from_pos, self.to_pos, self.message)
		return strng

	def __cmp__(self, b):
		if self.from_pos > b.from_pos:
			return 1
		elif self.from_pos < b.from_pos:
			return -1
		else:
			return 0

class Token:
	"""A word or tag token, negated or not. Examples:
	"^(has|will)",
	"he",
	(VB|VBP)
	"""
	
	def __init__(self, token):
		self.token = token
		self.negation = 0
		self.is_word = 0
		self.is_tag = 0
		if self.token.startswith('^'):
			self.token = token[1:len(token)]	# remove '^'
			self.negation = 1
		if self.token.startswith('"'):
			self.is_word = 1
			if not self.token.endswith('"'):
				print >> sys.stderr, "*** Warning: token '%s' starts with quote but doesn't\
					end with quote!" % token
			self.token = self.token[1:(len(self.token)-1)]	# remove quotes
		else:
			self.is_tag = 1
		return

	def __str__(self):
		"""Debugging only"""
		strng = self.token 
		if self.negation:
			strng = "^%s" % strng
		if self.is_word:
			strng = '"%s"' % strng
		return strng
