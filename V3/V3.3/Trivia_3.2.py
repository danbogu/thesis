import winsound
import json
import threading
import time
import collections
import random
from bidi import algorithm
import kivy
from kivy.config import Config
Config.set('graphics', 'fullscreen', '0')
from kivy.app import App
from kivy.core.window import Window
from kivy.uix.screenmanager import ScreenManager, Screen, NoTransition
from kivy.lang import Builder
from kivy.clock import Clock
from kivy.uix.popup import Popup
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.image import Image
from kivy.uix.boxlayout import BoxLayout
from kivy.clock import ClockBaseBehavior
from kivy.properties import OptionProperty
import pyodbc
import SimClock
SimClock.start()

def remove_apostrophe(sentence):
    t = []
    for s in range(len(sentence)):
        if sentence[s] =="'":
            t.append("'")
        t.append(sentence[s])
    return "".join(t)

#Import data form config file
congif_file_path = r"C:\Users\Dan\Desktop\trivia_config.json"
congif_file = open(congif_file_path)
config = json.load(congif_file)

participant_ID = int(config['Participant_ID'])
run_number = int(config['Run_number'])

sql_server_name = str(config['SQL_server_name'])
sql_database_name = str(config['SQL_database_name']) #not integrated yet
questions_main_database_name = str(config['Questions_main_database_name'])

hazard_sign_image_path = str(config['Hazard_sign_image_path'])
degraded_fitness_eye_sign_image_path = str(config['Degraded_fitness_eye_sign_image_path'])
degraded_fitness_coffee_sign_image_path = str(config['Degraded_fitness_coffee_sign_image_path'])
clock_log_file_path = str(config['Clock_log_file_path'])
question_trigger_path = str(config['Question_trigger_path'])
kss_trigger_path = str(config['Kss_trigger_path'])
hazard_popup_trigger_path = str(config['Hazard_popup_trigger_path'])
car_home_screen = str(config['Car_home_screen'])
#simulator_clock_file_path = str(config['Simulator_clock_file_path'])
mute_sound_file_path = str(config['Mute_sound_file_path'])
trivia_suggestion_sound_file_path = str(config['Trivia_suggestion_sound_file_path'])
hazard_degradedFitness_sound_file_path = str(config['Hazard_degradedFitness_sound_file_path'])
rest_required_sound_file_path = str(config['Rest_required_sound_file_path'])
questions_sound_folder_path = str(config['Questions_sound_folder_path'])
degraded_fitness_file_path = str(config['Degraded_fitness_file_path'])
sync_freq = int(config['Sync_freq'])
sync_freq = round(1.0/sync_freq,2)
answer_click_delay = int(config['Answer_click_delay'])
text_size = int(config['Text_size']) #Not functioning
words_to_line_break = int(config['Words_to_line_break'])
response_time = int(config['Response_time'])
score_screen_time = int(config['Score_screen_time'])
terminate_time = int(config['Terminate_time']) #Not functioning
questions_batch_size = int(config['Questions_batch_size'])
voiced_questions = bool(config['Voiced_questions']=="True")
hazard_popup_time_dismiss = int(config['Hazard_popup_time_dismiss'])
time_to_dismiss_degraded_fitness_popup = int(config['Time_to_dismiss_degraded_fitness_popup'])
kss_threshold = 0
kss_threshold = int(config['Kss_threshold'])

if run_number not in [1,2]:
	raise Exception("Run number must be 1 or 2")

#Hazard popup
hazard_popup = Popup(title='',separator_height = 0, #title_align = OptionProperty(),
			content = Image(source=hazard_sign_image_path),
			size_hint=(0.2, 0.2), pos_hint = {'x':0.4, 'y':0.8})


degraded_fitness_eye_popup_box = BoxLayout(orientation='vertical')
degraded_fitness_coffee_popup_box = BoxLayout(orientation='vertical')


degraded_fitness_eye_popup = Popup(title='Degraded Fitness',separator_height = 0, title_align = 'center', title_size = '12',
			content = degraded_fitness_eye_popup_box, auto_dismiss = False,
			size_hint=(0.3, 0.3), pos_hint = {'x':0.0, 'y':0.7}, background_color = (0.0,0.0,0.0,0.0),overlay_color = (0.0,0.0,0.0,0.0))
 

