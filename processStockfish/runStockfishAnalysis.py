#!/bin/python
# -*- coding: utf-8 -*-

import pgn
from subprocess import *
import select
import time
import sys, getopt
import analyzeStockfish
import psycopg2
import random

# Start time...
start_time = time.time()
print '---- Starting analysis on ' + str(time.ctime()) + '----'

# Set default depth and number of games, and check if parameter is being sent.
depth = 8
numgames = 1

# Check command-line arguments. If no argument is provided, just run the test file.
try:
	opts, args = getopt.getopt(sys.argv[1:], "d:n:m:", ["depth","numgames","fromdepth"])
except getopt.GetoptError, err:
	print str(err) # will print something like "option -a not recognized"
	sys.exit(2)

for o, a in opts:
	if o in ("-d", "--depth"):
		depth = int(float(a))
	elif o in ("-n", "--numgames"):
		numgames = int(float(a))
	elif o in ("-m", "--fromdepth"):
		fromdepth = int(float(a))
	else:
		assert False, "unhandled option"

# Query prefix for adding moves...
sql_insert = 'INSERT INTO move_properties (move' #stockfish_score, stockfish_delta_score) VALUES '
for i in range(fromdepth,depth+1):
	sql_insert += ', score_depth' + str(i)
sql_insert += ', delta_score) VALUES '
#print sql_insert

# Connect to the database
try:
	conn = psycopg2.connect("dbname='ficsdb' user='dfslezak' host='calamaro.exp.dc.uba.ar' password='23571113'")
	cursor = conn.cursor()
except:
	text = "I am unable to connect to the database"
	print text
	exit(0)

for i in range(numgames):
	# Get an unanalysed game from database
	#total_time = random.choice([1,1,1,2,3,3,3,4,5,5,5,6,7,8,9,10,10,10,11,12,13,14])
	#increment = 0
	nGames = 1

	# Get the min and max id_game to throw a random number...
	#statement = "SELECT min(id_game),max(id_game) FROM games WHERE games.increment="+str(increment)+" AND games.total_time="+str(total_time)
	statement = "SELECT min(id_game),max(id_game) FROM games"
	cursor.execute(statement)
	result = cursor.fetchone()
	min_id_game = result[0]
	max_id_game = result[1]
	random_game = random.randint(min_id_game, max_id_game)
	print 'Selecting game from ' + str(min_id_game) + ' to ' +str(max_id_game)+': '+str(random_game)

	# Get unanalysed game.
	#statement = "SELECT id_game, get_game(id_game) FROM games WHERE id_game>"+str(random_game)+" AND (stockfish_analysed IS NULL OR NOT stockfish_analysed) AND ply_count>5 AND ply_count<200 AND game_type<>4 AND game_type<>5 ORDER BY id_game LIMIT 1;"
	statement = "SELECT id_game, get_game(id_game) FROM games JOIN users as u1 ON u1.id_user=games.w_user JOIN users as u2 ON u2.id_user=games.b_user WHERE id_game>"+str(random_game)+" AND (stockfish_analysed IS NULL OR NOT stockfish_analysed) AND ply_count>5 AND ply_count<200 AND game_type<>4 AND game_type<>5 AND (u1.timezone is NOT NULL OR u2.timezone is NOT NULL) AND (u1.has_chronotype OR u2.has_chronotype) ORDER BY id_game LIMIT 1;"
        	cursor.execute(statement)
	result = cursor.fetchone()
	# If no more games to analyse, simpley start all over again choosing another total_time.
	if len(result)==0: 
		#print 'No more games of total_time='+str(total_time)
		print 'No more games to analyse'
		continue
	
	id_game = result[0]
	print 'Analysing game '+str(id_game)
	pgntext = result[1]
	pgntext_split = result[1].split()
	plyCount = pgntext_split[pgntext_split.index('[PlyCount')+1].strip('"[]')
	
	# Get unanalysed game.
	statement = "SELECT id_move, move_number,w_b FROM moves WHERE game=" + str(id_game) + "ORDER BY move_number,w_b"
	cursor.execute(statement)
	result = cursor.fetchall()
	ID_MOVE=0

	# Now that we have the PGN text, send it to stockfish to analyse it...
	scores = analyzeStockfish.analyzeGame(pgntext,depth,fromdepth)

	# Check that stockfish analysed all moves and generate SQL query for insertion
	if int(len(scores)) == int(plyCount):
		sql_insert_all = sql_insert
		iterator = 0
		for move,score_array in scores:
			# Initialize move-values string and calculate delta_score
			if iterator>0: 
				if (iterator % 2==0): sign = 1.0
				else: sign = (-1.0)
				delta_score = sign*(float(score_array[5])-float(scores[iterator-1][1][6]))
				sql_move=','
			else: 
				delta_score = score_array[6]
				sql_move=''
				
			
			# Create tuple for move-values string
			sql_move+='(' + str(result[iterator][ID_MOVE]) + ','
			for i in range(fromdepth,depth+1):
				sql_move+= str(float(score_array[i-fromdepth])/100.0) + ','
			sql_move += str(float(delta_score)/100.0)+')'
			
			# Append to SQL query.
			sql_insert_all += sql_move
			
			# Increment iterator
			iterator += 1
			
			#print "Move: " + str(move) + " --- score is " + str(score)
		sql_insert_all += ";"
		cursor.execute(sql_insert_all)
		conn.commit()
		#print sql_insert_all

	else:
		print "Game " + str(id_game) + ': Something went wrong. Different amount of moves and scores.'
		exit(0)
		
	# After inserting moves, we have to check "stockfish_analyzed".
	statement = "SET enable_seqscan=false; SELECT check_stockfish_analysed_game("+ str(id_game) + ");";
	cursor.execute(statement)
	result = cursor.fetchone()

	if result[0] == True:
		text = "Game " + str(id_game) + ": All scores inserted!!"
		print text
	else:
		text = "Game " + str(id_game) + ": Some score is missing..."
		print text

	conn.commit()

# Close database connection...
conn.close()

# End time...
end_time = time.time()
print '---- Ending analysis on ' + str(time.ctime()) + ' (Elapsed time: ' + str(end_time-start_time)+ 'seconds) ----'
