#from sublime import Region
import sublime
import sublime_plugin

import time
import os
import sys
sys.path.append('/home/chris/.config/sublime-text-3/Packages/poetry')
import re
from string import ascii_letters
import threading

import pronouncing as p

def processText(text):
	text = text.lower()

	def split_line(line):
		line += '.' # force last word to be added
		words = []
		word = ''
		for i, c in enumerate(list(line)):
			if c in ascii_letters:
				word += c
			elif len(word) > 0:
				words.append( (i - len(word), word) )
				word = ''
		return words

	lines = [ split_line(line.rstrip()) for line in text.split('\n') ]
	lines = [ [ (r, c, word) for c, word in line ] for r, line in enumerate(lines) ]

	def stresses(word):
		phonemes = p.phones_for_word(word)
		if len(phonemes) is 0:
			return [ None ]
		stresses = p.stresses(phonemes[0])
		if len(stresses) is 1:
			return [ None ]
		return [ int(c) > 0 for c in stresses ]

	lines = [ [ (r, c, word, stresses(word)) for r, c, word in line ] for line in lines ]

	return lines

def stressCheck(lines, template_lines, rhyme_scheme_lines, view):
	regions = []
	last_words = []
	for line, template_line in zip(lines, template_lines):
		if len(line) == 0: # empty line
			continue
		total_stresses = sum( [ len(word[3]) for word in line ] )
		if total_stresses < len(template_line):
			regions.append( ( view.line(view.text_point(line[0][0], 0)), 'tooFewSyllables' ) )
			continue
		line_index = 0
		last = None
		for r, c, word, stresses in line:
			if len(stresses) > len(template_line[line_index:]): # too many syllables
				start_point = view.text_point(r, c)
				end_point = view.text_point(r, line[-1][1] + len(line[-1][2]))
				regions.append( ( sublime.Region(start_point, end_point), 'tooManySyllables' ) ) # add rest of line
				break # don't need to process any more words
			if any( [ (stress1 != stress2 and stress1 != None and stress2 != None) for stress1, stress2 in zip(stresses, template_line[line_index:]) ] ): # a syllable doesn't match
				start_point = view.text_point(r, c)
				end_point = view.text_point(r, c + len(word))
				num_syllables = len(stresses)
				if template_line[line_index]: # should be stressed to start
					regions.append( ( sublime.Region(start_point, end_point), 'shouldBeStressed' + str(num_syllables) ) )
				else:
					regions.append( ( sublime.Region(start_point, end_point), 'shouldBeUnstressed' + str(num_syllables) ) )

			line_index += len(stresses)
			last = (r, c, word)

		# For checking for rhymes
		last_words.append(last)

	for line in lines[len(template_lines):]: # all extra lines
		if len(line) is not 0:
			regions.append( ( view.line(view.text_point(line[0][0], 0)), 'extraLine' ) )

	rhyme_map = {}
	for last, line in zip(last_words, rhyme_scheme_lines):
		if line is None:
			continue
		if line not in rhyme_map:
			rhyme_map[line] = set(p.rhymes(last[2]) + [last[2]])
		elif last[2] not in rhyme_map[line]:
			start_point = view.text_point(last[0], last[1])
			end_point = view.text_point(last[0], last[1] + len(last[2]))
			regions.append( (sublime.Region( start_point, end_point ), 'rhyme') )
	reasons = set([ reason for _, reason in regions ])
	collated_regions = [ (reason, [ region[0] for region in regions if region[1] == reason ]) for reason in reasons ]
	return collated_regions
	
def clearRegions(view):
	regionNames = [ 'tooManySyllables', 'tooFewSyllables', 'extraLine', 'rhyme', 'shouldBeStressed1', 'shouldBeStressed2', 'shouldBeStressed3', 'shouldBeStressed4', 'shouldBeStressed5',  'shouldBeUnstressed1', 'shouldBeUnstressed2', 'shouldBeUnstressed3', 'shouldBeUnstressed4', 'shouldBeUnstressed5' ]
	for regionName in regionNames:
		view.erase_regions(regionName)

flag = 0

def updateThread(view):
	stressMap = view.settings().get('poem_stress_scheme', False)
	rhymeMap = view.settings().get('poem_rhyme_scheme', False)
	if not stressMap and not rhymeMap:
		return

	global flag
	flag = (flag + 1) % 1000000
	holder = flag
	time.sleep(1)
	if flag != holder:
		return

	clearRegions(view)

	text = view.substr(sublime.Region(0, view.size()))
	text = text.rstrip()
	lines = processText(text)

	if len(stressMap) is 1:
		stressMap = [ stressMap[0] ] * len(lines)
	errorRegions = stressCheck(lines, stressMap, rhymeMap, view)

	for errorName, regions in errorRegions:
		view.add_regions(errorName, regions, 'squiggly', "", sublime.DRAW_SQUIGGLY_UNDERLINE|sublime.DRAW_NO_FILL|sublime.DRAW_NO_OUTLINE)

