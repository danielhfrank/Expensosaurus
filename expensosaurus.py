#!/usr/bin/env python
# encoding: utf-8
"""
expensosaurus.py

Created by Daniel Frank on 2011-06-13.
"""

import sys
import getopt


help_message = '''
File is expected as $name, $amount, $description
Can use # as a comment line'''


class Usage(Exception):
	def __init__(self, msg):
		self.msg = msg


def main(argv=None):
	if argv is None:
		argv = sys.argv
	try:
		# try:
		# 	opts, args = getopt.getopt(argv[1:], "hf:", ["help", "file="])
		# except getopt.error, msg:
		# 	raise Usage(msg)
		# 	
		# # option processing
		# for option, value in opts:
		# 	# if option == "-v":
		# 	# 	verbose = True
		# 	if option in ("-h", "--help"):
		# 		raise Usage(help_message)
		# 	if option == "-f":
		# 		output = value
		
		#Just want the one option basically
		
		filename = sys.argv[1]
		runner = Runner(filename)
		runner.run()
	
	except Usage, err:
		print >> sys.stderr, sys.argv[0].split("/")[-1] + ": " + str(err.msg)
		print >> sys.stderr, "\t for help use --help"
		return 2


#File is expected as $name, $amount, $description
#Can use # as a comment line

import os

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
		return self.ower.name + ' owes ' + self.owed.name + ' ' + str(self.amount)

class Runner:

	def __init__(self, filename):
		self.people = {}
		self.filename = filename


	def run(self):
		f = open(self.filename)
		contents = f.read()
		lines = [ln for ln in contents.split('\n') if not ln.startswith('#')]
		purchases = [self.parse_line(ln) for ln in lines]
		#now we have complete list of purchases. go through each purchase and update the amounts for people
		for purchase in purchases:
			purchase.purchaser.add_amnt(purchase.cost)
		#now our people are updated - pass to a method that will figure out what's owed 
		debts = self.compute_debts(self.people.values())
		for debt in debts:
			print debt.to_string()

	def parse_line(self, line):
		items = line.split(',')
		name = items[0]
		if name not in self.people.keys():
			purchaser = Person(name)
			self.people[purchaser.get_name()] = purchaser
		else:
			purchaser = self.people[purchaser]
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
		print 'total -> ' + str(total)
		print 'avg -> ' + str(avg)
		if(len(people) == 2):
			ower = people[0] if people[0].amount < people[1].amount else people[1]
			owed = people[0] if ower == people[1] else people[1]
			return [Debt(ower, owed, owed.amount - avg)]
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
				return [Debt(owers[x], owed[0], avg - owers[x].amount) for x in range(2)]
			else:
				#1 ower, 2 owed. Ower pays each owed what they deserve
				return [Debt(owers[0], owed[x], owed[x].amount - avg) for x in range(2)]


if __name__ == "__main__":
	sys.exit(main())
