from flask import Flask, render_template, request
from googleapiclient.discovery import build
from whoosh import scoring
from whoosh.fields import Schema, TEXT, ID, NUMERIC
from whoosh.qparser import QueryParser
from whoosh.qparser import MultifieldParser
import csv
import os
import whoosh.index as whoosh_index

app = Flask(__name__, instance_relative_config=True)
api_key = "api key here"
cse_key = "cse key here"
app.config.from_pyfile('config.py', silent=True)

fileNames = {'lyrics':
                 {'BM25F Multifield': ['artist', 'lyrics', 'song'],
                  'BM25F Singlefield': 'lyrics'},
                          'beer':
                              {'BM25F Multifield': ['beer', 'style', 'brewery', 'description'],
                               'BM25F Singlefield': 'beer'},
                          'grocery':
                              {'BM25F Multifield': ['product', 'brand', 'category', 'parent_category'],
                               'BM25F Singlefield': 'product'}
             }
# global variable to handle passing information between functions...
results_global = []


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
# init lyrics schema
def init_lyrics_schema():
    # Rank, Song, Artist, Year, Lyrics, Source
    return Schema(id=ID(unique=True, stored=True), rank=NUMERIC(stored=True),
                  song=TEXT(stored=True), artist=TEXT(field_boost=2.0, stored=True), year=NUMERIC(stored=True),
                  lyrics=TEXT(stored=True), source=NUMERIC(stored=True))


# *****************************************************************************************
# init beer schema
def init_beer_schema():
    return Schema(id=ID(unique=True, stored=True), beer=TEXT(stored=True),
                  style=TEXT(stored=True), brewery=TEXT(field_boost=2.0, stored=True),
                  description=TEXT(stored=True), rating=NUMERIC(float, stored=True),
                  abv=NUMERIC(float, stored=True), minibu=NUMERIC(stored=True), maxibu=NUMERIC(stored=True))


# *****************************************************************************************
# init beer schema
def init_grocery_schema():
    return Schema(id=ID(unique=True, stored=True), product=TEXT(stored=True),
                  variant_price=NUMERIC(float, stored=True), variant_uom=TEXT(stored=True),
                  variant_alt_price=NUMERIC(float, stored=True), variant_alt_uom=TEXT(stored=True),
                  brand=TEXT(field_boost=2.0, stored=True), category=TEXT(stored=True), parent_category=TEXT(stored=True))


# *****************************************************************************************
# add to index
def add_docs_to_lyrics_index(idx, name):
    # Rank, Song, Artist, Year, Lyrics, Source
    f = open(os.getcwd() + '\\files\\' + name + '.csv', 'r', encoding='utf8', errors='ignore')
    reader = csv.DictReader(f)
    writer = idx.writer()
    i = -1
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
# add to index
def add_docs_to_beer_index(idx, name):
    f = open(os.getcwd() + '\\files\\' + name + '.csv', 'r', encoding='utf8', errors='ignore')
    reader = csv.DictReader((line.replace('\0', '') for line in f), delimiter = ',')
    writer = idx.writer()
    i = -1
    for row in reader:
        i += 1
 #       try:
        writer.add_document(id=str(i), beer=row['Beer'], style=row['Style'], brewery=row['Brewery'],
                            description=row['Description'],
                            rating=str(float(row['Rating'])), abv=str(float(row['ABV'])), minibu=str(row['Min IBU']),
                            maxibu=str(row['Max IBU']))
 #       except:
 #           print('An error occurred at the following row in the file.')
  #          print(row['Beer'])
  #          break
    f.close()
    writer.commit()


# *****************************************************************************************
# add to index
def add_docs_to_grocery_index(idx, name):
    f = open(os.getcwd() + '\\files\\' + name + '.csv', 'r', newline='', encoding='utf-8-sig', errors='ignore')
    reader = csv.DictReader((line.replace('\0', '') for line in f), delimiter = ',', dialect='excel')
    writer = idx.writer()
    i = -1
    for row in reader:
        i += 1
 #       try:
        writer.add_document(id=str(i), product=row['Name'],
              variant_price=str(float(row['Variant Price'])), variant_uom=row['Variant UOM'],
              variant_alt_price=str(float(row['Variant Alt Price'])), variant_alt_uom=row['Variant Alt UOM'],
              brand=row['Brand'], category=row['Category'], parent_category=row['Parent Category'])
 #       except:
 #           print('An error occurred at the following row in the file.')
 #           print(row['Name'])
 #           break
    f.close()
    writer.commit()


# *****************************************************************************************
# init lyrics index
def init_index(name, function):
    return whoosh_index.create_in(os.getcwd() + '\\indices\\' + name + '_dir', schema=function())


