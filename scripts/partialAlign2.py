#!/usr/bin/python3

import sys
import collections
import itertools
import logging
from argparse import ArgumentParser

logging.basicConfig(format='%(message)s',level=logging.INFO)

def tokenFreq(corpus) :
    """Returns a frequency dictionary of all types in corpus."""
    freq = collections.defaultdict(int)
    for l in corpus :
        for t in l :
            freq[t] += 1
    return dict(freq) # cast to enable invalid key exception

# Small quirk: skips anchor words appearing twice
# in the same sentence. Whatever.
def hapaxes(freq) :
    """Get a set of all hapaxes in a frequency distribution"""
    hapaxes = set()
    for token,cnt in iter(freq.items()) :
        if cnt==1 :
            hapaxes.add(token)
    return hapaxes

def hapaxPositions( hapaxes, corpus ) :
    """Returns a dictionary mapping all hapaxes to their position (sentence number) in corpus"""
    hapaxPos = {}
    for ind,l in enumerate(corpus) :
        for t in l :
            if t in hapaxes :
                hapaxPos[t] = ind
    return hapaxPos

def structurePositions(corpus):
    """Find some structural anchor points.

    Returns a list of tuples of form (n,i),
    where n is the canonical form of the tag and i is its line number in the corpus.
    They are sorted by i."""
    keywords = ['<p','<section', #HTML - neglecting never used WS
                '\\section','\\chapter' #LaTeX
                ]
    keywords += ['<h' + str(i) for i in range(1,7)]
    pos = []
    for ind,sent in enumerate(corpus):
        if len(sent) == 0:
            pos.append((kw,ind))
        for token in sent:
            for kw in keywords:
                if token.startswith(kw):
                    pos.append((kw,ind))
    return pos

def structures(huCorpus,enCorpus): # TODO: deprecated
    """Find parallel structuring in the corpora

    The function will determine whether both texts are structured in a similar way.
    HTML and LaTeX tags are considered.
    Returns a list of position pairs."""
    huKw = structurePositions(huCorpus)
    enKw = structurePositions(enCorpus)
    if len(huKw)!=len(enKw): # if the versions are differently tagged
        logging.warning('Versions differently structured ('+str(len(huKw))+' vs. '+str(len(enKw))+' tags).')

    pairs = []
    for i in range(len(huKw)):
        if huKw[i][0]!=enKw[i][0]: # if the tags are not parallel
            return [] # give up
        pairs.append((huKw[i][1],enKw[i][1]))
    return pairs # success

def uniqSort(l) :
    """Sorts an iterator by value, eliminating duplicates."""
    return [ p for p,g in itertools.groupby(sorted(l)) ]

def less(a,b) :
    """Comparison operator for 2-tuples.

    A tuple a is considered less than another tuple b exactly if both values of a are less than their correspondents in b.

    Note that this is not a total order.
    An ordering system based on it will thus sort tuples with crossing values in an arbitrary way."""
    return a[0]<b[0] and a[1]<b[1]

def tupsub(a,b) :
    return (a[0]-b[0],a[1]-b[1])

