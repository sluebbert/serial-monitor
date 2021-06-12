#!/usr/bin/python

import serial
import signal
import subprocess
import argparse
import json
import re
import unicodedata
import stat
import os
from datetime import datetime
from sys import stdout, stderr
from time import sleep

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

def doesDeviceExist(name):
	try:
		os.stat(name)
		return True
	except FileNotFoundError:
		return False

def pushFormatter(formatters, formatter, index):
	if index in formatters:
		formatters[index].append(formatter)
	else:
		formatters[index] = [formatter]

def handleFormatting(line, regexes):
	formatters = {}

	sweep = 0
	stop = False
	for regex in regexes:
		index = 0
		sweep += 1
		
		while index < len(line):
			match = regex["re"].search(line[index:])
			if match is None:
				break

			start = match.start() + index
			end = match.end() + index
			index = end

			formatter = { 'sweep': sweep, 'regex': regex, 'start': start, 'end': end }

			if len(regex['prefix']) > 0:
				pushFormatter(formatters, formatter, start)
			pushFormatter(formatters, formatter, end)

			if regex['continueOnMatch'] is False:
				stop = True
				break
		
		if stop:
			break
			
	lastFormatterText = ''
	activeFormatters = []
	formattedLine = ''
	for i in range(len(line) + 1):

		if i in formatters:
			formatterText = ''
			formatterList = formatters[i]
			topActiveFormatter = None
			if len(activeFormatters) > 0:
				topActiveFormatter = activeFormatters[-1]

			for formatter in formatterList:
				if formatter['start'] == i:
					if topActiveFormatter is None or topActiveFormatter['sweep'] <= formatter['sweep']:
						activeFormatters.append(formatter)
					if len(formatter['regex']['prefix']) > 0 and (topActiveFormatter is None or topActiveFormatter['sweep'] < formatter['sweep']):
						formatterText = formatter['regex']['prefix']

				if formatter['end'] == i:
					previousTopFormatter = topActiveFormatter
					if formatter in activeFormatters:
						activeFormatters.remove(formatter)
					if len(activeFormatters) > 0:
						topActiveFormatter = activeFormatters[-1]
					else:
						topActiveFormatter = None

					if formatter == previousTopFormatter:
						if len(formatter['regex']['suffix']) > 0:
							formatterText = formatter['regex']['suffix']
						elif formatterText == '':
							if topActiveFormatter is not None and i != len(line):
								formatterText = topActiveFormatter['regex']['prefix']
							else:
								formatterText = clearFormat

			lastFormatterText = formatterText
			formattedLine += formatterText

		if i < len(line):
			c = line[i]
			formattedLine += c

	if len(lastFormatterText) > 0 and lastFormatterText != clearFormat:
		formattedLine += clearFormat

	return formattedLine

def replaceControlChars(match):
	# https://stackoverflow.com/a/13928029
	return r'\x{0:02x}'.format(ord(match.group()))

def getControlCharsRe():
	chars = ''

	for i in range(31):
		if i != 10 and i != 13:
			chars += chr(i)

	return re.compile('[' + chars + ']')

def reset(serialInstance):
	serialInstance.setDTR(False)
	sleep(1)
	serialInstance.flushInput()
	serialInstance.setDTR(True)


def connect(name, baudrate, regexes, showTimestamps, showDeltas, wdreset):
	with serial.Serial(name, baudrate=baudrate, bytesize=serial.EIGHTBITS, parity=serial.PARITY_NONE, stopbits=serial.STOPBITS_ONE, timeout=0.1, xonxoff=0, rtscts=0) as ser:

		stdout.write('Connecting...')
		stdout.flush()

		reset(ser)

		stdout.write(' Done\n\n')

		hiddenRe = getControlCharsRe()

		lastTimestamp = None
		lastChar = '\n'
		lastOutputTime = datetime.now()
		while not unlock:
			line = ser.readline().decode("utf-8", "backslashreplace")
			line = hiddenRe.sub(replaceControlChars, line)

			now = datetime.now()
			if len(line) > 0:
				if lastChar == '\n' and showTimestamps:
					if showDeltas and lastTimestamp is not None:
						timeDiff = now - lastTimestamp
						stdout.write('\033[38;5;237m%s ▲%s: \033[0m' % (str(now), str(timeDiff)))
					else:	
						stdout.write('\033[38;5;237m%s: \033[0m' % str(now))
					lastTimestamp = now

				line = handleFormatting(line, regexes)
				stdout.write(line + clearFormat)
				lastChar = line[-1]
				stdout.flush()
				lastOutputTime = datetime.now()

			wdTimeDiff = now - lastOutputTime
			if wdreset is not None and wdTimeDiff.total_seconds() >= wdreset:
				print('\nResetting due to timeout waiting on output (%s)\n' % (str(wdTimeDiff)))
				lastOutputTime = datetime.now()
				reset(ser)
				lastTimestamp = None

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
					"suffix": record["suffix"].replace("\\033", "\033") if "suffix" in record else '',
					"continueOnMatch": record["continueOnMatch"] if "continueOnMatch" in record else True
				})
	except Exception as err:
		printError("An error occurred while parsing the provided json file: " + str(err))
		return None

	return regexes

def main(name, baudrate, regexesPath, showTimestamps, showDeltas, unlockSleepAmount, wdreset, signalValue):
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
			try:
				if isDeviceAvailable(name):
					connect(name, baudrate, regexes, showTimestamps, showDeltas, wdreset)
					if unlock:
						print('\nUnlocked due to request.')
						sleep(unlockSleepAmount)
						unlock = False
				else:
					print('Waiting for device to be available...')
					while not isDeviceAvailable(name):
						sleep(1)
			except serial.serialutil.SerialException as e:
				if 'device disconnected' not in str(e):
					raise

				print('\nLost connection.')
				print('Waiting for device to be available...')
				while not doesDeviceExist(name):
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
	parser.add_argument('-d', '--deltas', action='store_true', help='Display deltas in back to back timestamps.')
	parser.add_argument('--wdreset', type=float, default=None, help='The amount of seconds to wait for output before auto resetting the device.')
	args = parser.parse_args()

	signalValue = signal.Signals[args.signal]
	main(args.name, args.baudrate, args.regexes, args.timestamps, args.deltas, args.wait, args.wdreset, signalValue)
