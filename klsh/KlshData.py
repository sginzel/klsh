import json
import random


class Song:
    """
    Song class is used for songs.
    """

    def __init__(self, attributes):
        """
        :param attributes: dictionary that is used as a data container for the song attributes
        """
        self._attributes = attributes
        return None

    def attribute(self, name):
        return self._attributes.get(name, None)

    def attribute_names(self):
        return list(self._attributes.keys())

    def title(self):
        return self.attribute("Titel")

    def category(self):
        return self.attribute("Kategorie")

    def author(self):
        return self.attribute("Text")

    def year(self):
        return self.attribute("Erscheinungsjahr")

    def source(self):
        return self.attribute("Quelle")

    def lyrics(self, lyric_type=None) -> str:
        """
        Available lyric_types:
            - klsh_text
            - original_text
            - german_text
        """
        if lyric_type is None:
            lyric_type = "original_text"
        return self.attribute(lyric_type)

    def load_by_year(year):
        """
        Loads songs from a specific year.
        :return: Array of Song objects
        """
        songs = []
        jsonfile = Song.get_lyricsstore(year)

        with open(jsonfile, "r") as fin:
            song_attributes = json.load(fin).values()
        for attr in song_attributes:
            songs.append(Song(attr))

        return songs

    def get_lyricsstore(year):
        """
        for a given year, return the json file that contains all songs.
        :return: filename as string
        """
        return "data/songs/lyrics_" + str(year) + ".json"


# This class takes care of creating a training dataset
# as described here: https://medium.com/coinmonks/word-level-lstm-text-generator-creating-automatic-song-lyrics-with-neural-networks-b8a1617104fb
class Corpus:
    """
    Corpus class to aggregate lyrics data from songs
    """

    def __init__(self, year_from, year_to):
        self.corpus = []
        cnt = 0
        for year in range(year_from, year_to):
            print("loading: " + str(year) + "")

            for song in Song.load_by_year(year):
                cnt += 1
                self.corpus += self.tokenize_song(song)
        print("loaded " + str(cnt) + " songs into corpus")
        self.words = None
        return None

    def tokenize_song(self, song) -> str:
        """
        Tokenizes a songs lyrics
        :param song: Song instance
        :return: array of words
        """
        lyrics = song.lyrics().lower().replace("\n", " \n")  # make sure newlines are handled as separate words
        tokens = [w for w in lyrics.split(' ') if w.strip() != '' or w == '\n']
        return tokens

    def generate_model_data(self, sequence_length=10, min_word_freq=10):
        word_freq = {}
        for word in self.corpus:
            word_freq[word] = word_freq.get(word, 0) + 1

        ignored_words = set()  # refactor this into a dict in case this takes too long
        for k, v in word_freq.items():
            if word_freq[k] < min_word_freq:
                ignored_words.add(k)

        self.words = set(self.corpus)
        print('Unique words before ignoring:', len(self.words))
        print('Ignoring words with frequency <', min_word_freq)
        self.words = sorted(set(self.words) - ignored_words)
        print('Unique words after ignoring:', len(self.words))

        self.word_indices = dict((c, i) for i, c in enumerate(self.words))
        self.indices_word = dict((i, c) for i, c in enumerate(self.words))

        # cut the text in semi-redundant sequences of SEQUENCE_LEN words
        STEP = 1
        sentences = []
        next_words = []
        ignored = 0
        for i in range(0, len(self.corpus) - sequence_length, STEP):
            # Only add sequences where no word is in ignored_words
            if len(set(self.corpus[i: i + sequence_length + 1]).intersection(ignored_words)) == 0:
                sentences.append(self.corpus[i: i + sequence_length])
                next_words.append(self.corpus[i + sequence_length])
            else:
                ignored = ignored + 1
        print('Ignored sequences:', ignored)
        print('Remaining sequences:', len(sentences))
        return self.shuffle_and_split_training_set(sentences, next_words)

    def shuffle_and_split_training_set(self, sentences, next_words) -> list:
        """
        Split into training and test sets (95/5)
        :param sentences: Array of array of words
        :param next_words: Array of words
        :return:
        """
        indexes = list(range(0, len(sentences)))
        random.shuffle(indexes)
        indexes_train = indexes[0:int(len(indexes) * 0.95)]
        indexes_test = indexes[int(len(indexes) * 0.95):-1]
        return (list(
            [
                [sentences[i] for i in list(indexes_train)],
                [next_words[i] for i in list(indexes_train)],
                [sentences[i] for i in list(indexes_test)],
                [next_words[i] for i in list(indexes_test)],
            ]))
