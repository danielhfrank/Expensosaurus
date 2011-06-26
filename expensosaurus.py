#!/usr/bin/env python
# encoding: utf-8
"""
expensosaurus.py

Created by Daniel Frank on 2011-06-13.
"""

import smtplib
from email.MIMEMultipart import MIMEMultipart
from email.MIMEBase import MIMEBase
from email.MIMEText import MIMEText
from email import Encoders

import sys
import getopt
import time
import os
import yaml


help_message = '''
File is expected as $name, $amount, $description
Can use # as a comment line

Cmd line usage: first, run -s or --setup : 1 config file - this will create necessary dirs. 
Assumes that expenses file does not exist yet! Will make sure to make a new one, so we never hit that error
Then can run with a list of config files as the only args
'''

TEST = True

settings = {}

class Usage(Exception):
	def __init__(self, msg):
		self.msg = msg


def main(argv=None):
	if argv is None:
		argv = sys.argv
	try:
		try:
			opts, args = getopt.getopt(argv[1:], "hs:", ["help", "setup="])
		except getopt.error, msg:
			raise Usage(msg)
			
		setup_file = None
		# option processing
		for option, value in opts:
			# if option == "-v":
			# 	verbose = True
			if option in ("-h", "--help"):
				raise Usage(help_message)
			if option in ('-s', '--setup'):
				setup_file = value
		
		if setup_file is not None:
			settings_dict = yaml.load(open(setup_file, 'r'))
			sys.exit(setup(settings_dict))
		
		#Just want the one option basically
		
		if TEST and len(argv) < 2:
			argv = [argv[0], '/Users/dan/Dropbox/Scripts/expensosaurus/settings.yaml']
		
		settings_files = argv[1:]
		
		for settings_file in settings_files:
			#load the settings.
			settings = yaml.load(open(settings_file, 'r'))
			# print settings
			# sys.exit(1)
		
			runner = Runner(settings)
			runner.run()
	
	except Usage, err:
		print >> sys.stderr, sys.argv[0].split("/")[-1] + ": " + str(err.msg)
		print >> sys.stderr, "\t for help use --help"
		return 2

def setup(settings_dict):
	os.mkdir(settings_dict['archive_dir'])
	tmp = open(settings_dict['expense_file'], 'a')
	tmp.write('')
	tmp.close()

#File is expected as $name, $amount, $description
#Can use # as a comment line


class Purchase:

	def __init__(self, purchaser, cost, description=''):
		self.purchaser = purchaser
		self.cost = float(cost)
		self.description = description


class Person:

	def __init__(self, name):
		self.name = name
		self.amount = 0.0

	def add_amnt(self, amnt):
		self.amount += amnt

	def get_name(self):
		return self.name

class Debt:

	def __init__(self, ower, owed, amount):
		self.ower = ower
		self.owed = owed
		self.amount = float(amount)

	def to_string(self):
		return '%s owes %s $%.2f' % (self.ower.name, self.owed.name, self.amount)
		# return self.ower.name + ' owes ' + self.owed.name + ' ' + str(self.amount)

class Runner:

	def __init__(self, settings):
		self.people = {}
		for name in settings['names']:
			self.people[name] = Person(name)
		self.filename = settings['expense_file']
		self.settings = settings


	def run(self):
		f = open(self.filename)
		contents = f.read()
		lines = [ln for ln in contents.split('\n') if len(ln) > 5 and not ln.startswith('#')]
		purchases = [self.parse_line(ln) for ln in lines]
		#now we have complete list of purchases. go through each purchase and update the amounts for people
		for purchase in purchases:
			purchase.purchaser.add_amnt(purchase.cost)
		#now our people are updated - pass to a method that will figure out what's owed 
		total, avg, debts = self.compute_debts(self.people.values())
		contents += '\n'
		contents += 'Total: %s\n' % total
		contents += 'Avg per person: %.2f\n' % avg
		contents += '\n'
		for debt in debts:
			contents += debt.to_string() + '\n'
		date_str = time.strftime("%b %Y")
		self.save_content(date_str + '.txt', contents)
		if not TEST:
			pass#delete the old file, and create a new one
		# self.email_content('%s Expense Report for %s' % (self.settings['name'],date_str), contents) 
		print contents
		

	def parse_line(self, line):
		items = [x.strip() for x in line.split(',', 2)]
		if len(items) is not 3:
			raise Exception('Line could not be parsed, too few items: %s' % line)
		print('processing ' + str(items))
		name = items[0]
		if name not in self.people.keys():
			purchaser = Person(name)
			self.people[purchaser.get_name()] = purchaser
		else:
			purchaser = self.people[name]
		cost = items[1]
		description = items[2]
		return Purchase(purchaser, cost, description)

	def compute_debts(self,people):
		#Should return a list of Debts
		if(len(people) > 3):
			#this shit ain't implemented yet!
			print 'FAIL - too many people!'
			sys.exit(1)
		if(len(people) < 2):
			#this shit doesn't make sense
			print 'FAIL - less than 2 people, makes no sense'
			sys.exit(1)
		total = sum(person.amount for person in people)
		avg = total/float(len(people))
		if(len(people) == 2):
			ower = people[0] if people[0].amount < people[1].amount else people[1]
			owed = people[0] if ower == people[1] else people[1]
			debts = [Debt(ower, owed, owed.amount - avg)]
		else:#this must mean there are 3 people
			owers = []
			owed = []
			for person in people:
				if person.amount < avg:
					owers.append(person)
				else:
					owed.append(person)
			if(len(owers) > len(owed)):
				#2 owers, 1 owed. so each ower pays what they owe, and owed gets it all
				debts =  [Debt(owers[x], owed[0], avg - owers[x].amount) for x in range(2)]
			else:
				#1 ower, 2 owed. Ower pays each owed what they deserve
				debts = [Debt(owers[0], owed[x], owed[x].amount - avg) for x in range(2)]
		return total, avg, debts
		
	def email_content(self, subject, text):
		msg = MIMEMultipart()
		msg['From'] = self.settings['email']
		msg['To'] = ','.join(self.settings['recipients'])
		msg['Subject'] = subject
		
		msg.attach(MIMEText(text))
			
		server = smtplib.SMTP('smtp.gmail.com',587)
		server.ehlo()  
		server.starttls()
		server.ehlo()
		server.login(self.settings['email'], self.settings['pw'])
		response = server.sendmail(self.settings['email'],
				self.settings['recipients'],
				msg.as_string())
		if len(response) != 0:
			print 'Possibly some trouble with emailing: %s' % response
		server.close()

	def save_content(self, title, content):
		date_str = time.strftime("%b %Y") 
		f = open(self.settings['archive_dir'] + '/' + title, 'w')
		content = ('%s Expense Report for %s' % (self.settings['name'],date_str)) + content
		f.write(content)
		f.close

if __name__ == "__main__":
	sys.exit(main())
