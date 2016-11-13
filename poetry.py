import sublime
import sublime_plugin

import os
import sys
sys.path.append('/home/chris/.config/sublime-text-3/Packages/poetry')
import re

import pronouncing as p
enabled = True

class PoetryCommand(sublime_plugin.EventListener):
	def on_modified_async(self, view):
		global enabled
		view.erase_regions("errors")
		if not enabled:
			return
		text = view.substr(sublime.Region(0, view.size())).lower()
		text = re.sub(r"[^a-zA-Z\s\n]", "", text)

		lines = [ line.rstrip().split() for line in text.split('\n') ]
		lines_phonemes = [ [ p.phones_for_word(word)[0] for word in line ] for line in lines]
		lines_syllables = [ [ p.syllable_count(phonemes) for phonemes in line_phonemes ] for line_phonemes in lines_phonemes ]
		syllables = [ sum(line_syllables) for line_syllables in lines_syllables ]

		haiku = [5, 7, 5]
		poem_standard = haiku

		bad_lines = [ i for i in range(len(lines)) if i > len(poem_standard) or poem_standard[i] != syllables[i] ]

		regions = [ view.line(view.text_point(i, 0)) for i in bad_lines ]

		view.add_regions("errors", regions, "squiggly", "", sublime.DRAW_SQUIGGLY_UNDERLINE|sublime.DRAW_NO_FILL|sublime.DRAW_NO_OUTLINE)

class DisableCommand(sublime_plugin.TextCommand):
	def run(self, edit):
		global enabled
		enabled = False

class EnableCommand(sublime_plugin.TextCommand):
	def run(self, edit):
		global enabled
		enabled = True