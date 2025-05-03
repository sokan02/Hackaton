import os
import glob
import time
import RPi.GPIO as GPIO
import threading
import datetime


interval = 1

speed = 0
desired_temperature = 22

sw_people_prev = 0
sw_window_prev = 0

STATE = ''

PIN1 = 17
PIN2 = 27
PIN3 = 22

SW_WINDOW = 23
SW_PEOPLE = 24

INPUT_ON = 0

TEMP_MAX = 32
TEMP_MIN = 18

P = 10
I = 0.8
SPEED_PROP = 0.85
integral_sum = 0
fan_speed = 0
FAN_SPEED_MAX = 100
FAN_SPEED_MIN = 0


def setup_sensor():
    os.system('modprobe w1-gpio')
    os.system('modprobe w1-therm')

    base_dir = '/sys/bus/w1/devices/'
    device_folder = glob.glob(base_dir + '28*')[0]  
    device_file = device_folder + '/w1_slave'
    return device_file

def read_temp_raw(device_file):
    with open(device_file, 'r') as f:
        lines = f.readlines()
    return lines

def read_temperature(device_file):
	lines = read_temp_raw(device_file)
    
	while lines[0].strip()[-3:] != 'YES':
		time.sleep(0.2)
		lines = read_temp_raw(device_file)
    
	equals_pos = lines[1].find('t=')
	if equals_pos != -1:
		temp_string = lines[1][equals_pos+2:]
		temp_c = float(temp_string) / 1000.0
		return temp_c
	return None




'''
    LED1 is Pin 17 
    LED2 is Pin 27 
    LED3 is Pin 22 
    
	Pins in the program have different markings than ones on the board
'''
def turn_on_led(pin):
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(pin, GPIO.OUT)
    GPIO.output(pin, GPIO.HIGH)

def turn_off_led(pin):
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(pin, GPIO.OUT)
    GPIO.output(pin, GPIO.LOW)


def read_switch_state(pin):
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)  
    return int(GPIO.input(pin))
 
def PID(temp_setpoint, temp_read):
	global fan_speed
	global integral_sum
	
	if(integral_sum  > TEMP_MAX):
		integral_sum = TEMP_MAX
	if(integral_sum  < -TEMP_MAX):
		integral_sum = -TEMP_MAX
	error = abs(temp_setpoint - temp_read)
	temp_out = P * error + I * (error + integral_sum)
	integral_sum = error + integral_sum
	fan_speed = SPEED_PROP * temp_out
	if (fan_speed > FAN_SPEED_MAX):
		fan_speed = FAN_SPEED_MAX
	if (fan_speed < FAN_SPEED_MIN):
		fan_speed = 0
	return None

'''

We use ECO PID for energy saving mode

'''
def ECO_PID(temp_setpoint, temp_read):
	global fan_speed
	global integral_sum
	
	if(integral_sum  > TEMP_MAX):
		integral_sum = TEMP_MAX
	if(integral_sum  < -TEMP_MAX):
		integral_sum = -TEMP_MAX
	error = temp_setpoint - temp_read
	temp_out = P * error + I * (error + integral_sum)
	integral_sum = error + integral_sum
	fan_speed = -SPEED_PROP * temp_out
	if (fan_speed > FAN_SPEED_MAX):
		fan_speed = FAN_SPEED_MAX
	if (fan_speed < FAN_SPEED_MIN):
		fan_speed = 0
	return None
    
def log_logic(device_file):
	global interval
	global sw_window_prev
	global sw_people_prev
	
	time_curr = datetime.datetime.now()
	while(True):
		
		time.sleep(5)
		
		if (read_switch_state(SW_WINDOW) != sw_window_prev):
			file = open('log.txt', 'a')
			file.write('window: ')
			sw_window = str(read_switch_state(SW_WINDOW))
			file.write(sw_window)
			file.write(' , date and time: ')
			file.write(str(datetime.datetime.now()))
			file.write('\n')
			file.close()
			sw_window_prev = read_switch_state(SW_WINDOW)
			
		if (read_switch_state(SW_PEOPLE) != sw_people_prev):
			file = open('log.txt', 'a')
			file.write('people in the room: ')
			sw_people = str(read_switch_state(SW_PEOPLE))
			file.write(sw_people)
			file.write(' , date and time: ')
			file.write(str(datetime.datetime.now()))
			file.write('\n')
			file.close()
			sw_people_prev = read_switch_state(SW_PEOPLE)
			
		if((datetime.datetime.now().hour - time_curr.hour) % 24 == interval and datetime.datetime.now().minute == time_curr.minute and datetime.datetime.now().second == time_curr.second):
			file = open('log.txt', 'a')
			file.write('temperature: ')
			file.write(str(read_temperature(device_file)))
			file.write(' , date and time: ')
			file.write(str(datetime.datetime.now()))
			file.write('\n')
			#file.write('stiglo')
			file.close()
			time_curr = datetime.datetime.now()
			
	
	
