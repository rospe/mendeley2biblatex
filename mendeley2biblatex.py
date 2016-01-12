#!/usr/bin/env python
# -*- coding: utf-8 -*-


"""
    \file mendeley2biblatex.py
	\author Peter Rosina, University of Augsburg - rosina@ds-lab.org
	\date 2014.10
    \author François Bianco, University of Geneva – francois.bianco@unige.ch
    \date 2012.09

    \mainpage Mendeley To BibLaTeX convertor

    This script converts Mendeley SQlite database to BibLaTeX file.

    \section Infos

     mendeley2bibtex.py was written by François Bianco, University of Geneva
– francois.bianco@unige.ch in order to get a correct conversion of Mendely
database to BibTeX not provided by the closed source Mendeley Desktop software.

    First locate your database. On Linux systems it is:
ls ~/.local/share/data/Mendeley\ Ltd./Mendeley\ Desktop/your@email.com@www.mendeley.com.sqlite

    On Windows it is:
    C:\\Users\\Username\\AppData\\Local\\Mendeley\ Ltd\\Mendeley\ Desktop\\your@email.com@www.mendeley.com.sqlite

    Make a copy of this file, as we assume no responsability for loss of data.

    Then run mendeley2bibtex.py on your file with

        ./mendeley2bibtex.py -f foldername -o mendeley.bib mendeley.sqlite


    \section Copyright

    Copyright © 2012 François Bianco, University of Geneva –
francois.bianco@unige.ch

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.

    See COPYING file for the full license.

    \section Updates

    2012.09:
        First Version
    2014.10:
        Second Version


"""

import sys
from optparse import OptionParser
import sqlite3
import re

version = '0.01'

def dict_factory(cursor, row):
    """A function to use the SQLite row as dict for string formatting"""
    d = {}
    for idx, col in enumerate(cursor.description):
        if row[idx]:
            d[col[0]] = row[idx]
        else:
            d[col[0]] = ''
    return d

def addContributors(db, entry, dbRole, role):
    c = db.cursor()
    c.execute('''
    SELECT lastName, firstNames
    FROM DocumentContributors
    WHERE documentId = ?
    AND contribution = "'''+dbRole+'''"
    ORDER BY id''', (entry['id'],))
    contributors_list = c.fetchall()
    contributors = []
    for contributor in contributors_list:
        #check for firstname
        if contributor[1]:
            contributors.append(', '.join(contributor))
        #else it is an organization, hence omit comma
        else:
            contributors.append('{'+contributor[0]+'}')
    entry[role] = ' and '.join(contributors)

def addAddress(entry):
    address = []
    if entry['city']:
        address.append(entry['city'])
    if entry['country']:
        address.append(entry['country'])
    entry['address'] = ', '.join(address)

def getFolderQuery(mendeley_folder):
    '''returns all relevant subfolder ids'''
    if not mendeley_folder:
        return '''in_folder_set(id) AS ( SELECT id FROM Folders )'''
    return '''parent_of(id, parentId) AS ( SELECT id, parentId FROM Folders ),
        in_folder_set(parentId) AS ( SELECT id from Folders WHERE name="{}"
            UNION ALL
            SELECT id FROM parent_of JOIN in_folder_set USING (parentId) )'''.format(mendeley_folder)

