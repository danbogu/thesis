import kivy
from kivy.config import Config
Config.set('graphics', 'fullscreen', '0')
from kivy.app import App
from kivy.uix.widget import Widget
from kivy.lang import Builder
from subprocess import call

Builder.load_file('Trivia_runner.kv')

class TriviaRunner(Widget):

	def triggerKss(self):
		call(["node",r"C:\Users\Dan\Desktop\scrips_folder\kss_trigger.js"])

	def triggerQuestion(self):
		call(["node",r"C:\Users\Dan\Desktop\scrips_folder\q_trigger.js"])

	def triggerScenario(self):
		call(["node",r"C:\Users\Dan\Desktop\scrips_folder\hazard_trigger.js"])


class TriviaRunnerApp(App):

	def build(self):
		return TriviaRunner()


if __name__ == "__main__":
	TriviaRunnerApp().run()

