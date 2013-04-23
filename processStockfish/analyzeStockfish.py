#!/bin/python
# -*- coding: utf-8 -*-

import pgn
from subprocess import *
import select
import time
import sys, getopt

def cleanmove(move):
	if move[-1]=='+':
		move = move[0:-1]
	return move
	
def analyzeMove(stockfish,move_type,white_turn,depth,fromdepth):
	#score = None
	score_array = [None]*(depth-fromdepth+1)
	
	# First, check that move is not checkmate
	if move_type[-1]=="#":
		for i in range(fromdepth,depth+1):
			score_array[i-fromdepth] = -99999
	else:
		# Send move_type to stockfish
		cmd = "position moves " + str(move_type) + "\n"
		stockfish.stdin.write(cmd)
		#print cmd

		# Start analysis
		cmd = "go depth " + str(depth) + "\n"
		stockfish.stdin.write(cmd)
		#print cmd

		# Search score in analysis
		search_string = "info depth " #+str(depth)+" score "
		end_string = "bestmove"
		line = ''
		while not end_string in line:
			line = stockfish.stdout.readline()
			#print str(line)
			
			# If line includes "lowerbound" or "upperbound", skip it.
			# If line includes "mate", then score is 999 or -999
			if search_string in line and "score" in line and not "mate" in line and not "lowerbound" in line and not "upperbound" in line:
				line = line.split()
				line_depth = int(line[2])
				if line_depth>=fromdepth:
					line_score = line[line.index("score")+2]
					#print line
					#print line_score
					#print "line_depth="+str(line_depth)
					#print "fromdepth="+str(fromdepth)
					score_array[line_depth-fromdepth] = int(line_score)
					#print str(line)

			if search_string in line and "mate" in line:
				line = line.split()
				line_depth = int(line[2])
				if line_depth>=fromdepth:
					if (int(line[line.index("mate")+1])<0): sign = -1
					else: sign = 1
					for i in range(line_depth,depth+1):
						score_array[i-fromdepth] = 99999*sign
					#line = end_string
					#print "Detected mate: " + str(score_array)
				else:
					if (int(line[line.index("mate")+1])<0): sign = -1
					else: sign = 1
					for i in range(fromdepth,depth+1):
						score_array[i-fromdepth] = 99999*sign
					#print str(line)
					#line = end_string


			if "Segmentation" in line:
				print line
				exit(0)
			#print str(line)
	
	if not white_turn:
		for i in range(fromdepth,depth+1):
			if score_array[i-fromdepth]!=None:
				score_array[i-fromdepth] = -int(score_array[i-fromdepth])

	#print '--- Score: ' + str(score_array)
	return score_array

def analyzeGame(pgntext,depth,fromdepth):
	start_ag = time.time()

	# *********** Convert SAN format to Long Algebraic ************
	pgn_extract = Popen(["pgn-extract", "-Wlalg","-C","-N","--notags","--noresults","--nomovenumbers"],bufsize=0,stdin=PIPE, stdout=PIPE,stderr=STDOUT, shell=False)
	pgn_extract.stdin.write(pgntext)
	
	pgn_splitted = pgntext.split()
	#end_code = str(pgn_splitted[pgn_splitted.index('[EndCode')+1].strip('"]'))
	
	moves_alg = pgn_extract.communicate()[0].split("\n")
	moves = " ".join(moves_alg[3:-1]).split()
	#print " ".join(moves)

	end_pgnExtract = time.time()

	## ************ Start Stockfish ************
	stockfish = Popen("./stockfish.out",bufsize=0,stdin=PIPE, stdout=PIPE,stderr=STDOUT, universal_newlines=True,shell=False)
	# Set uci interface
	cmd = "uci\n"
	stockfish.stdin.write(cmd)
	#print "SENDING COMMAND:  " + str(cmd)

	# Check for initialization
	line=''
	while not "uciok" in line:
		line = stockfish.stdout.readline()
		
	# Set analyse mode in stockfish
	cmd = "setoption name UCI_AnalyseMode value true\n"
	stockfish.stdin.write(cmd)
	#print "SENDING COMMAND:  " + str(cmd)

	# Start new game
	cmd = "ucinewgame\n"
	stockfish.stdin.write(cmd)
	#print "SENDING COMMAND:  " + str(cmd)

	end_fork = time.time()

	## *********** Analyse game ***********
	scores =[]
	score_array = [None]*(depth-fromdepth+1)
	# Start with black turns (white has already moved the first ply.
	white_turn = False
	# For each move, run stockfish analyzer...
	for i in range(len(moves)):
		move = moves[i]
		#print 'Analysing move ' + str(move)
		
		# If this is the last move, check the end_code. If it is "Sta" then score = 0
		if (i==len(moves)-1) and (('drawn' in pgntext) or ('Neither player' in pgntext)): 
			for i in range(fromdepth,depth+1):
				score_array[i-fromdepth] = 0
		else: 
			score_array = analyzeMove(stockfish,move,white_turn,depth,fromdepth)
		
		scores = scores + [[str(move), score_array]]
		white_turn = not white_turn
		
	# Quit stockfish
	cmd = "quit\n"
	stockfish.stdin.write(cmd)
	stockfish.communicate()

	end_analysis = time.time()
	#print 'Time control: PGN_EXTRACT='+str(end_pgnExtract-start_ag)+' --- STOCKFISH_FORK='+str(end_fork-end_pgnExtract)+' --- ANALYSIS='+str(end_analysis-end_fork) 


	return scores
	
if __name__ == "__main__":
	fileName = "prueba2.pgn"
	depth = 8

	# Check command-line arguments. If no argument is provided, just run the test file.
	try:
		opts, args = getopt.getopt(sys.argv[1:], "d:f:m:", ["depth","file","fromdepth"])
	except getopt.GetoptError, err:
		# print help information and exit:
		print str(err) # will print something like "option -a not recognized"
		usage()
		sys.exit(2)
	
	for o, a in opts:
		if o in ("-d", "--depth"):
			depth = int(a)
		elif o in ("-f", "--file"):
			fileName = a
		elif o in ("-m", "--fromdepth"):
			fromdepth = int(a)
		else:
			assert False, "unhandled option"
	#output = None
	#if len(sys.argv)>1:
		#fileName = sys.argv[1]
	#else:
		
	# Open PGN file
	f = open(fileName,'r')
	pgntext = f.read()
	f.close()
	
	# Send it to analyzer.
	scores = analyzeGame(pgntext,depth,fromdepth)
	
	old_score = [None]*(depth-fromdepth+1)
	for i in range(fromdepth,depth+1):
		old_score[i-fromdepth] = 0
	white_turn = 1
	for move,score in scores:
		print "Move: " + str(move) + " --- score is " + str(score) + ' --- delta_score=' + str((int(score[5]) - int(old_score[6]))*white_turn)
		old_score = score
		white_turn = -white_turn