degraded_fitness_coffee_popup = Popup(title='Degraded Fitness',separator_height = 0, title_align = 'center', title_size = '12',
			content = degraded_fitness_coffee_popup_box, auto_dismiss = False,
			size_hint=(0.3, 0.3), pos_hint = {'x':0.0, 'y':0.7}, background_color = (0.0,0.0,0.0,0.0),overlay_color = (0.0,0.0,0.0,0.0))

degraded_fitness_log = []
Degraded_fitness_acknowledgement = collections.namedtuple('Degraded_fitness_acknowledgement',['Value', 'TimeStemp'])

degraded_fitness_popup_dismissed = False

def dismiss_degraded_fitness(instance):
	global degraded_fitness_popup_dismissed
	degraded_fitness_file_success = False
	while not degraded_fitness_file_success:
		try:
			file = open(degraded_fitness_file_path,"w")
			file.write("0")
			file.close()
			degraded_fitness_file_success = True
		except:
			continue
		if degraded_fitness_file_success:
			break

	degraded_fitness_coffee_popup.dismiss()
	degraded_fitness_eye_popup.dismiss()
	degraded_fitness_log.append(Degraded_fitness_acknowledgement("Dismissed",str(SimClock.get_time())))
	degraded_fitness_popup_dismissed = True
	sound = SoundThread(trivia_suggestion_sound_file_path,0)
	sound.start()


degraded_fitness_eye_popup_box.add_widget(Image(source=degraded_fitness_eye_sign_image_path))
degraded_fitness_eye_popup_box.add_widget(Button(pos_hint={'center_x':0.5}, text='Close', on_press = dismiss_degraded_fitness, size_hint=(0.5, 0.2)))
degraded_fitness_coffee_popup_box.add_widget(Image(source=degraded_fitness_coffee_sign_image_path))
degraded_fitness_coffee_popup_box.add_widget(Button(pos_hint={'center_x':0.5},text='Close', on_press = dismiss_degraded_fitness, size_hint=(0.5, 0.2)))


#SQL connection
conn = pyodbc.connect('Driver={SQL Server};'
                      'Server='+sql_server_name+';'
                      'Database='+sql_database_name+';'
                      'Trusted_Connection=yes;')

Question = collections.namedtuple('Question',['ID', 'Question', 'Answer1', 'Answer2', 'Answer3', 'Answer4', 'Currect'])
Question_answer = collections.namedtuple('Question_answer',['ID', 'Answer_number', 'TimeStemp'])
KSS_answer = collections.namedtuple('KSS_answer',['Value', 'TimeStemp'])
questions_list = []
answers_log = []
kss_log = []
#SQL questions import
cursor = conn.cursor()
if run_number is 1:
	cursor.execute('SELECT * FROM trivia.dbo.'+questions_main_database_name)
	for row in cursor:
		questions_list.append(Question(row[0],row[1],row[2],row[3],row[4],row[5],row[6]))
	random.shuffle(questions_list) #The shuffle is done in the first experiment run.

if run_number is 2:
	cursor.execute('SELECT * FROM trivia.dbo.QUESTIONS_FOR_PART_2_ID_'+str(participant_ID))
	for row in cursor:
		questions_list.append(Question(row[0],row[1],row[2],row[3],row[4],row[5],row[6]))

degraded_fitness = False
#reset_trigger_on_kss = True


class SoundThread(threading.Thread):
	def __init__(self, sound_file_path=None, question_number=None, frequency=None, duration=None):
		threading.Thread.__init__(self)	
		self.path = sound_file_path
		self.question_number = question_number
		self.frequency = frequency
		self.duration = duration

	def run(self):
		if self.path is not None and self.question_number is not None:
			winsound.PlaySound(self.path,winsound.SND_ASYNC)
		else:
			winsound.Beep(self.frequency,self.duration)


def show_hazard_popup():
	hazard_popup.open()
	#sound = SoundThread(frequency = 1000, duration = 1000)
	#sound.start()
	sound = SoundThread(hazard_degradedFitness_sound_file_path,0)
	sound.start()


def dismiss_hazard_popup(*args):
	hazard_popup.dismiss()

