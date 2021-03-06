from ..libraries.encyclopedia_of_life.eol_api import EOL_API
from bitflow.utils.module import Module

from pprint import pprint

from bs4 import BeautifulSoup
from requests import get
from time import sleep

from pprint import pprint

import sys, re, os

search_url = 'https://eol.org/search?utf8=%E2%9C%93&q={}'
data_url = 'https://eol.org{}/data'
eol_url = 'https://eol.org{}'

'''
WARNING: Some of the following code disobeys robots.txt of particular websites.
  Thus, it is disabled by default and only left as reference.
  Use at your own risk.

       o     O
     __|_____|___
    |    --      |
    |  ( o )   ( o )
  { |        /   |
    |     [wwww]  < *Exterminate all humans.txt* )
    [____________|
       |   |              /Vvvv/
  _____|___|____          |___/
 /______________\_________/   |
 |              |             /
 | ( / )  ( + ) |__|__|__|_|_/
 |              |
 | [ -vV--vV-]  |
 |              |
 |______________/
'''

def get_data_page(query):
    '''
    Use EOL /search/ to find a particular page. 
    *DEFIES ROBOTS.txt* (/search/ directive disencouraged)
    '''
    expanded = '+'.join(query.split()) + '+'
    url = search_url.format(expanded)

    html = get(url).text
    processed = BeautifulSoup(html, 'html.parser')
    top = processed.find(attrs={'class' : 'search-result'})
    link = top.find('a')
    nav = link.get('href')
    return data_url.format(nav)


def read_data(page_url):
    '''
    Read the data page of an EOL url.
    *OBEYS ROBOTS.txt*
    '''
    extracted = []

    data = get(page_url)
    processed = BeautifulSoup(data.text, 'html.parser')
    rows = processed.find_all(attrs={'class', 'js-data-row'})
    for row in rows:
        source = row.find(attrs={'class', 'trait-source'})
        link = source.find('a')
        nav  = eol_url.format(link.get('href'))
        source_text = link.text
        data_div = row.find(attrs={'class', 'trait-data'})
        subdivs  = data_div.find_all('div')
        header = subdivs[0].find('div').text.strip()
        entry  = subdivs[1].text.strip()
        row_p = (nav, source_text, header, entry)
        extracted.append(row_p)
    return extracted

def search(query):
    '''
    Search for a query on EOL.
    
    PREFERRED: Use EOL neo4j API instead.

    *DEFIES ROBOTS.txt*
    '''
    page_url = get_data_page(query)
    return read_data(page_url)

class EOLModule(Module):
    '''
    Collect data from a particular Taxon's page

    Usage of the /search/ directive is disabled by default. Only enable this if EOL allows it.

    *OBEYS ROBOTS.txt*
    '''
    def __init__(self, in_label='Taxon', out_label='EOLData', connect_labels=('MENTIONED_IN_DATA', 'MENTIONS_SPECIES'), name='EOL'):
        Module.__init__(self, in_label, out_label, connect_labels, name)
        self.api = EOL_API()

    def process(self, previous):
        '''
        Download EOL data given a particular Taxon

        :param previous: neo4j transaction for a taxon.
        '''
        name = previous.data['name']
        uuid = previous.data['uuid']
        query = ' '.join(['MATCH (p:Page)-[:trait|:inferred_trait]->(t:Trait), (t)-[:predicate]->(pred:Term)',
                          'WHERE p.canonical = \'{name}\''.format(name=name),
                          'OPTIONAL MATCH (t)-[:object_term]->(obj:Term)',
                          'OPTIONAL MATCH (t)-[:units_term]->(units:Term)',
                          'OPTIONAL MATCH (p2:Page {page_id:t.object_page_id})'
                          'RETURN pred.name, pred.type, obj.name, units.name, t.measurement, p2.canonical',
                          'LIMIT 1000'])
        result = self.api.search(query)
        add_list = []
        for link, datatype, objname, unitname, measurement, target_name in result['data']:
            if datatype == 'measurement':
                if objname is None:
                    if unitname is None:
                        unitname = ''
                    if measurement is None:
                        measurement = ''
                    add_list.append(self.custom_transaction('Taxon', 'EOLMeasurement:EOLData', (link, link), {'name': link, 'units': unitname, 'value': measurement}, from_uuid=uuid))
                else:
                    add_list.append(self.custom_transaction('Taxon', 'EOLObject:EOLData', (link, link), {'value': objname}, from_uuid=uuid))
            elif target_name is not None:
                if '\'' not in target_name:
                    add_list.append(self.query_transaction(query='MATCH (n:Taxon) WHERE n.uuid = \'{}\' MATCH (m:Taxon) WHERE m.name = \'{}\' MERGE (n)-[:{}]->(m)'.format(uuid, target_name, link)))
        return add_list
