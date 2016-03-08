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

def query_mongodb(db, col):

	# Grab the collection from the database we want
	col = MongoClient()[db][col]

	# Return the collection cursor, to be queried later
	return col

	# # Query for all documents in that collection
	# cursor = col.find()

	# result = []
	# for document in cursor:
	# 	# pprint (document["content"][:60])  # Print the first 60 characters of the content
	# 	result.append(document)
	# return result

def tf_idf(documents):

	print("Extracting features from the dataset using a sparse vectorizer")
	t0 = time()
	vectorizer = TfidfVectorizer(encoding='latin1')
	X_train = vectorizer.fit_transform(documents)
	print("done in %fs" % (time() - t0))
	print("n_samples: %d, n_features: %d" % X_train.shape)

	feature_names = vectorizer.get_feature_names()

	# Final result to return
	all_tfs = []

	for doc in X_train:

		# convert the sparse matrix to a Python list
		doc = doc.todense()
		doc = numpy.array(doc)[0].tolist()

		# Create list to return, it will contain (word, frequency) pairs
		tf = []

		for i in range(len(doc)):
			if (doc[i] != 0):
				tf.append((feature_names[i], doc[i]))
				# print ('{0:14} ==> {1:10f}'.format(tf[-1][0], tf[-1][1]))

		# Sort the list by frequency, descending
		tf = sorted(tf, key=lambda freq: freq[1], reverse=True)

		# Append this document's tf to all the tfs
		all_tfs.append(tf)
	print (len(all_tfs))
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

	if idf_group == "A":

		# Query DB, looking for all topics to take inventory
		db_results = collection.find({}, { "topic": 1 } )

		# Gather unique topics
		all_topics = list(set(list(story["topic"] for story in db_results)))

		for topic in all_topics:
			# Query the DB for all results that match the given topic
			db_results = collection.find({}, { "topic":topic , "content":1} )

			documents = []
			for story in db_results:
				documents.append(story["content"])
			tf.append(tf_idf(documents))

		# Flatten the list of lists before returning
		return [item for sublist in tf for item in sublist]

	elif idf_group == "B":
		pass
	elif idf_group == "C":
		pass
	elif idf_group == "D":
		pass
	else:
		print ("The selection: " + str(idf_group) + " is not valid")
		return

if __name__ == "__main__":

	col = query_mongodb("news_bias", "stories")
	# tf_idf(documents)
	results = tf_idf_selector("A", col)
	pprint (results)
	print (len(results))