#Threading class quistions and kss trigger
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

#TODO: What is that!??
	def pp(self, num):
		print(str(num))

	def turn_off_trigger(self):
		success = False
		while not success:
			with self.lock:
				try:
					file = open(self.path,"w")
					file.write("2") #Only in the big simulator - After reading put "2" as a sign that the trigger was spotted.
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
		SimClock.stop()




trigger = TriggerThread(question_trigger_path)
trigger.start()

kss_trigger = TriggerThread(kss_trigger_path)
kss_trigger.start()

hazard_popup_trigger = TriggerThread(hazard_popup_trigger_path)
hazard_popup_trigger.start()

actived_hazard_popup = False
def check_trigger_for_hazard_popup(*args):
	global actived_hazard_popup
	global hazard_popup_trigger
	if hazard_popup_trigger.get_value() == 1:
		if actived_hazard_popup:
			return True
		#hazard_popup_trigger.turn_off_trigger()
		show_hazard_popup()
		actived_hazard_popup = True
		return True
	if actived_hazard_popup:
		if hazard_popup_trigger.get_value() == 0:
			dismiss_hazard_popup()
			actived_hazard_popup = False
		#Clock.schedule_once(dismiss_hazard_popup,hazard_popup_time_dismiss)
	return True

Clock.schedule_interval(check_trigger_for_hazard_popup,0.1)

class WindowManager(ScreenManager):

	def __init__(self, *args, **kwargs):
		super(WindowManager,self).__init__(*args, **kwargs)
		self.to_score_screen = None
		self.score = 0
		self.question_num = 0
		self.wait_for_trigger = None
		self.is_playing = None
		self.wait_for_kss_trigger = None
		self.on_kss_screen = None
		self.kss_appear_counter = 0
		#self.degraded_fitness = None

	#Inside of function will be replaced with initial game offer
	def start_screen(self):
		self.to_score_screen = False
		self.score = 0
		self.question_num = 0
		self.wait_for_trigger = True
		self.wait_for_kss_trigger =True
		self.on_kss_screen = False
		self.kss_appear_counter = 0
		#self.degraded_fitness = False
		self.current = "welcome_screen"

	def start_game(self):
		self.current = "question_screen"


class Blank(Screen):
	def entry(self):
		mute = SoundThread(mute_sound_file_path,0) #play muted sound
		mute.start()
		if self.manager.to_score_screen:
			self.manager.current = "score_screen"
		elif self.manager.is_playing:
			self.manager.current = "question_screen"
		else:
			self.manager.current = "welcome_screen"

class ScoreScreen(Screen):
	def entry(self):
		global score_screen_time
		self.manager.to_score_screen = False
		self.ids.score_label.text = algorithm.get_display("תודה ששיחקת! מקווים שנהנית!\n\n הניקוד שלך: "+ str(self.manager.score) + ".\n\n בקרוב נמשיך לשחק.")
		Clock.schedule_once(self.to_welcome_screen,score_screen_time)

	def to_welcome_screen(self,*args):
		self.manager.current = "welcome_screen"

#Welcome or hold screen
class WelcomeScreen(Screen):

	def __init__(self, *args, **kwargs):
		super(WelcomeScreen,self).__init__(*args, **kwargs)

	def entry(self):
		global degraded_fitness
		#Window.clearcolor = (32/255, 32/255, 32/255, 1)
		self.ids.home_screen.source = car_home_screen
		Clock.schedule_interval(self.check_trigger_for_kss, sync_freq)
		Clock.schedule_interval(self.check_trigger_for_batch_start, sync_freq)
		'''
		if degraded_fitness:
				if self.manager.kss_appear_counter > 2:
					degraded_fitness_coffee_popup.open()
				else:
					degraded_fitness_eye_popup.open()
		'''

		#self.ids.welcome_label.text = algorithm.get_display("ברוך הבא! אנא המתן לשאלות.")

		
		
	def check_trigger_for_batch_start(self, *args):
		#global trivia_on
		#if not trivia_on:
		#	return False
		if self.manager.is_playing or self.manager.on_kss_screen:
			#trigger.turn_off_trigger()
			return True

		if len(questions_list) > self.manager.question_num:
			if trigger.get_value() == 1:
				#trigger.turn_off_trigger()
				self.wait_for_trigger = False
				self.manager.current = "offer_screen"
				return False
		if trigger.get_value() == -1:
			self.manager.current = "end_screen"
			return False


	def check_trigger_for_kss(self, *args):
		if self.manager.on_kss_screen:
			#kss_trigger.turn_off_trigger()
			return True

		if kss_trigger.get_value() == 1:
			#kss_trigger.turn_off_trigger()
			#trigger.turn_off_trigger()
			self.manager.wait_for_kss_trigger = False
			self.manager.is_playing = False
			self.manager.current = "kss"
			return False

