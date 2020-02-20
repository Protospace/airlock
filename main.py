import logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO)

from multiprocessing import Process, Queue
from queue import Empty
import time

RELAY_PIN = 17
RFID_EN_PIN = 27
CARDS_FILE = 'card_data.json'
OPEN_DURATION = 4

ser = None

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

def unlock_door():
    GPIO.output(RELAY_PIN, GPIO.HIGH)
    GPIO.output(RFID_EN_PIN, GPIO.HIGH)

    time.sleep(OPEN_DURATION)

    GPIO.output(RELAY_PIN, GPIO.LOW)
    GPIO.output(RFID_EN_PIN, GPIO.LOW)

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

        card = card.decode().strip()
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

def update_thread(card_data_queue):
    while True:
        pass


if __name__ == '__main__':
    logging.info('Initializing...')
    init()

    card_data = Queue()

    Process(target=reader_thread, args=(card_data,)).start()
    Process(target=update_thread, args=(card_data,)).start()
