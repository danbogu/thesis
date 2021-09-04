import winsound
import json
import threading
import time
from random import randrange
import kivy
from kivy.config import Config
Config.set('graphics', 'fullscreen', '0')
from kivy.app import App
from kivy.core.window import Window
from kivy.uix.screenmanager import ScreenManager, Screen, NoTransition
from kivy.lang import Builder
from kivy.clock import Clock
from kivy.uix.popup import Popup
from kivy.uix.label import Label
from kivy.uix.image import Image
from kivy.properties import OptionProperty
import pyodbc

#Hazard popup
hazard_popup = Popup(title='',separator_height = 0, #title_align = OptionProperty(),
			content = Image(source=r"C:\Users\Dan\Desktop\warning-light.png"),
			size_hint=(0.2, 0.2), pos_hint = {'x':0.4, 'y':0.8})

degraded_fitness_popup = Popup(title='Degraded Fitness',separator_height = 0, title_align = 'center', title_size = '12',
			content = Image(source=r"C:\Users\Dan\Desktop\degraded_fitness.png"),
			size_hint=(0.3, 0.3), pos_hint = {'x':0.0, 'y':0.7}, background_color = (0.0,0.0,0.0,0.0),overlay_color = (0.0,0.0,0.0,0.0))
 
#SQL connection
conn = pyodbc.connect('Driver={SQL Server};'
                      'Server=DAN-PC\SQLEXPRESS;'
                      'Database=trivia;'
                      'Trusted_Connection=yes;')

#SQL questions import
cursor = conn.cursor()
cursor.execute('SELECT * FROM trivia.dbo.QUESTIONS_2')

questions_list = []
for row in cursor:
    questions_list.append((row[0],row[1],row[2],row[3],row[4],row[5],row[6]))
questions_list_cat_0 = [x for x in questions_list if x[6]=='0']
questions_list_cat_1 = [x for x in questions_list if x[6]=='1']
questions_list_cat_2 = [x for x in questions_list if x[6]=='2']
questions_list_cat_3 = [x for x in questions_list if x[6]=='3']
questions_list = [questions_list_cat_0,questions_list_cat_1,questions_list_cat_2,questions_list_cat_3]


answers_log = []

#Paths - insert to different config file
clock_log_file_path = r"C:\Users\Dan\Desktop\clock_log.txt"
question_trigger_path = r"C:\Users\Dan\Desktop\trigger.txt"
kss_trigger_path = r"C:\Users\Dan\Desktop\kss_trigger.txt"
hazard_popup_trigger_path = r"C:\Users\Dan\Desktop\popup_trigger.txt"

#Import data form config file
congif_file_path = r"C:\Users\Dan\Desktop\trivia_config.json"
congif_file = open(congif_file_path)
config = json.load(congif_file)
sync_freq = int(config['Sync_freq'])
sync_freq = round(1.0/sync_freq,2)
display_time = int(config['Display_time'])
text_size = int(config['Text_size'])
words_to_line_break = int(config['Words_to_line_break'])
response_time = int(config['Response_time'])
terminate_time = int(config['Terminate_time'])
questions_batch_size = int(config['Questions_batch_size'])
voiced_questions = bool(config['Voiced_questions']=="True")
#kss_on = bool(config['Kss_on'])
hazard_popup_time_dismiss = int(config['Hazard_popup_time_dismiss'])
#trivia_on = True // Trivia is always onss
kss_threshold = 0
category_list = ["cat1","cat2","cat3","cat4"]
#if kss_on:
#	trivia_on = False
kss_threshold = int(config['Kss_threshold'])

degraded_fitness = False
#reset_trigger_on_kss = True

def show_hazard_popup():
	#add a bip sound
	hazard_popup.open()


def dismiss_hazard_popup(*args):
	hazard_popup.dismiss()

#Threading class radadin quistions and kss trigger
import timer
timer.start()

class TriggerThread(threading.Thread):
	def __init__(self, question_trigger_path):
		threading.Thread.__init__(self)
		self.path = question_trigger_path
		self.stop = -1
		self.trigger = 0
		self.lock = threading.Lock()
		self.kill = False

	def read_file(self):
		success = False
		while not success:
			try:
				file = open(self.path,"r")
				self.trigger = int(file.read())
				file.close()
				success = True
			except:
				continue

	def get_value(self):
		with self.lock:
			return self.trigger

	def pp(self, num):
		print(str(num))

	def turn_off_trigger(self):
		success = False
		while not success:
			with self.lock:
				try:
					file = open(self.path,"w")
					file.write("0")
					file.close()
					success = True
				except:
					continue

	def run(self):
		self.read_file()
		while self.trigger != self.stop:
			time.sleep(sync_freq)
			with self.lock:
				self.read_file()

			if self.kill:
				break
		timer.stop()