class OfferScreen(Screen):
	def auto_dismiss_degreded_fitness_popup(self,*args):
		global degraded_fitness_popup_dismissed
		if not degraded_fitness_popup_dismissed:
			degraded_fitness_coffee_popup.dismiss()
			degraded_fitness_eye_popup.dismiss()
			degraded_fitness_log.append(Degraded_fitness_acknowledgement("Not dismissed","None"))
			sound = SoundThread(trivia_suggestion_sound_file_path,0)
			sound.start()

	def entry(self):
		global degraded_fitness
		if degraded_fitness:
			#Generic bip sound
			#sound = SoundThread(frequency = 1000, duration = 1000)
			#sound.start()
			global degraded_fitness_popup_dismissed
			
			if self.manager.kss_appear_counter > 2:

				self.success = False
				while not self.success:
					try:
						self.file = open(degraded_fitness_file_path,"w")
						self.file.write("2")
						self.file.close()
						self.success = True
					except:
						continue
					if self.success:
						break

				degraded_fitness_coffee_popup.open()
				degraded_fitness_popup_dismissed = False
				sound = SoundThread(rest_required_sound_file_path,0)
				sound.start()
			else:

				self.success = False
				while not self.success:
					try:
						self.file = open(degraded_fitness_file_path,"w")
						self.file.write("1")
						self.file.close()
						self.success = True
					except:
						continue
					if self.success:
						break

				degraded_fitness_eye_popup.open()
				degraded_fitness_popup_dismissed = False
				sound = SoundThread(hazard_degradedFitness_sound_file_path,0)
				sound.start()
			Clock.schedule_once(self.auto_dismiss_degreded_fitness_popup, time_to_dismiss_degraded_fitness_popup)
		else:
			#sound = SoundThread(frequency = 500, duration = 500)
			#sound.start()
			sound = SoundThread(trivia_suggestion_sound_file_path,0)
			sound.start()

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
		#sound = SoundThread(frequency = 500, duration = 500)
		#sound.start()
		sound = SoundThread(trivia_suggestion_sound_file_path,0)
		sound.start()
		self.manager.on_kss_screen = True
		self.manager.kss_appear_counter += 1
		self.clicked = False
		self.wait_for_response()

	def leave(self):
		self.manager.on_kss_screen = False

	def click(self, ans_num):
		global degraded_fitness
		global kss_result_file
		kss_log.append(KSS_answer(str(ans_num),str(SimClock.get_time())))
		if ans_num > kss_threshold:
			degraded_fitness = True
			self.manager.current = "offer_screen"
		else:
			self.manager.current = "blank"
		self.leave()
		self.clicked = True
		
	def wait_for_response(self):
		self.beggin_time = time.time()
		Clock.schedule_interval(self.check_question_end, sync_freq)

	def check_question_end(self,*args):
		if time.time() - self.beggin_time > response_time: #TODO: update unique KSS wating time
			kss_log.append(KSS_answer(str("None"),str("None")))
			self.manager.on_kss_screen = False
			self.manager.current = "blank"
		elif self.clicked:
			pass
		else:
			return True
		self.manager.wait_for_kss_trigger = True
		#self.manager.current = "blank"
		return False


