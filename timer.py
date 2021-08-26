import time
import threading


global on

value = 0

class Runner(threading.Thread):
	def __init__(self):
		threading.Thread.__init__(self)
		self.on = None

	def run(self):
		self.start_timer()

	def start_timer(self):
		global value
		self.on = True
		now = time.time()
		while self.on:
			time.sleep(1)
			try:
				file = open(r"C:\Users\Dan\Desktop\clock_log.txt", "w")
				value = round(time.time()-now)
				print(value)
				file.write(str(a))
				file.close()
			except:
				continue

	def stop_timer(self):
		self.on = False

global x
x = Runner()
def start():
	x.start()

def get_time():
	global value
	return value

def stop():
	x.stop_timer()

	#conda activate thesis_trivia