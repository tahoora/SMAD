from context import ROOT_DIR, dataUtils, nnUtils, md

import numpy           as np
import tensorflow      as tf

import os

os.environ['TF_CPP_MIN_LOG_LEVEL']='2'

# This module is used to detect God Classes in new systems using the pre-trained model.

#Constants
num_networks = 5
layers = [86, 44]
input_size     = 7
constants_size = 2

def get_save_path(net_number):
	return os.path.join(ROOT_DIR, 'neural_networks/trained_models/feature_envy/final/network' + str(net_number))

def getSmells(systemName):
	# Load Inputs in vector form
	x = nnUtils.getInstances(systemName, 'feature_envy')
	c = nnUtils.getSystemConstants(systemName)

	# New graph
	tf.reset_default_graph()
	# Create model
	model = md.MergedDetection(layers, input_size, constants_size)
	# Restore the trained models
	saver = tf.train.Saver()
	#Create session
	session = tf.Session()

	# Ensemble Prediction
	predictions = []
	for i in range(num_networks):
		# Reload the variables into the TensorFlow graph.
		saver.restore(sess=session, save_path=get_save_path(i))

		#Perform forward calculation
		feed_dict = {model.input_x: x, model.constants: c, model.dropout_keep_prob:1.0}
		pred = session.run(model.inference, feed_dict=feed_dict)
		predictions.append(pred)
  	
	output = np.mean(np.array(predictions), axis=0)
	feature_envy_index = np.where(output[:,0]>0.5)[0]

	return [c for i, c in enumerate(dataUtils.getCandidateFeatureEnvy(systemName)) if i in feature_envy_index]

if __name__ == "__main__":
	print(getSmells('android-platform-support'))