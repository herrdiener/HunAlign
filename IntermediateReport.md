HunAlign Project Intermediate Report
========================================
Nicolas Diener, Victor Bielawski

Summary
----------------------------
When aligning a corpus too large for the memory limit (discussed below),
HunAlign downgrades the thickness of its alignment matrix (i.e. the area of a
theoretical square grid that it actually uses) and, below a certain thickness
and with certain corpora, tries to write to nonexistent memory and crashes.

Findings
----------------------------
For a given pair of corpora, HunAlign allocates two 2D matrices, with each
dimension being the length of one of the corpora, one for the raw dynamic
programming table and one for the chosen alignment path. Both tables' rows, in
the ideal case, are limited to one tenth of the average corpus length. This
"thickness" has the effect of limiting alignments with too many orphaned
sentences, or in graphical terms, a path that deviates too much from a perfect
diagonal. When there isn't enough memory to store the preferred 1/10 thickness,
the thickness is downgraded to one that can be stored, further limiting
variations in the path.

For our stress testing, we used varying subsets of the Europarl English-Romanian
bilingual corpus, and tried to align the sub-corpora under both 4 and 16
gigabyte memory limits. Under the 4GB limit, the maximum number of sentences
alignable without thickness loss is 32220, and under the 16 GB limit the maximum
is 64265. When going above these limits, the thickness starts to decrease
hyperbolically, as expected.

![Graph: The maximum allowable thickness is approximately 25900000 * (memory
limit in megabytes) / (corpus size in sentences).](graph.png)

Depending on the corpus, an alignment can still sometimes be produced with a
substandard thickness. For this particular corpus, the boundary for a 16 GB
memory limit is at approximately 300000 sentences, but this can vary wildly by
corpus and will only be relevant for a hypothetical fine-tuning stage of the
project.

Next steps
----------------------------
As the current thickness algorithm already cuts corners to stay within
reasonable memory usage, it seems that the best way forward would be to
implement incremental dictionary population. However, in the interest of having
the application "just work", it is also a good idea to handle the cases with
not enough thickness more gracefully. An absolutely minimal solution would be to
report the error in a better way than a segfault, but we may also try to
dynamically recompute a single row with more thickness. If there is time left,
another possible improvement would be to allow non-linear boundaries for the
usable portion of the matrix, since real-life alignments tend to have more
deviation from a perfect diagonal in the middle of the matrix.
