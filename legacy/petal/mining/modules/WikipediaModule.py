import wikipedia

from .module import Module

SCRAPE_FIELDS = {'content', 'summary', 'coordinates', 'links', 'references', 'images', 'title'}

class WikipediaModule(Module):
    '''
    This is the Module for downloading Wikipedia articles for a particular species.
    Its type signature takes a Species and returns a WikipediaArticle:Article, as shown below.
    In neo4j, these two nodes will be connected by the specified labels as well.
    After this is defined, all that matters is the process() function, which takes a Species node and returns a list of Transaction objects that will add WikipediaArticle nodes to the database.
    '''
    def __init__(self, in_label='Species', out_label='WikipediaArticle:Article', connect_labels=('MENTIONED_IN_ARTICLE', 'MENTIONS_SPECIES'), name='Wikipedia'):
        Module.__init__(self, in_label, out_label, connect_labels, name)

    def process(self, node):
        # Lookup the species based on its name. Make sure that all Species objects have this attribute!!
        name = node['name']
        try:
            results = wikipedia.search(name) # Use Wikipedia API to get list of results from searching the species name, throttled to 10 results by default
            properties = list()
            for result in results: # Create a transaction for each result
                result_properties = dict() # Properties for the neo4j node, populated below
                try:
                    page = wikipedia.page(result, auto_suggest=True, redirect=True, preload=True) # Use wikiAPI to load the actual page
                    for field in SCRAPE_FIELDS: # Store only the desired properties (above) in the node properties
                        try:
                            result_properties[field] = getattr(page, field)
                        except KeyError:
                            pass
                except wikipedia.exceptions.WikipediaException as e:
                    pass
                properties.append(self.default_transaction(result_properties)) # Only create default transaction objects
                # In the future, use self.custom_transaction() and self.query_transaction() for more complicated Data Mining Modules
            return properties
        except Exception as e:
            return None

