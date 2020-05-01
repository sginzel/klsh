# A generator based on work by https://medium.com/@enriqueav
import random
import sys

import numpy as np
import pydot
from keras.callbacks import ModelCheckpoint, LambdaCallback, EarlyStopping
from keras.optimizers import RMSprop
from keras.utils import plot_model

from klsh.KlshData import Corpus
from klsh.KlshData import Song

from keras.preprocessing import sequence
from keras.models import Sequential
from keras.layers import Dense, Dropout, Embedding, LSTM, Bidirectional, Activation

# visualization
from IPython.display import SVG, display
from keras.utils import model_to_dot

#import tensorflow as tf

class LSTMOne:
    """
    First version of a tensor flow LSTM adapted from https://medium.com/coinmonks/word-level-lstm-text-generator-creating-automatic-song-lyrics-with-neural-networks-b8a1617104fb
    """

    SEQ_LENGTH = 10
    MIN_WORD_FREQUENCY = 10
    BATCH_SIZE = 1000
    MAXLEN = 40

    def __init__(self, corpus):
        """
        Takes a Corpus class to train a LSTM model
        :param corpus: Corpus instance
        """
        self.corpus = corpus
        self.sentences, self.next_words, self.sentences_test, self.next_words_test = corpus.generate_model_data(LSTMOne.SEQ_LENGTH, LSTMOne.MIN_WORD_FREQUENCY)

    # https://medium.com/coinmonks/word-level-lstm-text-generator-creating-automatic-song-lyrics-with-neural-networks-b8a1617104fb
    def model(self, dropout = 0.1):
        # https://github.com/keras-team/keras/blob/master/examples/lstm_text_generation.py
        maxlen = LSTMOne.MAXLEN

        model = Sequential()
        model.add(Bidirectional(LSTM(128), input_shape=(LSTMOne.SEQ_LENGTH, len(self.corpus.words))))
        if dropout > 0:
            model.add(Dropout(dropout))
        model.add(Dense(len(self.corpus.words)))
        model.add(Activation('softmax'))
        model.add(LSTM(128, input_shape=(maxlen, len(self.corpus.words))))

        return model

    def plot_model(self, filename = "model.png"):
        model = Sequential()
        model.add(Dense(2, input_dim=1, activation='relu'))
        model.add(Dense(1, activation='sigmoid'))
        plot_model(model, to_file=filename, show_shapes=True, show_layer_names=True)

    def display_model_svg(self):
        display(SVG(model_to_dot(self.model).create(prog='dot', format='svg')))

    def train_model_keras(self):
        model = self.model_keras()

        file_path = "./checkpoints/LSTM_LYRICS-epoch{epoch:03d}-words%d-sequence%d-minfreq%d-loss{loss:.4f}-acc{acc:.4f}-val_loss{val_loss:.4f}-val_acc{val_acc:.4f}" % (
            len(self.corpus.words),
            LSTMOne.SEQ_LENGTH,
            LSTMOne.MIN_WORD_FREQUENCY
        )
        checkpoint = ModelCheckpoint(file_path, monitor='val_acc', save_best_only=True)
        # print callback needs some love
        # print_callback = LambdaCallback(on_epoch_end=on_epoch_end)
        early_stopping = EarlyStopping(monitor='val_acc', patience=5)
        #callbacks_list = [checkpoint, print_callback, early_stopping]
        callbacks_list = [checkpoint, early_stopping]

        optimizer = RMSprop(learning_rate=0.01)
        model.compile(loss='categorical_crossentropy', optimizer=optimizer)

        model.fit_generator(self.generator(self.sentences, self.next_words, LSTMOne.BATCH_SIZE),
                            steps_per_epoch=int(len(self.sentences) / LSTMOne.BATCH_SIZE) + 1,
                            epochs=100,
                            callbacks=callbacks_list,
                            validation_data=self.generator(self.sentences_test, self.next_words_test,
                                                           LSTMOne.BATCH_SIZE),
                            validation_steps=int(len(self.sentences_test) / LSTMOne.BATCH_SIZE) + 1)

    def generator(self, sentence_list, next_word_list, batch_size):
        index = 0
        while True:
            x = np.zeros((batch_size, LSTMOne.SEQ_LENGTH, len(self.corpus.words)), dtype=np.bool)
            y = np.zeros((batch_size, len(self.corpus.words)), dtype=np.bool)
            for i in range(batch_size):
                for t, w in enumerate(sentence_list[index]):
                    x[i, t, self.corpus.word_indices[w]] = 1
                y[i, self.corpus.word_indices[next_word_list[index]]] = 1

                index = index + 1
                if index == len(sentence_list):
                    index = 0
            yield x, y