def maximalChain(pairs,secPairs) :
    """Find the longest sequence of anchor pairs that is equal in order for both corpora.

    The result is a list of sentence index pairs.
    It is very likely that these sentences correspond to each other.
    The input must be in ascending order. This may be achieved with uniqSort.
    The pairs in the second arguments are only considered if consistent between two primary pairs."""
    lattice = {}
    for p in pairs :
        bestLength = 0
        bestPredessor = None
        for q in pairs :
            if less(q,p) : # for all anchors occurring before p in both texts
                length,dummy = lattice[q]
                if bestLength<length+1 :
                    bestLength = length+1
                    bestPredessor = q
        lattice[p] = (bestLength,bestPredessor)
        # print bestLength,p,bestPredessor
    bestLength,p = max( (lattice[p][0],p) for p in pairs )
    chain = []
    while p :
        chain.append(p)
        length,p = lattice[p]
    chain.reverse()

    logging.debug('Unrefined chain: '+str(chain))

    if secPairs == []:
        return chain
    
    # use secondary pairs
    huSP, enSP = secPairs
    huInd = enInd = 0
    try:
        for p in chain[1:]:
            newPairs = []
            incongruent = False
            while huSP[huInd][1] < p[0] and enSP[enInd][1] < p[1]:
                if huSP[huInd][0] != enSP[enInd][0]: # if the tags differ
                    incongruent = True
                newPairs.append((huSP[huInd][1],enSP[enInd][1]))
                huInd += 1; enInd += 1
            if huSP[huInd][1] < p[0] or enSP[enInd][1] < p[1] or incongruent: # if this doesn't fit perfectly
                while huSP[huInd][1] < p[0]: # adapt the indices
                    huInd += 1
                while enSP[enInd][1] < p[1]:
                    enInd += 1
            else: # all is well
                chain += newPairs
    except IndexError:
        if huInd == len(huSP) and enInd == len(enSP):
            chain += newPairs
    
    logging.debug('Chain: '+str(uniqSort(chain)))
    return uniqSort(chain)

def selectFromChain( chain, maximalChunkSize, sentSizes, brutal ) : # TODO: implement brutality
    """Generate chunks from a chain of anchor points.

    chain -- list of anchor point position in the form of tuples.
    maximalChunkSize -- the maximal chunk size allowed.

    Returns a list of 2-tuples of sentence indices representing chunk borders
    and an int containing the lenght of the biggest chunk if the maximum had to be disregarded.

    The length of each chunk will be maximal, but lower than maximalChunkSize, if possible.
    The algorithm employed is greedy."""
    forced = 0
    filteredChain = [(0,0)] # SOF is always the beginning of the first chunk.
    huChunkSize, enChunkSize = 0,0
    lastPos,cursor = (0,0),(0,0) # pos of the last anchor and the last chunk border, respectively
    for p in chain[1:] :
        checkedP = False # whether we have tried everything possible about this p
        while not checkedP:
#            logging.debug(sentSizes[0][lastPos[0]:p[0]])
            huChunkSize += sum(sentSizes[0][lastPos[0]:p[0]])
            enChunkSize += sum(sentSizes[1][lastPos[1]:p[1]])
#            logging.debug('%s %s %s',cursor,lastPos,p)
            if huChunkSize>maximalChunkSize or enChunkSize>maximalChunkSize : # if currently tried chunk's too long in one version
                if lastPos!=cursor : # if we have an earlier anchor than p
                    huChunkSize -= sum(sentSizes[0][lastPos[0]:p[0]])
                    enChunkSize -= sum(sentSizes[1][lastPos[1]:p[1]])
                    assert huChunkSize <= maximalChunkSize >= enChunkSize
                    filteredChain.append(lastPos)
                elif brutal:
                    nShards = max(huChunkSize,enChunkSize)//maximalChunkSize+1
                    if huChunkSize > enChunkSize:
                        huShardSize = maximalChunkSize
                        enShardSize = maximalChunkSize*enChunkSize//huChunkSize
                    else:
                        enShardSize = maximalChunkSize
                        huShardSize = maximalChunkSize*huChunkSize//enChunkSize
                    while huChunkSize > maximalChunkSize or enChunkSize > maximalChunkSize :
                        huSearchPos,enSearchPos = cursor
                        while sum(sentSizes[0][cursor[0]:huSearchPos+1]) < huShardSize:
                            huSearchPos += 1
                        while sum(sentSizes[1][cursor[1]:enSearchPos+1]) < enShardSize:
                            enSearchPos += 1
                        searchPos = (huSearchPos,enSearchPos)
                        filteredChain.append(searchPos)
                        shardSizes = tuple(sum(sentSizes[l][filteredChain[-2][l]:filteredChain[-1][l]]) for l in range(2))
                        logging.debug('Shard of size %s created from %s to %s.',shardSizes,filteredChain[-2],filteredChain[-1])
                        cursor = searchPos
                        huChunkSize -= shardSizes[0]
                        enChunkSize -= shardSizes[1]
