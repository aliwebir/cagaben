# Standard Core Python Libraries
import os, sys, json
from time import time
from pprint import pprint

# MongoDB Python Interface
from pymongo import MongoClient

# Datamining Libraries
from sklearn.feature_extraction.text import TfidfVectorizer
import scipy.sparse as sp
import numpy

# Global Variables
ADAScores = {
	'washtimes': 35.4, #1
	'FoxNews': 39.7, #2

	#'NewsHour', #3
	'cnn': 56.0, #4
	'gma': 56.1, #5
	'usatoday': 63.4, #6
	#'usnews', #7
	'washingtonpost': 66.6, #8

	'latimes': 70.0, #9
	'CBSNews': 73.7, #10
	'nytimes': 73.7, #11
	#'wsj', #12 - not good
}

political_alignments = [
	("Conservative", [
		"washtimes",
		"FoxNews"]),
	("Neutral", [
		"cnn",
		"gma",
		"usatoday",
		"washingtonpost"]),
	("Liberal", [
		"latimes",
		"CBSNews",
		"nytimes"])
]

freq_threshold = 0.1


def read(path):
	print ("")
	errors = 0

	try:
		os.chdir(path)
	except e:
		raise e

	client = MongoClient()
	ibm_dataset = client.ibm_dataset
	related = ibm_dataset.related

	for jsonFileName in os.listdir(path):
 
		f = open(jsonFileName,"r")

		try:
			text = json.load(f)
		except:
			print (f.name)
			errors += 1
			continue

		try:
			related.insert_one(text)
		except e:
			print (f.name)
			errors += 1
	print (errors)

def connect_mongodb(db, col):

	# Grab the collection from the database we want
	col = MongoClient()[db][col]

	# Return the collection cursor, to be queried later
	return col

def tf_idf(documents):

	# Scikit Learn TF-IDF syntax
	vectorizer = TfidfVectorizer(encoding='latin1', stop_words='english')
	X_train = vectorizer.fit_transform(documents)

	# Get the names of the features (words)
	feature_names = vectorizer.get_feature_names()

	# Final result to return
	all_tfs = []

	for doc in X_train:

		# convert the sparse matrix to a Python list
		doc = doc.todense()
		doc = numpy.array(doc)[0].tolist()

		# Create a list for this story, it will contain (word, frequency) pairs
		tf = []

		for i in range(len(doc)):
			if (doc[i] != 0):
				tf.append((feature_names[i], doc[i]))
				# print ('{0:14} ==> {1:10f}'.format(tf[-1][0], tf[-1][1]))

		# Sort the list by frequency, descending
		tf = sorted(tf, key=lambda freq: freq[1], reverse=True)

		# Append this document's tf to all the tfs
		all_tfs.append(tf)
	return all_tfs


"""
def tf_idf_selector(idf_group, collection)
	idf_group:	'A' - Topic
							'B' - Political Alignment
							'C' - Agency
							'D' - Agency & Topic
	collection: The MongoDB collection to which we will query
"""
def tf_idf_selector(idf_group, collection):

	# tf is all of the text frequencies per story, against the defined idf_group
	tf = []

	# IDF is all stories under the same Topic
	if idf_group == "A":

		# Query DB, looking for all topics to take inventory
		db_results = collection.find({}, { "topic" : 1 } )

		# Gather unique topics
		all_topics = list(set(list(story["topic"] for story in db_results)))

		for topic in all_topics:

			# Query the DB for all results that match the given topic
			db_results = collection.find({ "topic" : topic })

			# Strip the content out of the database entries, as 
			# the TF-IDF algorithm only likes documents
			documents = []
			for story in db_results:
				documents.append(story["content"])

			tf.append(tf_idf(documents))

		# Flatten the list of lists before returning
		return [item for sublist in tf for item in sublist]

	# IDF is all stories under the same political alignment
	elif idf_group == "B":

		# Populate with queries
		queries = []
		for alignment in political_alignments:
			
			# Create the general query
			query = { "source" : { "$in": [] } }

			# Put the agencies into the query
			query["source"]["$in"] = alignment[1]

			# Add the query to the list of queries
			queries.append(query)

		# Query the database for the different alignments
		for alignment_query in queries:

			# Query the DB for all results that match the given source
			db_results = collection.find(alignment_query)

			# Strip the content out of the database entries, as 
			# the TF-IDF algorithm only likes documents
			documents = []
			for story in db_results:
				documents.append(story["content"])

			tf.append(tf_idf(documents))

		# Flatten the list of lists before returning
		return [item for sublist in tf for item in sublist]

	# IDF is all stories under the same Agency
	elif idf_group == "C":

		# Query DB, looking for all sources to take inventory
		db_results = collection.find({}, { "source" : 1 } )

		# Gather unique sources
		all_sources = list(set(list(story["source"] for story in db_results)))

		for source in all_sources:

			# Query the DB for all results that match the given source
			db_results = collection.find({ "source" : source })

			# Strip the content out of the database entries, as 
			# the TF-IDF algorithm only likes documents
			documents = []
			for story in db_results:
				documents.append(story["content"])

			tf.append(tf_idf(documents))

		# Flatten the list of lists before returning
		return [item for sublist in tf for item in sublist]

	# IDF is all stories under the same Agency and Topic
	elif idf_group == "D":

		# Query DB, looking for all topics to take inventory
		db_results1 = collection.find({}, { "topic" : 1 } )
		# Query DB, looking for all sources to take inventory
		db_results2 = collection.find({}, { "source" : 1 } )

		# Gather unique topics
		all_topics = list(set(list(story["topic"] for story in db_results1)))
		# Gather unique sources
		all_sources = list(set(list(story["source"] for story in db_results2)))

		for topic in all_topics:

			for source in all_sources:

				# Query the DB for all results that match the given source
				db_results = collection.find({ "topic" : topic, "source" : source })

				# Strip the content out of the database entries, as 
				# the TF-IDF algorithm only likes documents
				documents = []
				for story in db_results:
					documents.append(story["content"])

				tf.append(tf_idf(documents))

		# Flatten the list of lists before returning
		return [item for sublist in tf for item in sublist]
		
	else:
		print ("The selection: " + str(idf_group) + " is not valid")
		return

def filter_results(tf_stories):

	result = []

	for story in tf_stories:

		# Add an empy list to append these words to
		result.append([])

		for tf in story:

			# If we have gone below the threshold, stop adding words from that story
			if tf[1] < freq_threshold:
				break

			# We are still within our threshold, add words
			result[-1].append(tf)

	return result


if __name__ == "__main__":

	# col = connect_mongodb("cagaben7", "story")
	col = connect_mongodb("news_bias", "stories")

	results1 = filter_results(tf_idf_selector("A", col))
	results2 = filter_results(tf_idf_selector("B", col))
	results3 = filter_results(tf_idf_selector("C", col))
	results4 = filter_results(tf_idf_selector("D", col))

	results1 = filter_results(results1)
	results2 = filter_results(results2)
	results3 = filter_results(results3)
	results4 = filter_results(results4)

	for story in range(len(results1)):
		print ("\nNew Story: ")
		pprint (filtered_results1[story])
		pprint (filtered_results2[story])
		pprint (filtered_results3[story])
		pprint (filtered_results4[story])








