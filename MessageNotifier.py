#to create a virtual display as it is being run headless
# from pyvirtualdisplay import Display
#to control firefox
from selenium import webdriver
#to wait for the page to load
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException
#to be able to kill the created geckodriver and firefox once finished
import os
#for delays
import time
#To connect to wifi
from wireless import Wireless
#Use to turn on GPIO pin and so LED
import wiringpi
from math import log
import threading
import logging
from selenium.webdriver import DesiredCapabilities
import datetime

# Set LED brightness
def led(led_value):
    wiringpi.pwmWrite(LED,led_value)

def LEDControl():
    while(stay):
        if active:
            for i in range(1024, 800, -1):
                led(i)
                time.sleep(log(i + 799)/300)
            for i in range(800, 1024):
                led(i)
                time.sleep(log(i + 799)/300)
        else:
            led(1024)
            time.sleep(1)
    return


def ReadSettings():
    print("trying to copy file from /home/pi/dropoff")
    os.system('mv /home/pi/dropoff/Settings.txt /home/pi/share/Settings.txt')
    time.sleep(1)
    print("Assigning settings to variables")
    #Assigning settings to variables
    with open('/home/pi/share/Settings.txt', 'r') as Settings:
        lines = [line.rstrip('\n') for line in Settings]
    FacebookEmail = lines[4]
    FacebookPassword = lines[7]
    SSID = lines[10]
    WifiPassword = lines[13]
    global nightSleep
    nightSleep = lines[16]
    global beginSleep
    (h, m) = lines[19].split(':')
    beginSleep = int(h) + int(m)/60
    global endSleep
    (h, m) = lines[22].split(':')
    endSleep = int(h) + int(m)/60
    print("SSID " + SSID)
    print("Password " + WifiPassword)
    return SSID, WifiPassword, FacebookEmail, FacebookPassword

def isNowInTimePeriod():

    (h, m) = now.strftime("%H:%M").split(':')
    currentTime = int(h) + int(m)/60

    if beginSleep < endSleep:
        return currentTime >= beginSleep and currentTime <= endSleep
    else: #Over midnight
        return currentTime >= beginSleep or currentTime <= endSleep

def CheckForMessage():
        global active
        MessageCounter = WebDriverWait(browser, 60).until(EC.presence_of_element_located((By.PARTIAL_LINK_TEXT, 'Messages'))).text
        if len(MessageCounter) > 8:
            active = True
        else:
            active = False
        time.sleep(1)
        browser.refresh()

def fb_login():
    desired_capabilities = DesiredCapabilities.PHANTOMJS.copy()
    desired_capabilities['phantomjs.page.customHeaders.User-Agent'] = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_1) ' \
                                                                      'AppleWebKit/537.36 (KHTML, like Gecko) ' \
                                                                      'Chrome/39.0.2171.95 Safari/537.36'

    print("Opening browser")
    global browser
    browser = webdriver.PhantomJS(executable_path='/home/pi/share/phantomjs', desired_capabilities=desired_capabilities)
    browser.set_window_size(1024, 768) # optional
    browser.get('https://mbasic.facebook.com/')
    print("Inserting email " + FacebookEmail)
    browser.save_screenshot('screen.png') # save a screenshot to disk
    user=browser.find_element_by_name('email')
    user.send_keys(FacebookEmail)
    print("Inserting Password")
    password=browser.find_element_by_name('pass')
    password.send_keys(FacebookPassword)
    login=browser.find_element_by_name('login')
    login.click()
    print("Waiting to be logged in")
    #h
    try:
        WebDriverWait(browser, 60).until(EC.presence_of_element_located((By.PARTIAL_LINK_TEXT, 'Not Now'))).click()
    except:
        pass
    browser.find_element_by_partial_link_text('Chat').click()
    try:
        myElem = WebDriverWait(browser, 60).until(EC.presence_of_element_located((By.PARTIAL_LINK_TEXT, 'Turn')))
        print ("Page is ready!")
    except:
        print ("Loading took too much time!")
    browser.find_element_by_partial_link_text('Turn').click()
    browser.find_element_by_partial_link_text('Menu').click()
    try:
        myElem = WebDriverWait(browser, 60).until(EC.presence_of_element_located((By.PARTIAL_LINK_TEXT, 'Messages')))
        print ("Page is ready!")
    except:
        print ("Loading took too much time!")

    if nightSleep:
        while(1):
            if isNowInTimePeriod():
                print("sleeping")
                active = False
                time.sleep(3600)
                browser.refresh()
            else:
                CheckForMessage()
    else:
        while(1):
            CheckForMessage()
    raise NameError("Somehow out of loop")

try:
    #Setup logging
    logger = logging.getLogger('myapp')
    hdlr = logging.FileHandler('/home/pi/share/myapp.txt')
    formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
    hdlr.setFormatter(formatter)
    logger.addHandler(hdlr)
    logger.setLevel(logging.WARNING)

    LED  = 1 # gpio pin 12 = wiringpi no. 1 (BCM 18)

    # Initialize PWM output for LED
    wiringpi.wiringPiSetup()
    wiringpi.pinMode(LED, 2)     # PWM mode
    wiringpi.pwmWrite(LED, 1024)    # OFF

    global stay
    stay = True

    #Set Threading variables
    global active
    active = False
    global LEDThread
    LEDThread = threading.Thread(name='lightThread', target=LEDControl)
    LEDThread.start()

    os.system('cp /home/pi/share/Template_Settings.txt /home/pi/dropoff/')

    now = datetime.datetime.now()

    print("Trying to connect to previous wifi settings")
    #Connect to Wifi
    SSID, WifiPassword, FacebookEmail, FacebookPassword = ReadSettings()
    wireless = Wireless()
    wireless.connect(ssid=SSID, password=WifiPassword)
    time.sleep(3)
    if os.system('ping -c 1 google.com') != 0:
        print("Could not connet to previous wifi")
        print("Checking for Setup Wifi \nSSID: Tardis"
              "\nPassword: Tardis12345")

        #Connect to Wifi
        wireless.connect(ssid='Tardis', password='Tardis12345')
        print("completed wifi Tardis wifi setup")

        #Check if connected
        print("Checking if found the Tardis Setup wifi")
        time.sleep(3)
        disconnected = True
        wiringpi.pwmWrite(LED, 800)    # ON
        tryCounter = 0
        while(disconnected):
            print("Check settings and try Wifi")
            #Connect to Wifi
            if os.path.exists('/home/pi/dropoff/Settings.txt') or tryCounter>2000:
                SSID, WifiPassword, FacebookEmail, FacebookPassword = ReadSettings()
                wireless.connect(ssid=SSID, password=WifiPassword)
                time.sleep(3)
                if os.system('ping -c 1 google.com') != 0:
                    #Connect to Wifi
                    wireless.connect(ssid='Tardis', password='Tardis12345')
                    print("completed wifi Tardis wifi setup")
                    print("Could not connect previous Wifi")
                    print("Trying Again")

                else:
                    print("completed wifi setup")
                    disconnected = False
            time.sleep(1)
        led(1024)
    else:
        print("Connected to wifi")
    os.system('cp /home/pi/share/ConnectionSuccessful.txt /home/pi/dropoff/')
    os.system('sudo ntpdate')

    fb_login()
except:
#   for windows
#   browser.stop()
#   for linux
    stay = False
    print("Closing phantomsjs")
    print(os.system("sudo killall -KILL phantomjs"))
    LEDThread.join()
    logger.exception('')
    os.system('sudo reboot')