def convert(db_name, bibtex_file=sys.stdout, quiet=False, mendeley_folder=""):
    """Converts Mendely SQlite database to BibTeX file
    @param db_name The Mendeley SQlite file
    @param bibtex_file The BibTeX file to output the bibliography, if not
supplied the output is written to the system standard stdout.
    @param quiet If true do not show warnings and errors
    """
    
    db = sqlite3.connect(db_name)
    c = db.cursor()
    #c.row_factory = sqlite3.Row # CANNOT be used with unicode string formatting
                                 # since it expect str indexes, and we are using
                                 # unicode string... grrr... ascii is not dead
    c.row_factory = dict_factory # allows to use row (entry) as a dict with
                                 # unicode keys.
                                 
    if sys.stdout != bibtex_file:
        f = open(bibtex_file,'wb')
        #f.write(("""This file was generated automatically by Mendeley To BibTeX python script.\n\n""").encode())
    else:
        f = bibtex_file
        
    query = '''WITH RECURSIVE
    {}
    SELECT
        D.id,
        D.chapter,
        D.citationKey,
        D.city,
        D.country,
        D.day,
        D.doi,
        D.dateAccessed,
        D.deletionPending,
        D.edition,
        D.institution,
        D.isbn,
        D.issn,
        D.issue,
        D.medium,
        D.month,
        D.note,
        D.pages,
        D.publication,
        D.publisher,
        D.seriesEditor,
        D.series,
        D.sourceType,
        D.title,
        D.type,
        D.volume,
        D.year,
        DU.url
    FROM Documents D
    LEFT JOIN DocumentCanonicalIds DCI
        ON D.id = DCI.documentId
    LEFT JOIN DocumentUrls DU
        ON D.id = DU.documentId
    LEFT JOIN DocumentFolders DF
        ON D.id = DF.documentId
    WHERE D.confirmed = "true" AND
    D.deletionPending = "false" AND
    DF.folderID IN in_folder_set
    GROUP BY D.citationKey
    ORDER BY D.citationKey
    ;'''.format(getFolderQuery(mendeley_folder))
    
    citationTypes = {'JournalArticle' : 'article',
        'ConferenceProceedings' : 'inproceedings',
        'Book' : 'book',
        'BookSection' : 'incollection',
        'Thesis' : 'thesis',
        'Generic' : 'misc',
		'Hearing' : 'misc',
        'WebPage' : 'online',
        'Report' : 'report',
        'Bill' : 'misc',
        'MagazineArticle' : 'article',
        'EncyclopediaArticle' : 'inreference',
        'Patent' : 'patent',
        'WorkingPaper' : 'report'
    }

    replaceAttributes = {'address' : 'address',
        'author' : 'authors',
        'booktitle' : 'publication',
        'chapter' : 'chapter',
        'urldate' : 'dateAccessed',
        'day' : 'day',
        'doi' : 'doi',
        'editor' : 'editor',
        'howpublished' : 'medium',
        'institution' : 'institution',
        'isbn' : 'isbn',
        'issn' : 'issn',
        'issue' : 'issue',
        'journaltitle' : 'publication',
        'month' : 'month',
        #'note' : 'note',
        #'number' : 'issue', #mendeley does not differentiate between number and issue
        'organization' : 'institution',
        'pages' : 'pages',
        'publisher' : 'publisher',
        'series' : 'series',
        'title' : 'title',
        'url' : 'url',
        'volume' : 'volume',
        'year' : 'year'
    }
    
    for entry in c.execute(query):
        entries = [] 
        addContributors(db,entry, "DocumentAuthor","authors")
        addContributors(db,entry, "DocumentEditor","editor")
        addAddress(entry)

        for attributeBibLatex,attributeMendeley in replaceAttributes.items():
            if entry[attributeMendeley]:
                escapedValue = entry[attributeMendeley]
                if isinstance(escapedValue, str) or attributeBibLatex == "url":
                    if not attributeBibLatex == "url":
                        escapedValue = escapedValue.replace(u"~", "$\sim$")
                        escapedValue = escapedValue.replace("\\&","&").replace("&","\\&")  #escape & and not \&
                    else:
                        if isinstance(escapedValue, bytes):
                            escapedValue = escapedValue.decode("utf-8")                
                    entries.append(u'''    {key} = "{value}"'''.format(key=attributeBibLatex, value=escapedValue))
                else:
                    entries.append(u'''    {key} = {{{value}}}'''.format(key=attributeBibLatex, value=escapedValue))

        formatted_entry = u''
        try:
            formatted_entry = u'''\n@{entrytype}{{{citationKey},\n'''.format(entrytype=citationTypes[entry['type']], citationKey=entry['citationKey'])+''',\n'''.join(entries)+'''\n}'''
        except KeyError:
            if not quiet:
                print (u'''Unhandled entry type {0}, please add your own template.'''.format(entry['type']))

        f.write(formatted_entry.encode('utf-8'))

    if sys.stdout != bibtex_file:
        f.close()


def main() :
    """Set this script some command line options. See usage."""

    global version

    parser = OptionParser(usage='''%prog [-f foldername -o out.bib] mendeley.sqlite.\n\nAttention: Script ignores "Unsorted", "deletionPending" (in trash) and unconfirmed entries.''' ,version='%prog '+version)

    parser.add_option('-q', '--quiet', action='store_true', default=False,
                dest='quiet', help='Do not display information.')
    parser.add_option("-o", "--output", dest="bibtex_file", default=sys.stdout,
                help="BibTeX file name, else output will be printed to stdout.")
    parser.add_option("-f", "--folder", dest="mendeley_folder", default="",
                help="Mendeley folder name, else whole sorted DB will be used.")
    
    (options, args) = parser.parse_args()

    if not args :
        parser.error('''No file specified''')

    db_name = args

    convert(db_name[0], options.bibtex_file, options.quiet, options.mendeley_folder)

if __name__ == "__main__":
    try :
        main()
    except (KeyboardInterrupt) :
        print ("Interrupted by user.")
