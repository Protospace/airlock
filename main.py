import logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO)

from multiprocessing import Process, Queue
from queue import Empty
import RPi.GPIO as GPIO
import os
import json
import requests
import serial
import time
from signal import *

import secrets

DEBUG = os.environ.get('DEBUG', False)

RELAY_PIN = 17
RFID_EN_PIN = 27
CARDS_FILE = 'card_data.json'
OPEN_DURATION = 4

API_STATS = 'https://api.my.protospace.ca/stats/'
API_DOOR = 'https://api.my.protospace.ca/door/'
API_SEEN = lambda x: 'https://api.my.protospace.ca/door/{}/seen/'.format(x)

ser = None

def unlock_door():
    GPIO.output(RELAY_PIN, GPIO.HIGH)
    GPIO.output(RFID_EN_PIN, GPIO.HIGH)

    time.sleep(OPEN_DURATION)

    GPIO.output(RELAY_PIN, GPIO.LOW)
    GPIO.output(RFID_EN_PIN, GPIO.LOW)

def lock_door_on_exit(*args):
    logging.info('Exiting, locking door...')
    GPIO.output(RELAY_PIN, GPIO.LOW)
    GPIO.output(RFID_EN_PIN, GPIO.LOW)
    os._exit(0)

def init():
    global ser, cards

    GPIO.setwarnings(False)
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(RELAY_PIN, GPIO.OUT)
    GPIO.output(RELAY_PIN, GPIO.LOW)
    GPIO.setup(RFID_EN_PIN, GPIO.OUT)
    GPIO.output(RFID_EN_PIN, GPIO.LOW)
    logging.info('GPIO initialized')

    ser = serial.Serial(port='/dev/ttyAMA0', baudrate=2400, timeout=0.1)
    logging.info('Serial initialized')

    for sig in (SIGABRT, SIGILL, SIGINT, SIGSEGV, SIGTERM):
        signal(sig, lock_door_on_exit)
    logging.info('Signals initialized')

def reader_thread(card_data_queue):
    recent_scans = {}

    with open(CARDS_FILE, 'r') as f:
        card_data = json.load(f)
    logging.info('Read {} card numbers from disk'.format(str(len(card_data))))

    while True:
        try:
            card_data = card_data_queue.get_nowait()
        except Empty:
            pass

        card = ser.readline()
        if not card: continue

        try:
            card = card.decode().strip()
        except UnicodeDecodeError:
            continue

        if len(card) != 10: continue

        # debounce card scans
        now = time.time()
        if card in recent_scans:
            if now - recent_scans[card] < 5.0:
                continue
        recent_scans[card] = now

        logging.info('Read card: ' + card)

        if card in card_data:
            logging.info('Card recognized')
        else:
            logging.info('Card not recognized, denying access')
            continue

        logging.info('DOOR ACCESS - Card: {} | Name: {}'.format(
            card, card_data[card],
        ))

        unlock_door()

        try:
            res = requests.post(API_SEEN(card), timeout=2)
            res.raise_for_status()
        except BaseException as e:
            logging.error('Problem POSTing seen: {} - {}'.format(e.__class__.__name__, str(e)))
            continue

def update_thread(card_data_queue):
    last_card_change = None

    while True:
        time.sleep(5)

        try:
            res = requests.get(API_STATS, timeout=5)
            res.raise_for_status()
            res = res.json()
        except BaseException as e:
            logging.error('Problem GETting stats: {} - {}'.format(e.__class__.__name__, str(e)))
            continue

        if res['last_card_change'] == last_card_change:
            continue
        last_card_change = res['last_card_change']

        logging.info('Cards changed, pulling update from API')

        try:
            headers = {'Authorization': 'Bearer ' + secrets.DOOR_API_KEY}
            res = requests.get(API_DOOR, headers=headers, timeout=5)
            res.raise_for_status()
            res = res.json()
        except BaseException as e:
            logging.error('Problem GETting door: {} - {}'.format(e.__class__.__name__, str(e)))
            last_card_change = None
            continue

        logging.info('Got {} cards from API'.format(str(len(res))))
        card_data_queue.put(res)

        logging.info('Writing data to file')
        with open(CARDS_FILE, 'w') as f:
            json.dump(res, f)

def watchdog_thread():
    while True:
        with open('/dev/watchdog', 'w') as wdt:
            wdt.write('1')
        time.sleep(1)

if __name__ == '__main__':
    logging.info('Initializing...')
    init()

    card_data = Queue()

    Process(target=reader_thread, args=(card_data,)).start()
    Process(target=update_thread, args=(card_data,)).start()
    if not DEBUG: Process(target=watchdog_thread).start()
