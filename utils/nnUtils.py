from context               import ROOT_DIR
from sklearn.preprocessing import StandardScaler

import numpy             as np
import tensorflow        as tf
import matplotlib.pyplot as plt

import dataUtils
import os
import random
import sys

### EVALUATION ####
def detected(output):
	return np.sum((output > 0.5).astype(float))

def positive(labels):
	return np.sum(labels)

def true_positive(output, labels):
	return np.sum((output + labels > 1.5).astype(float))

def precision(output, labels):
	return true_positive(output, labels)/detected(output)

def recall(output, labels):
	return true_positive(output, labels)/positive(labels)

def f_measure(output, labels):
	p = precision(output, labels)
	r = recall(output, labels)

	return 2*p*r/(p+r)


### UTILS ###

def build_dataset(antipattern, systems):
	input_size = {'god_class':8, 'feature_envy':9}
	X = np.empty(shape=[0, input_size[antipattern]])
	Y = np.empty(shape=[0, 1])
	for systemName in systems:
		X = np.concatenate((X, getInstances(antipattern, systemName)), axis=0)
		Y = np.concatenate((Y, getLabels(antipattern, systemName)), axis=0)

	return X, Y

# Returns the Bayesian averaging between many network's predictions
def ensemble_prediction(model, save_paths, input_x):
	saver = tf.train.Saver(max_to_keep=len(save_paths))
	predictions = []
	with tf.Session() as session:
		for save_path in save_paths:
			saver.restore(sess=session, save_path=save_path)
			prediction = session.run(model.inference, feed_dict={model.input_x: input_x})
			predictions.append(prediction)

	return np.mean(np.array(predictions), axis=0)

# Get the path of a trained model for a given approach (smad or asci)
def get_save_path(approach, antipattern, test_system, model_number):
	directory = os.path.join(ROOT_DIR, 'neural_networks', approach, 'trained_models', antipattern, test_system)
	if not os.path.exists(directory):
			os.makedirs(directory)
	return os.path.join(directory, 'model_' + str(model_number))

# Plot learning curves with mean and standard deviations
# losses_train: a list of lists which contain losses values for training
# losses_test : same for testing
def plot_learning_curves(losses_train, losses_test):
	plt.figure()
	plt.ylim((0.0, 1.0))
	plt.xlabel("Epochs")
	plt.ylabel("Loss")
	mean_train = np.mean(losses_train, axis=0)
	mean_test = np.mean(losses_test, axis=0)
	percentile90_train = np.percentile(losses_train, 90, axis=0)
	percentile90_test  = np.percentile(losses_test, 90, axis=0)
	percentile10_train = np.percentile(losses_train, 10, axis=0)
	percentile10_test = np.percentile(losses_test, 10, axis=0)
	plt.grid()

	plt.fill_between(range(len(losses_train[0])), percentile90_train,
	                 percentile10_train, alpha=0.2,
	                 color="r")
	plt.fill_between(range(len(losses_test[0])), percentile90_test,
	                 percentile10_test, alpha=0.2,
	                 color="g")
	plt.plot(range(len(losses_train[0])), mean_train, color="r", label='Training set')
	plt.plot(range(len(losses_test[0])), mean_test, color="g", label='Test set')
	plt.legend(loc='best')
	plt.show()

# Returns an array of predictions for each input instances from a set of smells
# i.e., the set of occurrences detected by an approach.
# smells: a set of entities' names (i.e., those that have been detected) 
def predictFromDetect(antipattern, systemName, smells):
	entities = dataUtils.getEntities(antipattern, systemName)

	prediction = []
	for entity in entities:
		if entity in smells:
			prediction.append([1.])
		else:
			prediction.append([0.])

	return np.array(prediction)

def shuffle(X, Y):
	assert len(X) == len(Y), 'X and Y must have the same number of elements'

	idx = range(len(X))
	random.shuffle(idx)

	shuffled_X = np.array([X[i] for i in idx])
	shuffled_Y = np.array([Y[i] for i in idx])
	
	return shuffled_X, shuffled_Y

def split(X, Y, nb_split):
	assert len(X) == len(Y), 'X and Y must have the same number of elements' 
	
	length = len(X)//nb_split
	sections  = [(i+1)*length for i in range(nb_split-1)]

	return np.split(X, sections), np.split(Y, sections)


### INSTANCES AND LABELS GETTERS ###

# Get labels in vector form for a given system
# antipattern in ['god_class', 'feature_envy']
def getLabels(antipattern, systemName):
	entities = dataUtils.getEntities(antipattern, systemName)
	true = dataUtils.getAntipatterns(antipattern, systemName)

	labels = []
	for entity in entities:
		if entity in true:
			labels.append([1.])
		else:
			labels.append([0.])

	return np.array(labels)


def getInstances(antipattern, systemName, normalized=True):
	assert antipattern in ['god_class', 'feature_envy']

	metrics = []
	if antipattern == 'god_class':
		entities = dataUtils.getClasses(systemName)
		metrics.append(dataUtils.getGCDecorMetrics(systemName))
		metrics.append(dataUtils.getGCHistMetrics(systemName))
		metrics.append(dataUtils.getGCJDeodorantMetrics(systemName))
	else:
		entities = dataUtils.getCandidateFeatureEnvy(systemName)
		metrics.append(dataUtils.getFEHistMetrics(systemName))
		metrics.append(dataUtils.getFEInCodeMetrics(systemName))
		metrics.append(dataUtils.getFEJDeodorantMetrics(systemName))

	instances = []
	for entity in entities:
		instance = []
		for metricMap in metrics:
			instance += metricMap[entity]
		instances.append(instance)
	instances = np.array(instances).astype(float)

	# Batch normalization
	'''if normalized:
		scaler = StandardScaler()
		scaler.fit(instances)
		return scaler.transform(instances)'''

	scaler = StandardScaler()
	scaler.fit(instances)
	instances = scaler.transform(instances)

	instances = np.concatenate((instances, np.tile(getSystemConstants(systemName), (instances.shape[0],1))), axis=1)

	return instances


def getSystemConstants(systemName):
	systemToIndexMap = {
		'android-frameworks-opt-telephony': 0,
		'android-platform-support': 1,
		'apache-ant': 2,
		'apache-tomcat': 3,
		'lucene': 4,
		'argouml': 5,
		'jedit': 6,
		'xerces-2_7_0': 7
	}

	# Sizes of the systems (i.e, number of classes)
	sizes = [190, 104, 755, 1005, 160, 1246, 437, 658]

	# History length of the systems (i.e, number of commits)
	nb_commit = [98, 195, 6397, 3289, 429, 5559, 1181, 3453]

	constants = np.array([[sizes[i], nb_commit[i]] for i in range(8)]).astype(float)

	# Normalization
	scaler = StandardScaler()
	scaler.fit(constants)

	if systemName in systemToIndexMap:
		rescaledConstants = scaler.transform(constants)
		return rescaledConstants[systemToIndexMap[systemName]]
	else:
		size = len(dataUtils.getAllClasses(systemName))
		history_length = len(dataUtils.getHistory(systemName, 'C'))
		rescaledConstants = scaler.transform([[size, history_length]])
		return rescaledConstants[0] 