class QuestionScreen(Screen):

	def entry(self):
		self.ids.answer1.disabled = False
		self.ids.answer2.disabled = False
		self.ids.answer3.disabled = False
		self.ids.answer4.disabled = False
		self.ids['answer1'].background_color = 0.5, 0.5, 0.5, 0.5
		self.ids['answer2'].background_color = 0.5, 0.5, 0.5, 0.5
		self.ids['answer3'].background_color = 0.5, 0.5, 0.5, 0.5
		self.ids['answer4'].background_color = 0.5, 0.5, 0.5, 0.5
		self.clicked = False
		self.present_questions()
		self.wait_for_response()

	def click(self, ans_num):
		self.ans_num = ans_num
		if ans_num == int(questions_list[self.manager.question_num].Currect):
			self.manager.score += 1
			button_id = 'answer'+str(ans_num)
			self.ids[button_id].background_color = 0.0, 1.0, 0.0, 1.0
		else:
			button_id = 'answer'+str(ans_num)
			self.ids[button_id].background_color = 1.0, 0.0, 0.0, 1.0
		answers_log.append(Question_answer(str(questions_list[self.manager.question_num].ID), str(ans_num), str(SimClock.get_time())))

		self.ids.answer1.disabled = True
		self.ids.answer2.disabled = True
		self.ids.answer3.disabled = True
		self.ids.answer4.disabled = True
	
		Clock.schedule_once(self.clicked_true, answer_click_delay)

			 

	def clicked_true(self,*args):
		self.clicked = True

	def get_clicked():
		return self.clicked

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
			self.ids.question.text = algorithm.get_display(self.break_question(
				questions_list[self.manager.question_num].Question))
			self.ids.answer1.text = algorithm.get_display("א."+questions_list[self.manager.question_num].Answer1)
			self.ids.answer2.text = algorithm.get_display("ב."+questions_list[self.manager.question_num].Answer2)
			self.ids.answer3.text = algorithm.get_display("ג."+questions_list[self.manager.question_num].Answer3)
			self.ids.answer4.text = algorithm.get_display("ד."+questions_list[self.manager.question_num].Answer4)
			if voiced_questions:
				sound = SoundThread(questions_sound_folder_path+"\\"+str(questions_list[self.manager.question_num].ID)+".wav",0)
				sound.start()
		except:
			pass #TODO:out of Questions


	def wait_for_response(self):
		self.beggin_time = time.time()
		Clock.schedule_interval(self.check_question_end, sync_freq)


	def check_question_end(self,*args):
		if self.manager.on_kss_screen:
			return False
		if time.time() - self.beggin_time > response_time:
			answers_log.append(Question_answer(str(questions_list[self.manager.question_num].ID), str("None"), str(SimClock.get_time())))
		elif self.clicked:
			pass
		else:
			return True
		self.manager.question_num += 1
	
		if self.manager.question_num % questions_batch_size == 0:
			self.manager.wait_for_trigger = True
			self.manager.is_playing = False
			self.manager.to_score_screen = True
		self.manager.current = "blank"
		return False

class EndScreen(Screen):
	def entry(self):
		pass


kv = Builder.load_file('Trivia_3.2.kv')

class Trivia_3(App):

	def build(self):
		kv.start_screen()
		return kv