def next_state_logic():
	global STATE
	global fan_speed
	global INPUT_ON
	global speed
	global desired_temperature
	
	while(True):
		
		if(read_switch_state(SW_WINDOW) == 0):
			STATE = '5'
		elif(read_switch_state(SW_PEOPLE) == 0):
			STATE = '6'
					
					
			
	
def state_logic(device_file):
	global STATE
	global fan_speed
	global integral_sum
	global INPUT_ON
	global desired_temperature
	while(True):
		INPUT_ON = 1
		match STATE:
			case '1':
				INPUT_ON = 1
				print('\nChoose fan speed: 1 (40%) 2 (70%) 3 (100%) ')
				speed = input()
				match speed:
					case '1':
						fan_speed = 40
					case '2':
						fan_speed = 70
					case '3':
						fan_speed = 100
				STATE = '7'
			case '2':
					temperature = read_temperature(device_file)
					if(temperature >= 20 and temperature <= 24):
						fan_speed = 40
					elif(temperature >= 17 and temperature <= 27):
						fan_speed = 70
					else:
						fan_speed = 100
					STATE = '7'
				
			case '3':
				INPUT_ON = 1
				print('\nInput desired temperature in Celsius: (min. 18C, max. 26C) ')
				desired_temperature = float(input())
				STATE = '4'
			case '4':
				INPUT_ON = 0
				temperature = read_temperature(device_file)
				PID(desired_temperature, temperature)
				
			case '5':
				fan_speed = 0
				integral_sum = 0
				print("WARNING!!! WINDOW OPEN!!! WARNING!!!")
			case '6':
				ECO_PID(26, read_temperature(device_file))
				STATE = '7'
			case '7':
				INPUT_ON = 0
		INPUT_ON = 0



def output_logic(device_file):
	#interval = input("Choose interval for logging: \n")
	global STATE
	global fan_speed
	global INPUT_ON
		
	while(True):
			
		if(INPUT_ON == 0):
			clear = lambda: os.system('clear')
			#clear()
			print('\n\n\n\nFor manual fan speed settings choose 1\nFor automatic fixed fan speed settings choose 2\nFor automatic temperature control choose 3')
			print("Room temperature is: {}".format(read_temperature(device_file)))
			if(read_switch_state(SW_PEOPLE) == 1):
				print("Room is not empty")
			else:
				print("Room is empty")
			if(read_switch_state(SW_WINDOW) == 1):
				print("Window is closed")
			else:
				print("Window is open")
			print("Fan speed is: {}".format(fan_speed))
			
			if read_temperature(device_file) > 30:
				print("WARNING!!! TEMPERATURE IS HIGHER THAN 30C")
			
			if(fan_speed <= 40):
				turn_on_led(PIN1)
				turn_off_led(PIN2)
				turn_off_led(PIN3)
			elif(fan_speed <= 70):
				turn_off_led(PIN1)
				turn_on_led(PIN2)
				turn_off_led(PIN3)
			else:
				turn_off_led(PIN1)
				turn_off_led(PIN2)
				turn_on_led(PIN3)
			time.sleep(3)
 
   
def state():
	global INPUT_ON
	while(True):
		global STATE
		if(INPUT_ON == 0):
			STATE = input()
			INPUT_ON = 1
		
    
    
if __name__ == "__main__":
	device_file = setup_sensor()
    
    
	log_logic = threading.Thread(target = log_logic, args = (device_file,))
	next_state_logic = threading.Thread(target = next_state_logic)
	state_logic = threading.Thread(target = state_logic, args = (device_file,))
	output_logic = threading.Thread(target = output_logic, args = (device_file,))
	state = threading.Thread(target = state)
	
	
	
	log_logic.start();
	next_state_logic.start();
	state_logic.start();
	output_logic.start()
	state.start()
	
	log_logic.join();
	next_state_logic.join();
	state_logic.join();
	output_logic.join()
	state.join()
