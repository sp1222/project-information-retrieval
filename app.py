from dotenv import load_dotenv
from flask import Flask, render_template, request
from googleapiclient.discovery import build
from whoosh import scoring
from whoosh.fields import Schema, TEXT, ID, NUMERIC
from whoosh.qparser import QueryParser
from whoosh.qparser import MultifieldParser
import csv
import os
import whoosh.index as whoosh_index


app = Flask(__name__)
FILE_NAMES = {'lyrics':
                 {'BM25F Multifield': ['artist', 'lyrics', 'song'],
                  'BM25F Singlefield': 'lyrics'},
                          'beer':
                              {'BM25F Multifield': ['beer', 'style', 'brewery', 'description'],
                               'BM25F Singlefield': 'beer'},
                          'grocery':
                              {'BM25F Multifield': ['product', 'brand', 'category', 'parent_category'],
                               'BM25F Singlefield': 'product'}
             }
results_global = []
LOCAL_LIMIT = 1000
HIGHLIGHT_MAX = 1


def configure():
    load_dotenv()


class hit_object:
    '''
    hit object class
    '''
    def __init__(self, rank, docnum, score, snippet, dictionary):
        self.rank = rank
        self.docnum = docnum
        self.score = score
        self.snippet = snippet
        self.dictionary = dictionary


def init_lyrics_schema():
    '''
    init lyrics schema
    :return: Schema for lyrics
    '''
    # Rank, Song, Artist, Year, Lyrics, Source
    return Schema(id=ID(unique=True, stored=True), rank=NUMERIC(stored=True),
                  song=TEXT(stored=True), artist=TEXT(field_boost=2.0, stored=True), year=NUMERIC(stored=True),
                  lyrics=TEXT(stored=True), source=NUMERIC(stored=True))


def init_beer_schema():
    '''
    init beer schema
    :return: Schema for beer
    '''
    return Schema(id=ID(unique=True, stored=True), beer=TEXT(stored=True),
                  style=TEXT(stored=True), brewery=TEXT(field_boost=2.0, stored=True),
                  description=TEXT(stored=True), rating=NUMERIC(float, stored=True),
                  abv=NUMERIC(float, stored=True), minibu=NUMERIC(stored=True), maxibu=NUMERIC(stored=True))


def init_grocery_schema():
    '''
    init grocery schema
    :return: Schema for grocery
    '''
    return Schema(id=ID(unique=True, stored=True), product=TEXT(stored=True),
                  variant_price=NUMERIC(float, stored=True), variant_uom=TEXT(stored=True),
                  variant_alt_price=NUMERIC(float, stored=True), variant_alt_uom=TEXT(stored=True),
                  brand=TEXT(field_boost=2.0, stored=True), category=TEXT(stored=True), parent_category=TEXT(stored=True))


