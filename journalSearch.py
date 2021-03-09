"""Playing with the Elsevier API client

Thinking that ultimately we will want to
    query for set of journals, for a specific "loadedAfter" date
    get all papers that contain "mice" in title, abstract or full text
    and
    output the PDFs for those papers named by PMID_nnnn.pdf.

    Then those PDFs can be loaded by the littriageload.

What is implemented here (playing):
    just query for a set of journals and a "loadedAfter" date,
    output papers with "mice OR mouse" in text:
        pmid, pii, doi, title

What I've learned about the Elsevier client and the API:
0) IMPORTANT: we have an apikey and institutional token (for Jax) that we
    cannot make publicly available.
    So these cannot be in a public github repository.
    Currently these live in config.json

1) This code is using the PUT API to ScienceDirect (full text search).
    I could not get any date queries to work using the legacy GET API.
    All the notes below are for the PUT API which takes a json query param
    payload and returns a json result set.

    See  https://dev.elsevier.com/tecdoc_sdsearch_migration.html

2) waiting for response from Brian Smith at Elsevier about how we can get PDFs.
    The APIs do not provide a way to download PDFs.

3) The json results payload does not include PMID.
    I do a separate API FullDoc() call to get PMID.
    Maybe there is a bulk way to pass pii IDs to Scopus?
    NOTE papers can appear in ScienceDirect before they have their PMID.
    So this downloader may want to skip papers UNTIL their PMID appears here.
    (do we ever get papers from Elsevier journals that don't eventually appear
    in pubmed?)

4) Date ranges: API only supports "loadedAfter date" - cannot specify ranges

5) JOURNAL Searching: "pub" field is where you specify the journal name.
    It does not support an exact match, it searches for matching words (or
    quoted phrases).
    So search for "Developmental Biology" matches journals
        'Developmental Biology',
        'Current Topics in Developmental Biology',
        'Seminars in Cell & Developmental Biology', etc.
    I don't think it does stemming, but it appears to handle plurals, e.g.,
        searching for "Cells" returns the "Cell" journal.
    This is kind of annoying for us when we want to search by exact journals.

    We need to use the exact journal names instead of our journal abbreviations.
    I.e., "Dev Biol" doesn't match anything.

6) FULL TEXT searching: "qs" field specifies your text. It supposedly searches
    the full text but not the references section.
    Supports "AND" and "OR" and quoted phrases.
    Does not seem to support wildcards.
    I haven't determined if it does stemming or not.

    I have noticed that searching "qs" for "mice OR mouse" returns more papers
    than just "mice". So I think we should use that.
"""

from elsclient import ElsClient
from elsprofile import ElsAuthor, ElsAffil
from elsdoc import FullDoc, AbsDoc
from elssearch import ElsSearch
import json
    
## Load configuration
con_file = open("config.json")
config = json.load(con_file)
con_file.close()

## Initialize Elsevier API client
client = ElsClient(config['apikey'])
client.inst_token = config['insttoken']

FIELDSEP = '|'
OUTPUT_HEADER = FIELDSEP.join([
                        'PMID',
                        'pii',
                        'DOI',
                        #'journal',
                        'title',
                        ])

# ------------------------------
def formatResult(r):
    """ Return formatted text from a ScienceDirect query result r.
        r is json object.
    """
    # load full document info from API to get PMID
    pii = r['pii']
    #pii_doc = FullDoc(sd_pii=pii)

    if True or pii_doc.read(client):
        #data = pii_doc.data
        #pmid = data.get('pubmed-id', 'no_pmid')
        text = FIELDSEP.join([
                        #pmid,
                        pii,
                        r['doi'], # = data['coredata']['prism:doi'],
                        r['loadDate'],
                        #r['sourceTitle'],
                        #r['title'][:20],
                        ])
    else:
        text = "Read failed for pii='%s'" % pii
    return text
# ------------------------------

### Main

journals = ['Developmental Biology', 
            'Archives of Biochemistry and Biophysics',
           ]

for j in journals:
    query = {'pub'        : '"%s"' % j,
             'qs'         : 'mice OR mouse',
             'loadedAfter': '2020-12-01T00:00:00Z',
             'display'    : { 'sortBy': 'date' }
             }
    docSearch = ElsSearch(query, 'sciencedirect')
    docSearch.execute(client, get_all=True)

    print("%s: %d total search results" % (j, docSearch.tot_num_res))
    numJournalResults = 0
    articleCounts = {}  # articleCounts[jname] is num of articles 

    if docSearch.tot_num_res == 0: continue

    for r in docSearch.results[:]:
        srcTitle = r['sourceTitle']
        articleCounts[srcTitle] = articleCounts.get(srcTitle, 0) +1
        if srcTitle != j:       # skip if not the right journal name
            continue
        print(formatResult(r))
        numJournalResults += 1
    print("%s: %d matching references" % (j, numJournalResults))
    print(articleCounts)

