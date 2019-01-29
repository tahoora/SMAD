from context               import ROOT_DIR
from sklearn.preprocessing import StandardScaler

import numpy      as np
import tensorflow as tf
import liuUtils

import dataUtils
import random
import sys

### EVALUATION ####
def true_positive(output, labels):
	tp = tf.cast(tf.equal(tf.argmax(output,1) + tf.argmax(labels,1), 0), tf.float32)

	return tp

def precision(output, labels):
	tp = true_positive(output, labels)
	detected = tf.cast(tf.equal(tf.argmax(output,1), 0), tf.float32)

	return tf.reduce_sum(tp)/tf.reduce_sum(detected)

def recall(output, labels):
	tp = true_positive(output, labels)
	positive = tf.cast(tf.equal(tf.argmax(labels,1), 0), tf.float32)

	return tf.reduce_sum(tp)/tf.reduce_sum(positive)

def f_measure(output, labels):
	prec = precision(output, labels)
	rec = recall(output, labels)

	return 2*prec*rec/(prec+rec)

def accuracy(output, labels):
	correct_prediction = tf.equal(tf.argmax(output, 1), tf.argmax(labels,1))

	return tf.reduce_mean(tf.cast(correct_prediction, tf.float32))


### UTILS ###
def shuffle(instances, labels):
	assert len(instances) == len(labels), 'instances and labels must have the same number of elements'

	idx = range(len(instances))
	random.shuffle(idx)

	x = np.array([instances[i] for i in idx])
	y = np.array([labels[i] for i in idx])
	
	return x, y


### INSTANCES AND LABELS GETTERS ###

# Get labels in vector form for a given system
# antipattern in ['god_class', 'feature_envy']
def getLabels(systemName, antipattern):
	assert antipattern in ['god_class', 'feature_envy']

	if antipattern == 'god_class':
		entities = dataUtils.getClasses(systemName)
	else:
		entities = dataUtils.getCandidateFeatureEnvy(systemName)

	labels = []
	true = dataUtils.getAntipatterns(systemName, antipattern)
	for entity in entities:
		if entity in true:
			labels.append([1, 0])
		else:
			labels.append([0, 1])

	return np.array(labels)


def getInstances(systemName, antipattern, normalized=True):
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
	if normalized:
		scaler = StandardScaler()
		scaler.fit(instances)
		return scaler.transform(instances)

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
