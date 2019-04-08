#!/usr/bin/python

import serial
import signal
import subprocess
import argparse
import json
import re
import unicodedata
from datetime import datetime
from sys import stdout, stderr
from time import sleep

printable = set(('Lu', 'Ll'))
formatRe = re.compile('(\033[^m]+m)')
unlock = False
clearFormat = '\033[0m'

def printError(message):
	stderr.write("\033[38;5;9m" + message + "\033[0m\n\n")

def userSignalHandler(sig, frame):
	global unlock
	unlock = True

def isDeviceAvailable(name):
	result = subprocess.run(['fuser', name], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
	return result.returncode == 1

def handleFormatting(line, regexes):
	for regex in regexes:
		index = 0
		while index < len(line):
			match = regex["re"].search(line[index:])
			if match is None:
				break
			else:
				start = match.start() + index
				end = match.end() + index
				index = end

				formattingMatches = [x for x in formatRe.finditer(line)]

				mostRecentFormatter = None
				foundInFormatter = False
				for formatterMatch in formattingMatches:
					if (start >= formatterMatch.start() and start < formatterMatch.end()) or (end >= formatterMatch.start() and end < formatterMatch.end()):
						foundInFormatter = True

					if formatterMatch.start() <= start:
						mostRecentFormatter = formatterMatch

				if not foundInFormatter:
					line = line[:start] + regex['prefix'] + match[0] + regex['suffix'] + (mostRecentFormatter[0] if mostRecentFormatter is not None else clearFormat) + line[end:]

	return line

def replaceControlChars(match):
	# https://stackoverflow.com/a/13928029
	return r'\x{0:02x}'.format(ord(match.group()))

def getControlCharsRe():
	chars = ''

	for i in range(31):
		if i != 10 and i != 13:
			chars += chr(i)

	return re.compile('[' + chars + ']')

def connect(name, baudrate, regexes, showTimestamps):
	with serial.Serial(name, baudrate=baudrate, bytesize=serial.EIGHTBITS, parity=serial.PARITY_NONE, stopbits=serial.STOPBITS_ONE, timeout=1, xonxoff=0, rtscts=0) as ser:

		stdout.write('Connecting...')
		stdout.flush()

		ser.setDTR(False)
		sleep(1)
		ser.flushInput()
		ser.setDTR(True)

		stdout.write(' Done\n\n')

		hiddenRe = getControlCharsRe()

		lastChar = '\n'
		while not unlock:
			line = ser.readline().decode("utf-8", "backslashreplace")
			line = hiddenRe.sub(replaceControlChars, line)

			if len(line) > 0:
				if lastChar == '\n' and showTimestamps:
					stdout.write('\033[38;5;237m%s: \033[0m' % str(datetime.now()))

				line = handleFormatting(line, regexes)
				stdout.write(line + clearFormat)
				lastChar = line[-1]
				stdout.flush();

def getRegexes(path):
	regexes = []

	try:
		with open(path, 'r') as f:
			content = json.load(f)

			for record in content:
				flags = 0
				if 'flags' in record:
					recordFlags = record['flags'].lower()
					if 'i' in recordFlags:
						flags |= re.I
					if 'a' in recordFlags:
						flags |= re.A
					if 'l' in recordFlags:
						flags |= re.L
					if 'm' in recordFlags:
						flags |= re.M
					if 's' in recordFlags:
						flags |= re.S
					if 'x' in recordFlags:
						flags |= re.X

				regexes.append({
					"re": re.compile(record["pattern"], flags),
					"prefix": record["prefix"].replace("\\033", "\033") if "prefix" in record else '',
					"suffix": record["suffix"].replace("\\033", "\033") if "suffix" in record else ''
				})
	except Exception as err:
		printError("An error occurred while parsing the provided json file: " + str(err))
		return None

	return regexes

def main(name, baudrate, regexesPath, showTimestamps, unlockSleepAmount, signalValue):
	global unlock

	regexes = []
	if regexesPath is not None:
		regexes = getRegexes(regexesPath)
		if regexes is None:
			return

	signal.signal(signalValue, userSignalHandler)

	print(f'Name: {name}')
	print(f'Baudrate: {baudrate}')
	print(f'Signal: {signalValue.name}')
	print()

	try:
		while True:
			if isDeviceAvailable(name):
				connect(name, baudrate, regexes, showTimestamps)
				if unlock:
					print('\nUnlocked due to request.')
					sleep(unlockSleepAmount)
					unlock = False
			else:
				print('Waiting for device to be available...')
				while not isDeviceAvailable(name):
					sleep(1)

	except KeyboardInterrupt:
		print('Exiting')


if __name__ == '__main__':
	parser = argparse.ArgumentParser(description='Monitors serial activity.', formatter_class=argparse.ArgumentDefaultsHelpFormatter)
	parser.add_argument('name', help='The device to connect to.')
	parser.add_argument('-b', '--baudrate', type=int, default=9600, help='The baudrate to use.')
	parser.add_argument('-r', '--regexes', help='The json file containing regexes to use for style highlighting.')
	parser.add_argument('-w', '--wait', type=float, default=5, help='The amount of seconds to unlock and sleep / wait for before retrying to connect when requested to disconnect.')
	parser.add_argument('-s', '--signal', default='SIGUSR1', help='The signal to listen to that will trigger a temporary disconnect.')
	parser.add_argument('-t', '--timestamps', action='store_true', help='Display timestamps before each new line received.')
	args = parser.parse_args()

	signalValue = signal.Signals[args.signal]
	main(args.name, args.baudrate, args.regexes, args.timestamps, args.wait, signalValue)
