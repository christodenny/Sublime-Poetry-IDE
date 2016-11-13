import sublime
import sublime_plugin

enabled = False

class PoetryCommand(sublime_plugin.EventListener):
	def on_modified_async(self, view):
		global enabled
		view.erase_regions("hello")
		if not enabled:
			return
		text = view.substr(sublime.Region(0, view.size()))
		lines = text.split("\n")
		for i in range(len(lines)):
			lines[i] = lines[i].rstrip().split(" ")
		counts = []
		for line in lines:
			counts.append(len(line))
		haiku = [5, 7, 5]
		bad_lines = []
		for i in range(len(counts)):
			if i >= len(haiku) or haiku[i] != counts[i]:
				bad_lines.append(i)
		regions = []
		for i in bad_lines:
			regions.append(view.line(view.text_point(i, 0)))
		view.add_regions("hello", regions, "squiggly", "", sublime.DRAW_SQUIGGLY_UNDERLINE|sublime.DRAW_NO_FILL|sublime.DRAW_NO_OUTLINE)

class DisableCommand(sublime_plugin.TextCommand):
	def run(self, edit):
		global enabled
		enabled = False

class EnableCommand(sublime_plugin.TextCommand):
	def run(self, edit):
		global enabled
		enabled = True