#                    logging.debug('\tShard of size %s created from %s to %s.',tuple(sum(sentSizes[l][cursor[l]:p[l]]) for l in range(2)),
#                                                                                    filteredChain[-2],filteredChain[-1])
                    filteredChain.append(p)
                    checkedP = True
                else :
                    # we were forced to include more than maximalChunkSize
                    logging.debug('forced:')
                    filteredChain.append(p)
                    forced = max(forced,huChunkSize,enChunkSize)
                    checkedP = True
                logging.debug('Chunk of size %s created from %s to %s.', (huChunkSize,enChunkSize),filteredChain[-2],filteredChain[-1])
                huChunkSize, enChunkSize = 0,0
                cursor = filteredChain[-1]
            else:
                checkedP = True # search through the anchor list
        lastPos=p
            
    # we include the last element regardless, because
    # by convention it marks the end of the corpora.
    if filteredChain[-1]!=chain[-1] :
        filteredChain.append(chain[-1])
    logging.debug('Filtered chain: '+str(filteredChain))
    return filteredChain,forced

def main() :
    argParser = ArgumentParser(
        description='''A preprocessor for hunalign.
Cuts a very large sentence-segmented unaligned bicorpus into smaller parts manageable by hunalign.''',
        epilog='''The two input files must have one line per sentence. Whitespace-delimited tokenization is preferred.
The output is a set of files named output_[123..].[lang1 lang2]
The standard output is a batch job description for hunalign, so this can and should be followed by:
hunalign dictionary.dic -batch hunalign_batch'''
)

    #Switches
    argParser.add_argument('-b','--brutal',action='store_true',help='Use brutal mode, which will always produce files small enough, at the cost of possibly arbitrary cut points')
    argParser.add_argument('--enc',default=None,help='decode input files from ENC')
    argParser.add_argument('--enc1',default='UTF-8',help='decode file1 from ENC1') #test file has iso8859
    argParser.add_argument('--enc2',default='UTF-8',help='decode file2 from ENC2')
    sepCritArgs = argParser.add_argument_group('Separating criteria','Disable specific criteria for splitting heuristics.')
    sepCritArgs.add_argument('--no-hapaxes',action='store_true',default=False,help='Ignore parallel hapaxes')
    sepCritArgs.add_argument('--no-tags',action='store_true',default=False,help='Ignore parallel HTML and LaTeX structuring tags')

    #Arguments
    argParser.add_argument('huFilename',metavar='file1',help='the large file to be aligned in lang1')
    argParser.add_argument('enFilename',metavar='file2',help='the large file to be aligned in lang2')
    argParser.add_argument('maximalChunkSize',type=int,nargs='?',default=5000,metavar='max',help='the maximal byte size for corpus parts, defaults to 5000')
    argParser.add_argument('output',default='output',nargs='?',help='the base name of the output files')
    argParser.add_argument('huLangName',metavar='lang1',nargs='?',default='f',help='the abbreviation of file1\'s language, defaults to f')
    argParser.add_argument('enLangName',metavar='lang2',nargs='?',default='e',help='the abbreviation of file2\'s language, defaults to e')

    args = argParser.parse_args()
    
    if args.enc!=None:
        args.enc1=args.enc2=args.enc

    logging.info('Reading corpora...')
    with open(args.huFilename,encoding=args.enc1) as huFile, open(args.enFilename,encoding=args.enc2) as enFile:
        huCorpus = [[t for t in l.strip().split()] for l in huFile.readlines()]
        enCorpus = [[t for t in l.strip().split()] for l in enFile.readlines()]
    logging.info('Done.')
    # The corpora are now lists of sentences, which are in turn lists of
    # tokens. Note that issues such as letter case and punctuation
    # aren't handled at all, so use with a raw corpus is not encouraged.

    if not args.no_hapaxes:
        huFreq = tokenFreq(huCorpus)
        enFreq = tokenFreq(enCorpus)
        huHap = hapaxes(huFreq)
        enHap = hapaxes(enFreq)
        commonHap = huHap & enHap
        huPositions = hapaxPositions(huHap,huCorpus)
        enPositions = hapaxPositions(enHap,enCorpus)
    sentSizes = ([sum(len(t.encode(args.enc1))+1 for t in s) for s in huCorpus],[sum(len(t.encode(args.enc2))+1 for t in s) for s in enCorpus]) # in bytes, including WS

    # Now we are going to chart hapaxes occurring in both corpora.
    # We will use them as anchor points later.
    pairs = []
    if not args.no_hapaxes:
        for t in commonHap :
            #       print("%d\t%d\t%s" % (huPositions[t],enPositions[t],t))
            pairs.append( (huPositions[t],enPositions[t]) )

    pairs.append((0,0)) # Start token (SOF)
    # by convention, we include this to mark the end of the corpora
    # luckily it is always < comparable to every other element,
    # so maximalChain never forgets to include it.
    # this is not true for (0,0)!
    corpusSizes = (len(huCorpus),len(enCorpus))
    pairs.append(corpusSizes) # End token (EOF)

    pairs = uniqSort(pairs)
    # pairs now contains an ordered list of all anchor mappings.

    # Add some structural anchor points
    secondaryPairs = (uniqSort(structurePositions(huCorpus)),uniqSort(structurePositions(enCorpus))) if not args.no_tags else []
    
    logging.info('Computing maximal chain in poset...')
    chain = maximalChain(pairs,secondaryPairs)
    logging.info('Done.')
    logging.info('%d long chain found in %d+%d sized poset.', len(chain), len(pairs), min(len(secondaryPairs[0]),len(secondaryPairs[1])) if secondaryPairs != [] else 0 )

    if args.maximalChunkSize>0 :
        logging.info('Selecting at most %d sized chunks...', args.maximalChunkSize)
        chain,forced = selectFromChain(chain, args.maximalChunkSize, sentSizes, args.brutal)
        logging.info( '%d chunks selected.', len(chain)-1 )
        logging.info('Done.')
        if forced != 0 :
            logging.error('MaximalChunkSize could not be obeyed.')
            logging.error('Therefore we had to produce a chunk of size %i.',forced)

    debug = False
    if debug :
        justResult = True
        if justResult :
            chainToPrint = chain[:-1]
        else :
            chainToPrint = pairs[:-1]
        for huPos,enPos in chainToPrint :
            s = ' '.join(huCorpus[huPos]) + '\t' + ' '.join(enCorpus[enPos])
            if justResult :
                print(s)
            else :
                if (huPos,enPos) in chain :
                    s += '\t<<<<<<<<'
                print(s)
                print()
    else :
        justPrintChain = False
        if justPrintChain :
            for p in chain :
                out(p[0],p[1])
        else :
            logging.info('Writing subcorpora to files...')
            lastPos = (0,0)
            ind = 1
            for pos in chain :
                if pos==lastPos :
                    continue
                baseFilename = args.output + '_' + str(ind)
                huSubCorpus = strInterval( huCorpus, lastPos[0], pos[0] )
                enSubCorpus = strInterval( enCorpus, lastPos[1], pos[1] )

                huFilename = baseFilename + '.' + args.huLangName
                with open( huFilename, 'w' ) as huFile:
                    huFile.write(huSubCorpus)

                enFilename = baseFilename + '.' + args.enLangName
                with open( enFilename, 'w' ) as enFile:
                    enFile.write(enSubCorpus)

                print(huFilename +'\t'+ enFilename +'\t'+ baseFilename+'.align')

                lastPos = pos
                ind += 1
            logging.info('Done.')

def strInterval( corpus, start, end ) :
    """Return tokens start to end-1 of corpus in text format.
    
    The sentences are separated by line breaks.
    The tokens of a sentence are separated by spaces."""
    return '\n'.join(' '.join(line) for line in corpus[start:end])

if __name__ == '__main__':
    main()

