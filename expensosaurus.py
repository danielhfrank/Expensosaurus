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

TEST = False

settings = {}

class Usage(Exception):
	def __init__(self, msg):
		self.msg = msg


def main(argv=None):
	if argv is None:
		argv = sys.argv
	try:
		try:
			opts, args = getopt.getopt(argv[1:], "hls:", ["help", "lite", "setup="])
		except getopt.error, msg:
			raise Usage(msg)
			
		setup_file = None
		lite = False
		# option processing
		for option, value in opts:
			# if option == "-v":
			# 	verbose = True
			if option in ("-h", "--help"):
				raise Usage(help_message)
	        if option in ('-s', '--setup'):
				setup_file = value
            if option in ('l', '--lite'):
                lite = True
		
		if setup_file is not None:
			settings_dict = yaml.load(open(setup_file, 'r'))
			sys.exit(setup(settings_dict))
		
		#Just want the one option basically
		
		if TEST and len(argv) < 2:
			argv = [argv[0], '/Users/dan/Dropbox/Scripts/expensosaurus/settings.yaml']
		
        if lite:
            Runner(None, True).run()
            sys.exit(0)
        
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
		
	def __cmp__(self, other):
		return self.amount - other.amount

class Debt:

	def __init__(self, ower, owed, amount):
		self.ower = ower
		self.owed = owed
		self.amount = float(amount)

	def to_string(self):
		return '%s owes %s $%.2f' % (self.ower.name, self.owed.name, self.amount)
		# return self.ower.name + ' owes ' + self.owed.name + ' ' + str(self.amount)

class Runner:

	def __init__(self, settings, lite=False):
		self.people = {}
        if not lite:
		    for name in settings['names']:
			    self.people[name] = Person(name)
		    self.filename = settings['expense_file']
		    self.settings = settings
        self.lite = lite


	def run(self):
		expenses = open(self.filename, 'r') if not self.lite else sys.stdin
		lines = [ln for ln in expenses if len(ln) > 5 and not ln.startswith('#')]
        if not lite:
            expenses.close()
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
		if not (TEST or self.lite):
            self.save_content(date_str + '.txt', contents)
			open(self.filename, 'w').write('')#delete old file and create a new one
		    self.email_content('%s Expense Report for %s' % (self.settings['name'],date_str), contents) 
		print contents
		

	def parse_line(self, line):
		items = [x.strip() for x in line.split(',', 2)]
		if len(items) is not 3:
			raise Exception('Line could not be parsed, too few items: %s' % line)
        if not self.lite:
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
		
	
	def compute_debts(self, people):
		total = sum(person.amount for person in people)
		avg = total/float(len(people))
		debts = []
		def pop(peoples, avg):
			#sort, and get people who owe / are owed the most
			peoples.sort()
			ower = peoples[0]
			owed = peoples[-1]
			amnt = min(avg - ower.amount, owed.amount - avg)#greatest amount that can be paid - one person will become square
			debt = Debt(ower, owed, amnt)
			ower.amount += amnt #because ower is now paying out this much more
			owed.amount -= amnt #because is being paid this, to cover part of debt
			if ower.amount == avg:
				peoples.remove(ower)
			elif owed.amount == avg:
				peoples.remove(owed)
			else:
				raise Exception('Your math sucks, nobody is square after transaction')
			return debt, peoples
		import copy
		ppl = copy.copy(people)
		while len(ppl) > 1:
			debt, ppl = pop(ppl, avg)
			debts.append(debt)
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
		content = ('%s Expense Report for %s\n\n' % (self.settings['name'],date_str)) + content
		f.write(content)
		f.close
            

if __name__ == "__main__":
	sys.exit(main())
