import os
import glob
import time
import RPi.GPIO as GPIO
import threading
import datetime

interval = 1

STATE = ''

PIN1 = 17
PIN2 = 27
PIN3 = 22

SW_WINDOW = 23
SW_PEOPLE = 24

INPUT_ON = 0

TEMP_MAX = 32
TEMP_MIN = 18

P = 0.1
I = 0.1
SPEED_PROP = 1
integral_sum = 0
fan_speed = 0
FAN_SPEED_MAX = 100
FAN_SPEED_MIN = 0

'''
    Senzor temperature
    Koriscenje: 
        1) pozvati sensor = setup_sensor()
        2) pozvati temperatura = read_temperature(sensor)
'''
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
    LED
    Ukljuci LED: turn_on_led(LED_koji_se_ukljucuje)
    Ugasi LED: turn_off_led(LED_koji_se_gasi)
    LED1 je na Pinu 17 ukoliko je dobro povezano
    LED2 je na Pinu 27 ukoliko je dobro povezano
    LED3 je na Pinu 22 ukoliko je dobro povezano
    
    Pinovi u programu se razlikuju po oznaci od onih na raspberry plocici
'''
def turn_on_led(pin):
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(pin, GPIO.OUT)
    GPIO.output(pin, GPIO.HIGH)

def turn_off_led(pin):
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(pin, GPIO.OUT)
    GPIO.output(pin, GPIO.LOW)




'''
    Perkidaci
    Procitaj stanje prekidaca: stajne_prekidaca = read_switch_state(prekidac)
    Prekidac1 je na pinu 23 ukoliko je dobro povezano
    Prekidac2 je na pinu 24 ukoliko je dobro povezano
    
    Pinovi u programu se razlikuju po oznaci od onih na raspberry plocici
'''
def read_switch_state(pin):
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)  
    return GPIO.input(pin)
    
def log_info():
	print("logovano")
	
	
''' Funkcija za implementaciju PID regulatora
	Prima kao argumente zeljenu temperaturu od strane korisnika, integralnu sumu od ranijih izvrsavanja i procitanu temperaturu sa senzora
'''	
def ECO_PID(temp_setpoint, temp_read):
	global fan_speed
	global integral_sum
	
	if(integral_sum  > TEMP_MAX):
		integral_sum = TEMP_MAX
	if(integral_sum  < -TEMP_MAX):
		integral_sum = -TEMP_MAX
	error = temp_setpoint - temp_read
	temp_out = 10 * error + 0.5 * (error + integral_sum)
	integral_sum = error + integral_sum
	fan_speed = -SPEED_PROP * temp_out
	if (fan_speed > FAN_SPEED_MAX):
		fan_speed = FAN_SPEED_MAX
	if (fan_speed < FAN_SPEED_MIN):
		fan_speed = 0
	return None
	
def PID(temp_setpoint, temp_read):
	global fan_speed
	global integral_sum
	
	if(integral_sum  > TEMP_MAX):
		integral_sum = TEMP_MAX
	if(integral_sum  < -TEMP_MAX):
		integral_sum = -TEMP_MAX
	error = abs(temp_setpoint - temp_read)
	temp_out = 10 * error + 0.5 * (error + integral_sum)
	integral_sum = error + integral_sum
	fan_speed = SPEED_PROP * temp_out
	if (fan_speed > FAN_SPEED_MAX):
		fan_speed = FAN_SPEED_MAX
	if (fan_speed < FAN_SPEED_MIN):
		fan_speed = 0
	return None
	
''' Loguje temperaturu u fajl log.txt na svakih n sati (n = interval)   '''	

def logTemperature(device_file):
	global interval
	time = datetime.datetime.now()
	while(True):
		if((datetime.datetime.now().hour - time.hour) % 24 == interval and datetime.datetime.now().minute == time.minute and datetime.datetime.now().second == time.second):
			file = open('log.txt', 'a')
			file.write('temperature: ')
			temp = str(read_temperature(device_file))
			file.write(temp)
			file.write(' , date and time: ')
			file.write(str(datetime.datetime.now()))
			file.write('\n')
			#file.write('stiglo')
			file.close()
			time = datetime.datetime.now()

def analogIO(device_file):
	global fan_speed
	global integral_sum
	global STATE
	global INPUT_ON
	while(True):
		if(read_switch_state(SW_WINDOW) == 0):
			fan_speed = 0
			integral_sum = 0
			turn_off_led(PIN1)
			turn_off_led(PIN2)
			turn_off_led(PIN3)
		elif(read_switch_state(SW_PEOPLE) == 0):
			ECO_PID(26, read_temperature(device_file))
			#vrattii se na ovo
		else:
			
			STATE = input()
			match STATE:
				case '1':
					INPUT_ON = 1
					print('\nChoose fan speed: 1 (40%) 2 (70%) 3 (100%) ')
					speed = input()
					match speed:
						case '1':
							fan_speed = 40
							turn_on_led(PIN1)
							turn_off_led(PIN2)
							turn_off_led(PIN3)
						case '2':
							fan_speed = 70
							turn_off_led(PIN1)
							turn_on_led(PIN2)
							turn_off_led(PIN3)
						case '3':
							fan_speed = 100
							turn_off_led(PIN1)
							turn_off_led(PIN2)
							turn_on_led(PIN3)
					STATE = ''
					INPUT_ON = 0
				case '2':
					temperature = read_temperature(device_file)
					if(temperature >= 20 and temperature <= 24):
						fan_speed = 40
						turn_on_led(PIN1)
						turn_off_led(PIN2)
						turn_off_led(PIN3)
					elif(temperature >= 17 and temperature <= 27):
						fan_speed = 70
						turn_off_led(PIN1)
						turn_on_led(PIN2)
						turn_off_led(PIN3)
					else:
						fan_speed = 100
						turn_off_led(PIN1)
						turn_off_led(PIN2)
						turn_on_led(PIN3)
					STATE = ''
				case '3':
					INPUT_ON = 1
					print('\nInput desired temperature in Celsius: (min. 18C, max. 26C) ')
					desired_temperature = float(input())
					temperature = read_temperature(device_file)
					PID(desired_temperature, temperature)
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
					STATE = ''
					INPUT_ON = 0
										
	
def userInterface(device_file):
	global STATE
	global fan_speed
	global INPUT_ON
	while(True):
		#STATE = input()
		#time.sleep(6)
		
		clear = lambda: os.system('clear')
		if(INPUT_ON == 0):
			clear()
			print('Choose work state: MANUAL, AUTO_FIXED OR AUTO_PID')
			print(read_temperature(device_file))
			print(read_switch_state(SW_PEOPLE))
			print(read_switch_state(SW_WINDOW))
			print(fan_speed)
			time.sleep(3)
		
		
    
if __name__ == "__main__":
	device_file = setup_sensor()
    
    
	logTemp = threading.Thread(target = logTemperature, args = (device_file,))
	analogIO = threading.Thread(target = analogIO, args = (device_file,))
	ui = threading.Thread(target = userInterface, args = (device_file,))
	
	
	
	logTemp.start();
	analogIO.start();
	ui.start();
	
	logTemp.join()
	analogIO.join()
	ui.join()







