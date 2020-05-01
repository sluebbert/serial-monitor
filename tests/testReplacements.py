import unittest
import re
import importlib
serialMonitor = importlib.import_module("serial-monitor", package='serial_monitor')

clearFormat = '\033[0m'

class TestTextReplacements(unittest.TestCase):

	def test_simplePrefixAndSuffix(self):

		regexes = [
			{ "re": re.compile("hello", re.I), "prefix": "before", "suffix": "after", "continueOnMatch": True }
		]

		inputText = "hello"
		outputText = serialMonitor.handleFormatting(inputText, regexes)
		self.assertEqual("beforehelloafter" + clearFormat, outputText)

	def test_simpleSingleFormattedPrefix(self):

		regexes = [
			{ "re": re.compile("hello", re.I), "prefix": "\033[38;5;99m", "suffix": "", "continueOnMatch": True }
		]

		inputText = "hello"
		outputText = serialMonitor.handleFormatting(inputText, regexes)
		self.assertEqual("\033[38;5;99mhello" + clearFormat, outputText)

	def test_multipleMatchesSingleRegex(self):

		regexes = [
			{ "re": re.compile("hello", re.I), "prefix": "\033[38;5;99m", "suffix": "", "continueOnMatch": True }
		]

		inputText = "hello here and hello there"
		outputText = serialMonitor.handleFormatting(inputText, regexes)
		self.assertEqual("\033[38;5;99mhello%s here and \033[38;5;99mhello%s there" %(clearFormat, clearFormat), outputText)

	def test_multipleRegexStack(self):

		regexes = [
			{ "re": re.compile("hello!", re.I), "prefix": "\033[38;5;99m", "suffix": "", "continueOnMatch": True },
			{ "re": re.compile("lo", re.I), "prefix": "\033[38;5;214m", "suffix": "", "continueOnMatch": True }
		]

		inputText = "hello!"
		outputText = serialMonitor.handleFormatting(inputText, regexes)
		self.assertEqual("\033[38;5;99mhel\033[38;5;214mlo\033[38;5;99m!" + clearFormat, outputText)

	def test_multipleRegexOverride(self):

		regexes = [
			{ "re": re.compile("lo", re.I), "prefix": "\033[38;5;214m", "suffix": "", "continueOnMatch": True },
			{ "re": re.compile("hello", re.I), "prefix": "\033[38;5;99m", "suffix": "", "continueOnMatch": True }
		]

		inputText = "hello"
		outputText = serialMonitor.handleFormatting(inputText, regexes)
		self.assertEqual("\033[38;5;99mhello" + clearFormat, outputText)

	def test_multipleRegexMultipleMatches(self):

		regexes = [
			{ "re": re.compile("\d+", re.I), "prefix": "\033[38;5;214m", "suffix": "", "continueOnMatch": True },
			{ "re": re.compile("bytes", re.I), "prefix": "\033[38;5;99m", "suffix": "", "continueOnMatch": True }
		]

		inputText = "sending 25 bytes to device 2"
		outputText = serialMonitor.handleFormatting(inputText, regexes)
		self.assertEqual("sending \033[38;5;214m25%s \033[38;5;99mbytes%s to device \033[38;5;214m2%s" % (clearFormat, clearFormat, clearFormat), outputText)

	def test_multipleRegexMess(self):
		self.maxDiff = None

		regexes = [
			{ "re": re.compile("sending.*", re.I), "prefix": "\033[38;5;149m", "suffix": "", "continueOnMatch": True },
			{ "re": re.compile("\d+", re.I), "prefix": "\033[38;5;214m", "suffix": "", "continueOnMatch": True },
			{ "re": re.compile("bytes", re.I), "prefix": "\033[38;5;99m", "suffix": "", "continueOnMatch": True },
			{ "re": re.compile("o", re.I), "prefix": "\033[38;5;177m", "suffix": "", "continueOnMatch": True },
			{ "re": re.compile("oo+", re.I), "prefix": "\033[38;5;200m", "suffix": "", "continueOnMatch": True }
		]

		inputText = "sending 25 bytes to device 2, here we gooo!"
		outputText = serialMonitor.handleFormatting(inputText, regexes)
		self.assertEqual("\033[38;5;149msending \033[38;5;214m25\033[38;5;149m \033[38;5;99mbytes\033[38;5;149m t\033[38;5;177mo\033[38;5;149m device \033[38;5;214m2\033[38;5;149m, here we g\033[38;5;200mooo\033[38;5;149m!" + clearFormat, outputText)

	def test_multipleRegexMoreReplacements(self):

		regexes = [
			{ "re": re.compile("((-|\\+?)([0-9]{1,3}(,?[0-9])*)(\\.[0-9]+|\\.)?|\\.[0-9]+)", re.I), "prefix": "\033[38;5;149m", "suffix": "", "continueOnMatch": True }
		]

		inputText = "1 2 3 4"
		outputText = serialMonitor.handleFormatting(inputText, regexes)
		self.assertEqual("\033[38;5;149m1%s \033[38;5;149m2%s \033[38;5;149m3%s \033[38;5;149m4%s" % (clearFormat, clearFormat, clearFormat, clearFormat), outputText)

	def test_multipleRegexStopAfterwards(self):

		regexes = [
			{ "re": re.compile("this", re.I), "prefix": "\033[38;5;149m", "suffix": "", "continueOnMatch": False },
			{ "re": re.compile("that", re.I), "prefix": "\033[38;5;100m", "suffix": "", "continueOnMatch": True }
		]

		inputText = "this not that"
		outputText = serialMonitor.handleFormatting(inputText, regexes)
		self.assertEqual("\033[38;5;149mthis%s not that" % (clearFormat), outputText)

if __name__ == "__main__":
	unittest.main()
