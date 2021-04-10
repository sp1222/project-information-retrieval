from flask import Flask, render_template, request, redirect, url_for
from googleapiclient.discovery import build
from whoosh.fields import SchemaClass, Schema, TEXT, ID, NUMERIC
import whoosh.index as whoosh_index
from whoosh.qparser import QueryParser
from whoosh.qparser import MultifieldParser
import csv
import os

app = Flask(__name__)
app.secret_key = "D4T4 M!n!ng"
api_key = "AIzaSyBRsn6JVdq6-Jbk-AbM2YncKA9ji3DTvQA"
cse_key = "81d96764a1dfab385"
fileNames = {'lyrics':
                 {'BM25F Multifield': ['artist', 'lyrics', 'song'],
                  'BM25F Singlefield': 'lyrics'}
             }

# *****************************************************************************************
# hit object class
class hit_object:

    def __init__(self, rank, docnum, score, snippet, dictionary):
        self.rank = rank
        self.docnum = docnum
        self.score = score
        self.snippet = snippet
        self.dictionary = dictionary

# *****************************************************************************************
# init schema, generic blank
def init_schema():
    return Schema(path=ID(unique=True, stored=True), content=TEXT(stored=True))

# *****************************************************************************************
# init lyrics schema
def init_lyrics_schema():
    # Rank, Song, Artist, Year, Lyrics, Source
    return Schema(id=ID(unique=True, stored=True), rank=NUMERIC(stored=True),
                  song=TEXT(stored=True), artist=TEXT(field_boost=2.0, stored=True), year=NUMERIC(stored=True),
                  lyrics=TEXT(stored=True), source=NUMERIC(stored=True))

# *****************************************************************************************
# init index
def init_index(name):
    return whoosh_index.create_in(name + '_dir', schema=init_schema())

# *****************************************************************************************
# init lyrics index
def init_lyrics_index(name):
    return whoosh_index.create_in(name + '_dir', schema=init_lyrics_schema())

# *****************************************************************************************
# add to index
def add_docs_to_lyrics_index(idx, name):
    # Rank, Song, Artist, Year, Lyrics, Source
    f = open(name + '.csv', 'r')
    reader = csv.DictReader(f)
    writer = idx.writer()
    i = 0
    for row in reader:
        i += 1
        try:
            writer.add_document(id=str(i), rank=str(row['Rank']), song=row['Song'], artist=row['Artist'],
                                year=str(row['Year']),
                                lyrics=row['Lyrics'] if row['Lyrics'] != 'NA' else '',
                                source=str(row['Source']) if row['Source'] != 'NA' else '0')
        except:
            print('An error occurred at the following row in the file.')
            print(row['Rank'] + '\t' + row['Song'] + '\t' + row['Artist'] + '\t' + row['Year'] + '\t' + row['Lyrics']
                  + '\t' + row['Source'])
            break
    f.close()
    writer.commit()

# *****************************************************************************************
# run search query using the keyword entered.
def search_query(idx, word):
    qp = QueryParser('content', schema=idx.schema)
    q = qp.parse(word)

    with idx.searcher() as searcher:
        res = searcher.search(q)
    return res

# *****************************************************************************************
# run multifield query using the keyword entered.
def multifield_search_query(idx, word, fields=[]):
    limit = 10
    highlight_Max = 1
    res = []
    qp = MultifieldParser(fields, idx.schema)
    q = qp.parse(word)

    with idx.searcher() as searcher:
        result = searcher.search(q, limit=limit)
        for hit in result:
            highlight = ''
            for field in fields:
                if len(hit.highlights(field)) > 0:
                    highlight += hit.highlights(field, top=highlight_Max) + ' ... '
            res.append(hit_object(rank=hit.rank, docnum=hit.docnum, score=hit.score, snippet=highlight
                                  , dictionary=hit.fields()))
    return res

# *****************************************************************************************
# run simple query using the keyword entered.
def simple_search_query(idx, word, field=''):
    limit = 10
    highlight_char_Max = 0
    res = []
    qp = QueryParser(field, schema=idx.schema)
    q = qp.parse(word)

    with idx.searcher() as searcher:
        result = searcher.search(q, limit=limit)
        for hit in result:
            res.append(
                hit_object(rank=hit.rank, docnum=hit.docnum, score=hit.score, snippet=hit.highlights(field, top=3)
                           , dictionary=hit.fields()))
    return res

# *****************************************************************************************
# search results of a keyword using Google API
def web_search(k, **kwargs):
    if k:
        service = build("customsearch", "v1", developerKey=api_key)
        r = service.cse().list(q=k, cx=cse_key, **kwargs).execute()
        return r['items']  # returns a dictionary of items
    return None

# *****************************************************************************************
# lyrics page, work in progress..
# issue with getting lyrics value.
# issue with getting request.method == "POST" instead of "GET"
'''
@app.route('/lyrics/<song>/', methods=['POST', 'GET'])
def lyrics(song):
    lyrics = None
    if request.method == 'POST':
        lyrics = request.form[song]
    else:
        lyrics = request.args.get(song)
    print(request.method)
    print(request.form.getlist('value'))
    return render_template('lyrics.html', song=song, lyrics=lyrics)
'''

# *****************************************************************************************
# lyrics page, brute forced it..
@app.route('/lyrics/<song>/<lyrics>')
def lyrics(song, lyrics):
    return render_template('lyrics.html', song=song, lyrics=lyrics)

# *****************************************************************************************
# host home
@app.route('/', methods=['POST', 'GET'])
def home():
    # dictionary of search types with their respective function calls.
    scoring_methods = {'BM25F Multifield': multifield_search_query,
                       'BM25F Singlefield': simple_search_query}
    if request.method == 'POST':
        keyword = request.form['keyword']
        if keyword is not None or keyword.isspace == False or keyword != '':
            if request.form['button'] == 'Search Locally':
                file = request.form['file']
                score_method = request.form['score_method']
                # conduct the search of our structured data on the local web server and display the results...
                medium = 'Locally'

                search_index = whoosh_index.open_dir(file + '_dir')
                results = scoring_methods[score_method](search_index, keyword, fileNames[file][score_method])

                return render_template('home.html', keyword=keyword, medium=medium, results=results,
                                       files=list(fileNames.keys()), scoring_methods=list(scoring_methods.keys()))
            elif request.form['button'] == 'Search Google':
                # conduct the search using google, yahoo, bing, etc..
                # results should contain title and snippet information.
                # titles should be clickable links to their corresponding pages

                ### ADD: evaluate the search engine?

                medium = 'Google'
                results = web_search(keyword, num=10)
                return render_template('home.html', keyword=keyword, medium=medium, results=results,
                                       files=list(fileNames.keys()), scoring_methods=list(scoring_methods.keys()))

    return render_template('home.html', keyword='', medium='', results=[],
                            files=list(fileNames.keys()), scoring_methods=list(scoring_methods.keys()))


# ******************************************************************************************
# Init __name__
if __name__ == '__main__':
    # initialize indices if they do not already exist for each .csv file.
    # make it so that i don't have to rebuild these every single time..
    for name in list(fileNames.keys()):
      if not os.path.exists(name + '_dir'):
          os.mkdir(name + '_dir')
          idx = init_lyrics_index(name)
          add_docs_to_lyrics_index(idx, name)
    app.run(debug=True)
