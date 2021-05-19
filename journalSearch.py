"""Playing with the Elsevier API and SciDirectClient.py client library.

What is implemented here:
    query for set of journals, for a specific "loadedAfter" date,
    get all papers that contain "mice" in title, abstract or full text
    (omitting reference section)
    and
    download the PDFs for those papers named by PMID_nnnn.pdf.
    Currently writes them into a subdirectory named "pdfs/"
    (this code doesn't check the db to see if we already have the PMID. The
    production downloader will want to do this.)

Usage: python journalSearch.py

What I've learned about the API:
0) IMPORTANT: we have an apikey and institutional token (for Jax) that we
    cannot make publicly available.
    So these cannot be in a public github repository.
    Currently these live in config.json - MOVING THESE TO MGICONFIG

1) This code is using the PUT API to ScienceDirect (full text search).
    See SciDirectSearch in SciDirectClient.py.
    I could not get any date queries to work using the legacy GET API.
    All the notes below are for the PUT API which takes a json query param
    payload and returns a json result set.

    See  https://dev.elsevier.com/tecdoc_sdsearch_migration.html

3) The json results payload does not include PMID.
    The SciDirectReference class does a separate API call to get the PMID,
    other bits of metadata, and the PDF.
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

    We need to use the exact journal names instead of MGI journal abbreviations.
    I.e., "Dev Biol" doesn't match anything.

6) FULL TEXT searching: "qs" field specifies your text. It supposedly searches
    the full text but not the references section.
    Supports "AND" and "OR" and quoted phrases.
    Does not seem to support wildcards.
    I haven't determined if it does stemming or not.
"""

from SciDirectLib import ElsClient, SciDirectSearch, SciDirectReference
import json
    
FIELDSEP = '|'

# ------------------------------
def formatResult(r):
    """ Return formatted text from a SciDirectReference object.
    """
    text = FIELDSEP.join([
                    r.getPmid(),
                    #r.getPii(),
                    r.getDoi(),
                    r.getPubType(),
                    r.getVolume(),
                    r.getLoadDate()[:10],
                    r.getPublicationDate()[:10],
                    r.getTitle()[:10],
                    ])
    return text
# ------------------------------

### Main

ACTUALLY_WRITE_PDFS = False     # skip writing if debugging
AFTER_DATE = '2021-04-01'       # get articles added after this date

# The MGI journals that are available at SciDirect
# These are taken from Harold's list of journals searched via Quosa.
#  Are there any other MGI monitored journals that are at Elsevier/SciDirect?
class Journal(object):  # simple journal struct
    def __init__(self, mgiName, elsevierName):
        self.mgiName = mgiName
        self.elsevierName = elsevierName

journals = [
    Journal('Arch Biochem Biophys', 'Archives of Biochemistry and Biophysics'),
    Journal('Dev Biol', 'Developmental Biology'),
    Journal('J Mol Cell Cardiol','Journal of Molecular and Cellular Cardiology'),
    Journal('Brain Research', 'Brain Research'),
    Journal('Experimental Cell Research', 'Experimental Cell Research'),
    Journal('Experimental Neurology', 'Experimental Neurology'),
    Journal('Neuron', 'Neuron'),
    Journal('Neurobiology of Disease', 'Neurobiology of Disease'),
    Journal('Bone', 'Bone'),
    Journal('Neurosci Letters', 'Neuroscience Letters'),
    Journal('J Invest Dermatol', 'Journal of Investigative Dermatology'),
    Journal('Cancer Cell', 'Cancer Cell'),
    Journal('Cancer Lett', 'Cancer Letters'),
    Journal('Neuroscience', 'Neuroscience'),
    Journal('Neurobiology of Aging', 'Neurobiology of Aging'),
    Journal('Matrix Biology', 'Matrix Biology'),
    Journal('J Bio Chem', 'Journal of Biological Chemistry'),
   ]

# Would like to understand what the SciDirect pubTypes are. Collect them
pubTypes = {}       # pubTypes['type'] = num of refs with that type

print("Looking for Papers after %s" % AFTER_DATE)

## Load API key and Jax institution token from config file
## TODO: get these values from env instead and have these added to mgiconfig
con_file = open("config.json")
config = json.load(con_file)
con_file.close()

## Initialize Elsevier API client
elsClient = ElsClient(config['apikey'], inst_token=config['insttoken'])

for journal in journals[:]:
    jName = journal.elsevierName
    query = {'pub'        : '"%s"' % jName,
             'qs'         : 'mice',
             'loadedAfter': AFTER_DATE + 'T00:00:00Z',
             'display'    : { 'sortBy': 'date' }
             }
    search = SciDirectSearch(elsClient, query, getAll=True).execute()

    print("%s: %d total search results" % (jName, search.getTotalNumResults()))

    # keep track of matching journal names. The search may match journals
    #  that are not the ones we want
    articleCounts = {}      # articleCounts[jName] is num of articles 
    numJournalResults = 0   # num of refs from the journal we're looking for 

    numPMIDs = 0            # num of refs w/ PMIDs
    numPDFs = 0             # num of PDFs written for this journal

    if search.getTotalNumResults() == 0: continue

    for r in search.getIterator():
        try:
            journal = r.getJournal()
            articleCounts[journal] = articleCounts.get(journal, 0) +1
            if journal == jName:       # skip if not the right journal name
                numJournalResults += 1
                print(formatResult(r))

                # gather pubtypes
                pubType = r.getPubType()
                pubTypes[pubType] = pubTypes.get(pubType, 0) +1

                # write pdf if we have PMID
                if r.getPmid() != 'no PMID':
                    numPMIDs += 1 
                    if ACTUALLY_WRITE_PDFS:
                        numPDFs += 1 
                        fname = 'pdfs/PMID_%s.pdf' % r.getPmid()
                        with open(fname, 'wb') as f:
                            f.write(r.getPdf())
        except: # in case we get any exceptions working w/ this r, let's see it
            print("Reference exception\n")
            print(json.dumps(r.getDetails(), sort_keys=True, indent=2))
            raise

    print("%s: %d matching references, %d w/ PMIDs, %d PDFs written" % \
                            (jName, numJournalResults, numPMIDs, numPDFs))
    print("Summary of matching journal names:")
    print(articleCounts)

print()
print("Summary of pubTypes across all journals:")
for k in sorted(pubTypes.keys()):
    print("%s: %d" % (k, pubTypes[k]))
