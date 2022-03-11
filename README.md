# project-information-retrieval
Intro to Data Mining class project.  Implement a Google API, and conduct word searches using Whoosh on files.
Launched on repl.it, the project can be observed here (please note repl needs to wake up and may take time to launch):

https://project-information-retrieval.sp1222.repl.co/

NOTE: Google Chrome throws a certificate transparency error, the site should work fine in incognito mode or firefox.
  Will look into a solution in the near future.


Use a Google API key to implement a Google search for keywords entered by the user and presents the collected
information to the user.  This includes a linked image if available and linked title of the page,
the originating website's home page, and a small snippet of the data collected.  Google searches
will display 10 results.

Local searches are those conducted on files that are stored locally, which includes a list of lyrics, groceries, and beer.
The project utilizes the Whoosh package, which is a 'programmer library for creating a search engine.'
I use it to conduct searches using its default BM25F scoring system on indices
of documents created using unicode from uploaded files.

What I have learned is how, particularly with song information, the artist tag did not yield a
high score during the multifield search, so I was gave a field boost of 2.0 to 'artist' to yield better
results.  Another detail I noticed is how drastically different the search results can be when searching
single field (which I chose to be lyrics) vs searching multi field (artist, lyrics, and song).  searching
'queen' with both showcases the change of results of the searches with artist having the field boost.