def add_docs_to_lyrics_index(idx, name):
    '''
    add to lyrics index
    :param idx: index we are writing to
    :param name: name of file we are writing from
    '''
    # Rank, Song, Artist, Year, Lyrics, Source
    f = open(os.getcwd() + '\\files\\' + name + '.csv', 'r', encoding='utf8', errors='ignore')
    reader = csv.DictReader(f)
    writer = idx.writer()
    id = -1
    for row in reader:
        id += 1
        try:
            writer.add_document(id=str(id), rank=str(row['Rank']), song=row['Song'], artist=row['Artist'],
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


def add_docs_to_beer_index(idx, name):
    '''
    add to beer index
    :param idx: index we are writing to
    :param name: name of file we are writing from
    '''
    f = open(os.getcwd() + '\\files\\' + name + '.csv', 'r', encoding='utf8', errors='ignore')
    reader = csv.DictReader((line.replace('\0', '') for line in f), delimiter = ',')
    writer = idx.writer()
    id = -1
    for row in reader:
        id += 1
        writer.add_document(id=str(id), beer=row['Beer'], style=row['Style'], brewery=row['Brewery'],
                            description=row['Description'],
                            rating=str(float(row['Rating'])), abv=str(float(row['ABV'])), minibu=str(row['Min IBU']),
                            maxibu=str(row['Max IBU']))
    f.close()
    writer.commit()


def add_docs_to_grocery_index(idx, name):
    '''
    add to grocery index
    :param idx: index we are writing to
    :param name: name of file we are writing from
    '''
    f = open(os.getcwd() + '\\files\\' + name + '.csv', 'r', newline='', encoding='utf-8-sig', errors='ignore')
    reader = csv.DictReader((line.replace('\0', '') for line in f), delimiter = ',', dialect='excel')
    writer = idx.writer()
    id = -1
    for row in reader:
        id += 1
        writer.add_document(id=str(id), product=row['Name'],
              variant_price=str(float(row['Variant Price'])), variant_uom=row['Variant UOM'],
              variant_alt_price=str(float(row['Variant Alt Price'])), variant_alt_uom=row['Variant Alt UOM'],
              brand=row['Brand'], category=row['Category'], parent_category=row['Parent Category'])
    f.close()
    writer.commit()


def init_index(name, function):
    '''
    init index depending on which file name we are passing
    :param name: name of file for index we are initializing
    :param function: function called for the schema we are looking to index with
    :return: whoosh index
    '''
    return whoosh_index.create_in(os.getcwd() + '\\indices\\' + name + '_dir', schema=function())


def multifield_search_query(idx, word, fields=[]):
    '''
    run multifield query using the keyword entered.
    :param idx: index being searched
    :param word: word being parsed
    :param fields: fields of interest in the index
    :return: dictionary of search results
    '''
    d = {}
    qp = MultifieldParser(fields, idx.schema)
    q = qp.parse(word)

    with idx.searcher() as searcher:
        result = searcher.search(q, limit=LOCAL_LIMIT)
        res = []
        for hit in result:
            highlight = ''
            for field in fields:
                if len(hit.highlights(field)) > 0:
                    highlight += hit.highlights(field, top=HIGHLIGHT_MAX) + ' ... '
            res.append(hit_object(rank=hit.rank, docnum=hit.docnum, score=hit.score, snippet=highlight
                                  , dictionary=hit.fields()))
        d['searchTime'] = result.runtime
        d['totalResults'] = result.scored_length()
        d['items'] = res
    return d


def simple_search_query(idx, word, field=''):
    '''
    run simple query using the keyword entered.
    :param idx: index being searched
    :param word: word being parsed
    :param field: field of interest in the index
    :return: dictionary of search results
    '''
    d = {}
    qp = QueryParser(field, schema=idx.schema)
    q = qp.parse(word)

    with idx.searcher() as searcher:
        result = searcher.search(q, limit=LOCAL_LIMIT)
        res = []
        for hit in result:
            res.append(
                hit_object(rank=hit.rank, docnum=hit.docnum, score=hit.score, snippet=hit.highlights(field, top=3)
                           , dictionary=hit.fields()))
        d['searchTime'] = result.runtime
        d['totalResults'] = result.scored_length()
        d['items'] = res
    return d


def web_search(k, **kwargs):
    '''
    search results of a keyword using Google API
    :param k: keyword being searched
    :param kwargs: number of arguments to return from Google API
    :return: dictionary of search results
    '''
    if k:
        service = build("customsearch", "v1", developerKey=os.getenv('api_key'))
        r = service.cse().list(q=k, cx=os.getenv('cse_key'), **kwargs).execute()
        d = {}
        d['searchTime'] = r['searchInformation']['searchTime']
        d['totalResults'] = r['searchInformation']['formattedTotalResults']
        d['items'] = r['items']
        return d
    return None


@app.route('/lyrics/<rank>=<song>/')
def lyrics(rank, song):
    '''
    lyrics page
    :param rank: rank of the search result
    :param song: song returned at given ranking
    :return: html template to render
    '''
    global results_global
    song_info = results_global[int(rank)].dictionary
    return render_template('lyrics.html', song_info=song_info)


@app.route('/beer/<rank>=<beer>/')
def beer(rank, beer):
    '''
    beer page
    :param rank: rank of the search result
    :param beer: beer returned at given ranking
    :return: html template to render
    '''
    global results_global
    beer_info = results_global[int(rank)].dictionary
    return render_template('beer.html', beer_info=beer_info)


@app.route('/grocery/<rank>=<product>/')
def grocery(rank, product):
    '''
    grocery page
    :param rank: rank of the search result
    :param grocery: grocery returned at given ranking
    :return: html template to render
    '''
    global results_global
    product_info = results_global[int(rank)].dictionary
    return render_template('grocery.html', product_info=product_info)


@app.route('/', methods=['POST', 'GET'])
def home():
    '''
    home page
    :return: html template to render
    '''
    # dictionary of search types with their respective function calls.
    scoring_methods = {'BM25F Multifield': multifield_search_query,
                       'BM25F Singlefield': simple_search_query}
    if request.method == 'POST':
        keyword = request.form['keyword']
        if keyword is not None or keyword.isspace == False or keyword != '':
            medium = str()
            results = list()
            file = str()
            if request.form['button'] == 'Search Locally':
                file = request.form['file']
                score_method = request.form['score_method']
                medium = 'Locally'
                search_index = whoosh_index.open_dir(os.getcwd() + '\\indices\\' + file + '_dir')
                results = scoring_methods[score_method](search_index, keyword, FILE_NAMES[file][score_method])
                global results_global
                results_global = results['items']

            elif request.form['button'] == 'Search Google':
                medium = 'Google'
                results = web_search(keyword, num=10)

            return render_template('home.html', keyword=keyword, medium=medium, results=results,
                                   files=list(FILE_NAMES.keys()), scoring_methods=list(scoring_methods.keys()),
                                   file=file)

    return render_template('home.html', keyword='', medium='', results=[],
                           files=list(FILE_NAMES.keys()), scoring_methods=list(scoring_methods.keys()), file='')


if __name__ == '__main__':
    print('Getting Config')
    configure()
    # initialize indices if they do not already exist for each .csv file.
    index_schema_functions = {'lyrics': init_lyrics_schema,
                              'beer': init_beer_schema,
                              'grocery': init_grocery_schema
                              }
    index_add_doc_functions = {'lyrics': add_docs_to_lyrics_index,
                               'beer': add_docs_to_beer_index,
                               'grocery': add_docs_to_grocery_index
                               }
    # made it so that i don't have to rebuild these every single time..
    for name in list(FILE_NAMES.keys()):
        print('initializing '+ name + ' index')
        if not os.path.exists(os.getcwd() + '\\indices\\' + name + '_dir'):
            os.mkdir(os.getcwd() + '\\indices\\' + name + '_dir')
            index = init_index(name, index_schema_functions[name])
            index_add_doc_functions[name](index, name)
    app.run(debug=True, host='0.0.0.0', port=5000)
    
    

#    Note, for repl.it, all back double slashes "\\" need to change to single forward slashes "/"
#    app.run(debug=True) changes to app.run(host='0.0.0.0', port='8080')