class PoetryCommand(sublime_plugin.EventListener):
	def on_hover(self, view, point, hover_zone):
		errorMap = [
			('shouldBeStressed1', 'This word should be stressed'),
			('shouldBeUnstressed1', 'This word should be unstressed'),
			('shouldBeStressed2', 'This word should be stressed-unstressed'),
			('shouldBeUnstressed2', 'This word should be unstressed-stressed'),
			('shouldBeStressed3', 'This word should be stressed-unstressed-stressed'),
			('shouldBeUnstressed3', 'This word should be unstressed-stressed-unstressed'),
			('shouldBeStressed4', 'This word should be stressed-unstressed-stressed-unstressed'),
			('shouldBeUnstressed4', 'This word should be unstressed-stressed-unstressed-stressed'),
			('shouldBeStressed5', 'This word should be stressed-unstressed-stressed-unstressed-stressed'),
			('shouldBeUnstressed5', 'This word should be unstressed-stressed-unstressed-stressed-unstressed'),
			('tooManySyllables', 'There are too many syllables on this line'),
			('tooFewSyllables', 'There are too few syllables on this line'),
			('rhyme', 'This word does not fit into the rhyme scheme'),
			('extraLine', 'There are too many lines in this poem') ]

		for errors, message in errorMap:
			regions = view.get_regions(errors)
			for region in regions:
				if region.contains(point):
					view.show_popup(message, sublime.HIDE_ON_MOUSE_MOVE_AWAY)


	def on_modified_async(self, view):
		threading.Thread(target = updateThread, args = (view,)).start()

class BlankVerseCommand(sublime_plugin.TextCommand):
	stress_scheme = [ [False, True, False, True, False, True, False, True, False, True] ]
	rhyme_scheme = [ None, None, None ]

	def run(self, edit):
		sublime.active_window().active_view().settings().set('poem_stress_scheme', self.stress_scheme)
		sublime.active_window().active_view().settings().set('poem_rhyme_scheme', self.rhyme_scheme)
		updateThread(sublime.active_window().active_view())

class EnglishSonnetCommand(sublime_plugin.TextCommand):
	stress_scheme = [[None] * 10 ] * 12
	rhyme_scheme = [ 0, 1, 0, 1, 2, 3, 2, 3, 4, 5, 4, 5, 6, 6 ]

	def run(self, edit):
		sublime.active_window().active_view().settings().set('poem_stress_scheme', self.stress_scheme)
		sublime.active_window().active_view().settings().set('poem_rhyme_scheme', self.rhyme_scheme)
		updateThread(sublime.active_window().active_view())

class ItalianSonnetCommand(sublime_plugin.TextCommand):
	stress_scheme = [[None] * 10 ] * 12
	rhyme_scheme = [ 0, 1, 1, 0, 0, 1, 1, 0, 2, 3, 4, 2, 3, 4 ]

	def run(self, edit):
		sublime.active_window().active_view().settings().set('poem_stress_scheme', self.stress_scheme)
		sublime.active_window().active_view().settings().set('poem_rhyme_scheme', self.rhyme_scheme)
		updateThread(sublime.active_window().active_view())

class LimerickCommand(sublime_plugin.TextCommand):
	stress_scheme = [
		[False, False, True, False, False, True, False, False, True],
		[False, False, True, False, False, True, False, False, True],
		[False, False, True, False, False, True],
		[False, False, True, False, False, True],
		[False, False, True, False, False, True, False, False, True]]
	rhyme_scheme = [ 0, 0, 1, 1, 0 ]

	def run(self, edit):
		sublime.active_window().active_view().settings().set('poem_stress_scheme', self.stress_scheme)
		sublime.active_window().active_view().settings().set('poem_rhyme_scheme', self.rhyme_scheme)
		updateThread(sublime.active_window().active_view())

class HaikuCommand(sublime_plugin.TextCommand):
	stress_scheme = [ [None] * 5, [None] * 7, [None] * 5 ]
	rhyme_scheme = [ None, None, None ]

	def run(self, edit):
		sublime.active_window().active_view().settings().set('poem_stress_scheme', self.stress_scheme)
		sublime.active_window().active_view().settings().set('poem_rhyme_scheme', self.rhyme_scheme)
		updateThread(sublime.active_window().active_view())

class PindaricOdeCommand(sublime_plugin.TextCommand):
	stress_scheme = [ [None] * 10, [None] * 10, [None] * 8, [None] * 10, [None] * 10, [None] * 8, [None] * 7, [None] * 7, [None] * 7, [None] * 7, [None] * 7, [None] * 7 ]
	rhyme_scheme = [ 0, 0, 1, 0, 0, 2, 3, 3, 4, 4, 5, 5 ]

	def run(self, edit):
		sublime.active_window().active_view().settings().set('poem_stress_scheme', self.stress_scheme)
		sublime.active_window().active_view().settings().set('poem_rhyme_scheme', self.rhyme_scheme)
		updateThread(sublime.active_window().active_view())

class DisableCommand(sublime_plugin.TextCommand):
	def run(self, edit):
		sublime.active_window().active_view().settings().set('poem_stress_scheme', False)
		clearRegions(sublime.active_window().active_view())
