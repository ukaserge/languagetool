#!/usr/bin/python
# Test cases for Rule.py
# (c) 2002,2003 Daniel Naber <daniel.naber@t-online.de>
#$rcs = ' $Id: RulesTest.py,v 1.5 2003-06-21 19:21:47 dnaber Exp $ ' ;

import unittest
import Rules

class RuleTestCase(unittest.TestCase):

    def setUp(self):
		self.rule = Rules.PatternRule(None)
		self.rule.setVars("TEST1", '"word" (VB|TST)', "Test message.", 0, \
			"Good example.", "Bad example.", 0, 5, "en")
		# negation:
		self.rule2 = Rules.PatternRule(None)
		self.rule2.setVars("TEST1", '"word" ^(VB|TST)', "Test message.", 0, \
			"Good example.", "Bad example.", 0, 5, "en")
		# negation at the beginning:
		self.rule3 = Rules.PatternRule(None)
		self.rule3.setVars("TEST1", '^"word" (VB|TST)', "Test message.", 0, \
			"Good example.", "Bad example.", 0, 5, "en")
		return

    def testConstructor(self):
		assert(self.rule.rule_id == "TEST1")
		assert(len(self.rule.tokens) == 2)
		return

    def testSentenceLengthRule(self):
		r = Rules.SentenceLengthRule()
		r.setMaxLength(3)

		# just below the limit:
		warnings = r.match([('x','x','T'),('x','x','T'),('x','x','T')])
		assert(len(warnings) == 0)

		# just on the limit:
		warnings = r.match([('x','x','T'),('x','x','T'),('x','x','T'),('x','x','T')])
		assert(len(warnings) == 1)
		assert( str(warnings[0]).startswith('<error from="3" to="4">'))
		r.setMaxLength(60)
		warnings = r.match([('x','x','T'),('x','x','T'),('x','x','T'),('x','x','T')])
		assert(len(warnings) == 0)
		r.setMaxLength(3)

		# whitespace is okay:
		warnings = r.match([('  ',None,None),('x','x','T'),('x','x','T'),('x','x','T')])
		assert(len(warnings) == 0)

		# much longer than the limit:
		warnings = r.match([('x','x','T'),('x','x','T'),('x','x','T'),('x','x','T'),\
			('x','x','T'),('x','x','T'),('x','x','T')])
		assert(len(warnings) == 1)

		return

    def testPatternRuleMatch(self):

		# rule 1:
		
		res_list = self.rule.match([('word', 'word', 'XX'),(' ', None, None),('bla', 'bla', 'VB')], 0)
		self.assertEqual(len(res_list), 1)
		self.assertEqual(str(res_list[0]), '<error from="0" to="4">Test message.</error>')

		res_list = self.rule.match([('no', 'no', 'XX'),('foo', 'foo', 'VB')], 0)
		assert(len(res_list) == 0)

		res_list = self.rule.match([], 0)
		assert(len(res_list) == 0)

		res_list = self.rule.match([('word', 'word', 'XX')], 0)
		assert(len(res_list) == 0)
		
		# rule 2:
		
		res_list = self.rule2.match([('word', 'word', 'XX'),('', None, None),('xxx', 'xxx', 'VBX')], 0)
		assert(len(res_list) == 1)

		# rule 3:
		
		res_list = self.rule3.match([('foo', 'foo', 'XX'),(' ', None, None),('xxx', 'xxx', 'VB')], 0)
		assert(len(res_list) == 1)
		return

class TokenTestCase(unittest.TestCase):

    def testNegation(self):

		rule = Rules.Token("^(NN)")
		self.assertEqual(rule.token, "(NN)")
		assert(rule.negation)

		rule = Rules.Token('^"word"')
		self.assertEqual(rule.token, "word")
		assert(rule.negation)
		return

    def testNonNegation(self):

		rule = Rules.Token('NN')
		self.assertEqual(rule.token, "NN")
		assert(not rule.negation)

		rule = Rules.Token('"word"')
		self.assertEqual(rule.token, "word")
		assert(not rule.negation)
		return

		
if __name__ == "__main__":
    unittest.main()