class SoundThread(threading.Thread):
	def __init__(self, sound_file_path, question_number):
		threading.Thread.__init__(self)	
		self.path = sound_file_path
		#self.question_number = question_number

	def run(self):
		winsound.PlaySound(self.path,winsound.SND_ASYNC)



trigger = TriggerThread(question_trigger_path)
trigger.start()

#if kss_on:
kss_trigger = TriggerThread(kss_trigger_path)
kss_trigger.start()

hazard_popup_trigger = TriggerThread(hazard_popup_trigger_path)
hazard_popup_trigger.start()


def check_trigger_for_hazard_popup(*args):
	if hazard_popup_trigger.get_value() == 1:
		show_hazard_popup()
		hazard_popup_trigger.turn_off_trigger()
		Clock.schedule_once(dismiss_hazard_popup,hazard_popup_time_dismiss)
	return True

Clock.schedule_interval(check_trigger_for_hazard_popup,0.1)

class WindowManager(ScreenManager):

	def __init__(self, *args, **kwargs):
		super(WindowManager,self).__init__(*args, **kwargs)
		self.question_num = [0,0,0,0]
		self.wait_for_trigger = None
		self.is_playing = None
		self.wait_for_kss_trigger = None
		self.on_kss_screen = None
		self.question_category = None
		#self.degraded_fitness = None

	#Inside of function will be replaced with initial game offer
	def start_screen(self):
		self.question_num = [0,0,0,0]
		self.wait_for_trigger = True
		#if kss_on:
		self.wait_for_kss_trigger =True
		self.on_kss_screen = False
		self.question_category = 0
		#self.degraded_fitness = False
		self.current = "welcome_screen"

	def start_game(self):
		self.current = "category_screen"


class Blank(Screen):
	def entry(self):
		mute = SoundThread(r"C:\Users\Dan\Downloads\Soundless Sound.wav",0) #play muted sound
		mute.start()
		if self.manager.is_playing:
			self.manager.current = "question_screen"
		else:
			self.manager.current = "welcome_screen"

#Welcome or hold screen
class WelcomeScreen(Screen):

	def __init__(self, *args, **kwargs):
		super(WelcomeScreen,self).__init__(*args, **kwargs)

	def entry(self):
		global degraded_fitness
		if degraded_fitness:
			degraded_fitness_popup.open()

		#if kss_on:
		Clock.schedule_interval(self.check_trigger_for_kss, sync_freq)
		Clock.schedule_interval(self.check_trigger_for_batch_start, sync_freq)
		

		
	def check_trigger_for_batch_start(self, *args):
		#global trivia_on
		#if not trivia_on:
		#	return False
		#if len(questions_list) > self.manager.question_num:
		if trigger.get_value() == 1:
			trigger.turn_off_trigger()
			self.wait_for_trigger = False
			self.manager.current = "offer_screen"
			return False
		elif trigger.get_value() == -1:
			self.manager.current = "end_screen"
			return False


	def check_trigger_for_kss(self, *args):
		if kss_trigger.get_value() == 1:
			kss_trigger.turn_off_trigger()
			trigger.turn_off_trigger()
			self.manager.wait_for_kss_trigger = False
			self.manager.is_playing = False
			self.manager.current = "kss"
			return False

class OfferScreen(Screen):
	def entry(self):
		global degraded_fitness
		if degraded_fitness:
			degraded_fitness_popup.open()

	def is_playing(self, ans):
		global degraded_fitness
		self.manager.is_playing = ans
		if ans:
			degraded_fitness = False
			self.manager.start_game()
		else:
			self.manager.wait_for_trigger = True
			self.manager.current = "welcome_screen"

			#Add response time?

class KSS(Screen):
	#To kill questions voice on kss enter - play muted sound or read kss question

	def entry(self):
		self.manager.on_kss_screen = True
		self.clicked = False
		self.wait_for_response()

	def leave(self):
		self.manager.on_kss_screen = False

	def click(self, ans_num):
		global degraded_fitness
		#TODO: store answer and time
		#global trivia_on
		if ans_num > kss_threshold:
			#trivia_on = True
			#self.manager.degraded_fitness = True
			degraded_fitness = True
			degraded_fitness_popup.open()
			self.manager.current = "offer_screen"
		else:
			#trivia_on = False
			self.manager.current = "blank"
		self.leave()
		self.clicked = True
		
	def wait_for_response(self):
		self.beggin_time = time.time()
		Clock.schedule_interval(self.check_question_end, sync_freq)

	def check_question_end(self,*args):
		if time.time() - self.beggin_time > response_time: #TODO: update unique KSS wating time
			answers_log.append(("answer for KSS:",None, None, None))
			self.manager.current = "blank"
		elif self.clicked:
			pass
		else:
			return True
		self.manager.wait_for_kss_trigger = True
		#self.manager.current = "blank"
		return False

