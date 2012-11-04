#!/bin/bash
corpusloc=~/europarl-ro-en.nobackup
prefix=europarl-v7.ro-en
hunalign=~/HunAlign.nobackup/src/hunalign/hunalign
mv $corpusloc/results $corpusloc/results.bak$(date '+%Y%m%d')
count=80000
while [ $count -le 390000 ]; do
	echo -n "Trying with $count lines: " | tee -a $corpusloc/results
	head -n $count < $corpusloc/$prefix.en > $corpusloc/testen
	head -n $count < $corpusloc/$prefix.ro > $corpusloc/testro
	#rm $corpusloc/autodict
	$hunalign -autodict=$corpusloc/autodict /dev/null $corpusloc/testen $corpusloc/testro 2>&1 | tee /dev/stderr |  egrep 'planned thickness|alloc|[Ss]egmentation' | tee -a $corpusloc/results
	echo '' | tee -a $corpusloc/results
	count=$(($count * 4 / 3))
done