# *****************************************************************************************
# run multifield query using the keyword entered.
def multifield_search_query(idx, word, fields=[]):
    limit = 10000
    highlight_Max = 1
    d = {}
    qp = MultifieldParser(fields, idx.schema)
    q = qp.parse(word)

    with idx.searcher() as searcher:
        result = searcher.search(q, limit=limit)
        res = []
        for hit in result:
            highlight = ''
            for field in fields:
                if len(hit.highlights(field)) > 0:
                    highlight += hit.highlights(field, top=highlight_Max) + ' ... '
            res.append(hit_object(rank=hit.rank, docnum=hit.docnum, score=hit.score, snippet=highlight
                                  , dictionary=hit.fields()))
        d['searchTime'] = result.runtime
        d['totalResults'] = result.scored_length()
        d['items'] = res
    return d


# *****************************************************************************************
# run simple query using the keyword entered.
def simple_search_query(idx, word, field=''):
    limit = 10000
    d = {}
    qp = QueryParser(field, schema=idx.schema)
    q = qp.parse(word)

    with idx.searcher() as searcher:
        result = searcher.search(q, limit=limit)
        res = []
        for hit in result:
            res.append(
                hit_object(rank=hit.rank, docnum=hit.docnum, score=hit.score, snippet=hit.highlights(field, top=3)
                           , dictionary=hit.fields()))
        d['searchTime'] = result.runtime
        d['totalResults'] = result.scored_length()
        d['items'] = res
    return d


# *****************************************************************************************
# search results of a keyword using Google API
def web_search(k, **kwargs):
    if k:
        service = build("customsearch", "v1", developerKey=api_key)
        r = service.cse().list(q=k, cx=cse_key, **kwargs).execute()
        return r['items']  # returns a dictionary of items
        d = {}
        d['searchTime'] = r['searchInformation']['searchTime']
        d['totalResults'] = r['searchInformation']['formattedTotalResults']
        d['items'] = r['items']
        return d
    return None


# *****************************************************************************************
# lyrics page
# NOTE: use global results to get the lyrics for displaying.

@app.route('/lyrics/<rank>=<song>/')
def lyrics(rank, song):
    global results_global
    song_info = results_global[int(rank)].dictionary
    return render_template('lyrics.html', song_info=song_info)


# *****************************************************************************************
# beer page
# NOTE: use global results to get the information for displaying.

@app.route('/beer/<rank>=<beer>/')
def beer(rank, beer):
    global results_global
    beer_info = results_global[int(rank)].dictionary
    return render_template('beer.html', beer_info=beer_info)


# *****************************************************************************************
# grocery page
# NOTE: use global results to get the information for displaying.

@app.route('/grocery/<rank>=<product>/')
def grocery(rank, product):
    global results_global
    product_info = results_global[int(rank)].dictionary
    return render_template('grocery.html', product_info=product_info)


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

                search_index = whoosh_index.open_dir(os.getcwd() + '\\indices\\' + file + '_dir')
                results = scoring_methods[score_method](search_index, keyword, fileNames[file][score_method])
                global results_global
                results_global = results['items']

                return render_template('home.html', keyword=keyword, medium=medium, results=results,
                                       files=list(fileNames.keys()), scoring_methods=list(scoring_methods.keys()),
                                       file=file)
            elif request.form['button'] == 'Search Google':
                # conduct the search using google, yahoo, bing, etc..
                # results should contain title and snippet information.
                # titles should be clickable links to their corresponding pages

                medium = 'Google'
                results = web_search(keyword, num=10)
                return render_template('home.html', keyword=keyword, medium=medium, results=results,
                                       files=list(fileNames.keys()), scoring_methods=list(scoring_methods.keys()),
                                       file='')

    return render_template('home.html', keyword='', medium='', results=[],
                           files=list(fileNames.keys()), scoring_methods=list(scoring_methods.keys()), file='')


# ******************************************************************************************
# Init __name__
if __name__ == '__main__':
    # initialize indices if they do not already exist for each .csv file.
    # made it so that i don't have to rebuild these every single time..
    index_schema_functions = {'lyrics': init_lyrics_schema,
                              'beer': init_beer_schema,
                              'grocery': init_grocery_schema
                              }
    index_add_doc_functions = {'lyrics': add_docs_to_lyrics_index,
                               'beer': add_docs_to_beer_index,
                               'grocery': add_docs_to_grocery_index
                               }
    for name in list(fileNames.keys()):
        if not os.path.exists(os.getcwd() + '\\indices\\' + name + '_dir'):
            os.mkdir(os.getcwd() + '\\indices\\' + name + '_dir')
            index = init_index(name, index_schema_functions[name])
            index_add_doc_functions[name](index, name)
    app.run(debug=True)
    
    

#    Note, for repl.it, all back double slashes "\\" need to change to single forward slashes "/"
#    app.run(debug=True) changes to app.run(host='0.0.0.0', port='8080')