if __name__ == "__main__":
	Trivia_3().run()
	trigger.kill = True
	kss_trigger.kill = True
	hazard_popup_trigger.kill = True

	if run_number is 1: #at the end of part 1 we create the datebase for part 2
		query = "CREATE TABLE QUESTIONS_FOR_PART_2_ID_" + str(participant_ID) + "(ID VARCHAR(255),Question VARCHAR(255),Answer1 VARCHAR(255),Answer2 VARCHAR(255),Answer3 VARCHAR(255),Answer4 VARCHAR(255),Currect VARCHAR(255))"	
		cursor.execute(query)
		conn.commit()
		for q in range(kv.question_num+1,len(questions_list)):
			#todo:change to generic database name
			query = "INSERT INTO trivia.dbo.QUESTIONS_FOR_PART_2_ID_" + str(participant_ID) + " VALUES ('" + str(questions_list[q].ID) + "','" + str(remove_apostrophe(questions_list[q].Question)) + "','"+ str(remove_apostrophe(questions_list[q].Answer1)) + "','"+ str(remove_apostrophe(questions_list[q].Answer2)) + "','"+ str(remove_apostrophe(questions_list[q].Answer3)) + "','"+ str(remove_apostrophe(questions_list[q].Answer4)) + "','"+ str(questions_list[q].Currect) + "')"
			cursor.execute(query)
			conn.commit()
		query = "CREATE TABLE RESULTS_PART_1_ID_" + str(participant_ID) + "(ID VARCHAR(255),Answer_number VARCHAR(255),TimeStemp VARCHAR(255))"	
		cursor.execute(query)

		if len(answers_log) == 0:
			print("Answer log is empty")
			answers_log.append(Question_answer("None","None","None"))
		for element in answers_log:
			query = "INSERT INTO trivia.dbo.RESULTS_PART_1_ID_" + str(participant_ID) + " VALUES ('"+str(element.ID)+"','"+str(element.Answer_number)+"','"+str(element.TimeStemp)+"');"
			cursor.execute(query)
			conn.commit()
		query = "CREATE TABLE KSS_RESULTS_PART_1_ID_" + str(participant_ID) + "(Value VARCHAR(255),TimeStemp VARCHAR(255))"	
		cursor.execute(query)

		if len(kss_log) == 0:
			print("KSS log is empty")
			kss_log.append(KSS_answer("None","None"))
		for element in kss_log: 
			query = "INSERT INTO trivia.dbo.KSS_RESULTS_PART_1_ID_" + str(participant_ID) + " VALUES ('"+str(element.Value)+"','"+str(element.TimeStemp)+"');"
			cursor.execute(query)
			conn.commit()

		query = "CREATE TABLE DEGRADED_FITNESS_ACKNOWLEDGMENT_PART_1_ID_" + str(participant_ID) + "(Value VARCHAR(255),TimeStemp VARCHAR(255))"	
		cursor.execute(query)

		if len(degraded_fitness_log) == 0:
			print("Degraded fitness log is empty")
			degraded_fitness_log.append(Degraded_fitness_acknowledgement("None","None"))
		for element in degraded_fitness_log: 
			query = "INSERT INTO trivia.dbo.DEGRADED_FITNESS_ACKNOWLEDGMENT_PART_1_ID_" + str(participant_ID) + " VALUES ('"+str(element.Value)+"','"+str(element.TimeStemp)+"');"
			cursor.execute(query)
			conn.commit()
	if run_number is 2:
		query = "CREATE TABLE RESULTS_PART_2_ID_" + str(participant_ID) + "(ID VARCHAR(255),Answer_number VARCHAR(255),TimeStemp VARCHAR(255))"	
		cursor.execute(query)

		if len(answers_log) == 0:
			print("Answer log is empty")
			answers_log.append(Question_answer("None","None","None"))
		for element in answers_log: 
			query = "INSERT INTO trivia.dbo.RESULTS_PART_2_ID_" + str(participant_ID) + " VALUES ('"+str(element.ID)+"','"+str(element.Answer_number)+"','"+str(element.TimeStemp)+"');"
			cursor.execute(query)
			conn.commit()

		query = "CREATE TABLE KSS_RESULTS_PART_2_ID_" + str(participant_ID) + "(Value VARCHAR(255),TimeStemp VARCHAR(255))"	
		cursor.execute(query)

		if len(kss_log) == 0:
			print("KSS log is empty")
			kss_log.append(KSS_answer("None","None"))
		for element in kss_log: 
			query = "INSERT INTO trivia.dbo.KSS_RESULTS_PART_2_ID_" + str(participant_ID) + " VALUES ('"+str(element.Value)+"','"+str(element.TimeStemp)+"');"
			cursor.execute(query)
			conn.commit()

		query = "CREATE TABLE DEGRADED_FITNESS_ACKNOWLEDGMENT_PART_2_ID_" + str(participant_ID) + "(Value VARCHAR(255),TimeStemp VARCHAR(255))"	
		cursor.execute(query)

		if len(degraded_fitness_log) == 0:
			print("Degraded fitness log is empty")
			degraded_fitness_log.append(Degraded_fitness_acknowledgement("None","None"))
		for element in degraded_fitness_log: 
			query = "INSERT INTO trivia.dbo.DEGRADED_FITNESS_ACKNOWLEDGMENT_PART_2_ID_" + str(participant_ID) + " VALUES ('"+str(element.Value)+"','"+str(element.TimeStemp)+"');"
			cursor.execute(query)
			conn.commit()