class CategoryScreen(Screen):

	def entry(self):
		global category_list
		self.clicked = False
		self.ids.category_choose.text = "Please choose a category."
		self.ids.category0.text = category_list[0]
		self.ids.category1.text = category_list[1]
		self.ids.category2.text = category_list[2]
		self.ids.category3.text = category_list[3]
		self.wait_for_response()

	def click(self, ans_num):
		self.manager.question_category = ans_num
		self.clicked = True

	def wait_for_response(self):
			self.beggin_time = time.time()
			Clock.schedule_interval(self.check_question_end, sync_freq)

	def check_question_end(self,*args):
		if time.time() - self.beggin_time > response_time: #TODO: update unique category wating time
			#answers_log.append((None,None, None, None))
			self.manager.question_category = randrange(4)
		elif self.clicked:
			pass
		else:
			return True
		self.manager.current = "question_screen"
		return False


class QuestionScreen(Screen):

	def entry(self):
		self.ids['answer1'].background_color = 1.0, 1.0, 1.0, 1.0
		self.ids['answer2'].background_color = 1.0, 1.0, 1.0, 1.0
		self.ids['answer3'].background_color = 1.0, 1.0, 1.0, 1.0
		self.ids['answer4'].background_color = 1.0, 1.0, 1.0, 1.0
		self.clicked = False
		self.present_questions()
		self.wait_for_response()

	def click(self, ans_num):
		if ans_num == questions_list[self.manager.question_category][self.manager.question_num[self.manager.question_category]][5]:
			button_id = 'answer'+str(ans_num)
			self.ids[button_id].background_color = 0.0, 1.0, 0.0, 1.0
		else:
			button_id = 'answer'+str(ans_num)
			self.ids[button_id].background_color = 1.0, 0.0, 0.0, 1.0
													#TODO:put question id here
		answers_log.append(("answer for question:",self.manager.question_num[0], ans_num, timer.get_time()))
		Clock.schedule_once(self.clicked_true, 2)
			 

	def clicked_true(self,*args):
		self.clicked = True

	def break_question(self, question):
		question_splitted = question.split()
		breaked_question = ''
		for w_num, w in enumerate(question_splitted):
			breaked_question += w
			breaked_question += " "
			if (w_num+1) % words_to_line_break == 0:
				breaked_question += "\n"
		return breaked_question

	def present_questions(self):
		try:
			self.ids.question.text = self.break_question(
				questions_list[self.manager.question_category][self.manager.question_num[self.manager.question_category]][0])
			self.ids.answer1.text = "A."+ questions_list[self.manager.question_category][self.manager.question_num[self.manager.question_category]][1]
			self.ids.answer2.text = "B."+ questions_list[self.manager.question_category][self.manager.question_num[self.manager.question_category]][2]
			self.ids.answer3.text = "C."+ questions_list[self.manager.question_category][self.manager.question_num[self.manager.question_category]][3]
			self.ids.answer4.text = "D."+ questions_list[self.manager.question_category][self.manager.question_num[self.manager.question_category]][4]
			if voiced_questions:
				sound = SoundThread(r"C:\Users\Dan\Downloads\1.wav",0)
				sound.start()
		except:
			pass #out of Questions


	def wait_for_response(self):
		self.beggin_time = time.time()
		Clock.schedule_interval(self.check_question_end, sync_freq)


	def check_question_end(self,*args):
		if self.manager.on_kss_screen:
			return False
		if time.time() - self.beggin_time > response_time:
														#TODO: put question id
			answers_log.append(("answer for question:",self.manager.question_num[0],None, None))
		elif self.clicked:
			pass
		else:
			return True
		self.manager.question_num[self.manager.question_category] += 1
	
		if self.manager.question_num[self.manager.question_category] % questions_batch_size == 0:
			self.manager.wait_for_trigger = True
			self.manager.is_playing = False
		self.manager.current = "blank"
		return False

class EndScreen(Screen):
	def entry(self):
		pass


kv = Builder.load_file('Trivia_4.kv')

class Trivia_4(App):

	def build(self):
		kv.start_screen()
		return kv

if __name__ == "__main__":
	Trivia_4().run()
	trigger.kill = True
	kss_trigger.kill = True
	hazard_popup_trigger.kill = True
	
for element in answers_log:
	query = "INSERT INTO trivia.dbo.RESULTS VALUES ('"+str(element[0])+"','"+str(element[1])+"','"+str(element[2])+"','"+str(element[3])+"');"
	cursor.execute(query)
	conn.commit()

