#!/bin/bash

set -e

size=1
iters=1
window=1
count=100
warmup=30
warmup_memory=32

DIR="result-`date +%F-%T`"
mkdir $DIR
cd $DIR

while [ $size -le 1073741824 ]
do
	echo "=============== Running size=$size iters=$iters window=$window ========================="
	start=`date +"%s"`
	
	mpirun -launcher ssh -launcher-exec /usr/bin/nss_yhpc_ssh -ppn 2 ../mpiGraph $size $iters $window > mpiGraph.out
	
	end=`date +"%s"`
	let time=$end-$start+1 # It must +1 becasue time=0 will lead to error and exit
	if [ $time -ge 60 ]
	then
		echo "time = ${time}s > 60s , run again with ${warmup}s warm up"
		mpirun -launcher ssh -launcher-exec /usr/bin/nss_yhpc_ssh -ppn 2 ../mpiGraph $size $iters $window $warmup $warmup_memory > mpiGraph.out
		mv mpiGraph.out "result$count size-$size iters-$iters window-$window"
		let count=$count+1		
		let size=$size*2
		while [ $iters -gt 1 ] && [ $time -gt 120 ]
		do
			let iters=$iters/2
			let time=$time/2
		done

	else
		let iters=$iters*2
		echo "time = ${time}s < 60s , run again with iters=$iters"
	fi
	echo
	echo
done
