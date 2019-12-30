#!/bin/bash

set -e

size=1
iters=131072
window=1
count=100

mpi="openmpi"

if [ $mpi = "intel" ]
then
	module load IMPI/2018.1.163-icc-18.0.1
elif [ $mpi = "mvapich" ]
then
	module load mvapich/icc-18.0.1
elif [ $mpi = "openmpi" ]
then
	module load openmpi-3.1.4-icc-18.0.1
else 
	echo mpi $mpi not defined!
	exit 0
fi

make $mpi

export PATH=$PATH:/GPUFS/nsccgz_yfdu_16/fgn/sriov-test/mpigraph/usr/bin
export LD_LIBRARY_PATH=$LD_LIBRARY_PATH:/GPUFS/nsccgz_yfdu_16/fgn/sriov-test/mpigraph/usr/lib64

rm -rf result*

while [ $size -le 1073741824 ]
do
	echo "=============== Running size=$size iters=$iters window=$window ========================="
	start=`date +"%s"`

	if [ $mpi = "intel" ]
	then
		mpirun -n 32 -ppn 1 -hosts \
		cpn1,cpn2,cpn3,cpn4,cpn5,cpn6,cpn7,cpn8,cpn9,cpn10,cpn11,cpn12,cpn13,cpn14,cpn15,cpn16,cpn106,cpn107,cpn108,cpn109,cpn110,cpn111,cpn112,cpn113,cpn114,cpn115,cpn116,cpn117,cpn118,cpn119,cpn120,cpn121 \
		./mpiGraph $size $iters $window > mpiGraph.out
	elif [ $mpi = "mvapich" ]
	then
		MV2_IBA_HCA=mlx5_2 mpirun -n 32 -ppn 1 -hosts \
		cpn1,cpn2,cpn3,cpn4,cpn5,cpn6,cpn7,cpn8,cpn9,cpn10,cpn11,cpn12,cpn13,cpn14,cpn15,cpn16,cpn106,cpn107,cpn108,cpn109,cpn110,cpn111,cpn112,cpn113,cpn114,cpn115,cpn116,cpn117,cpn118,cpn119,cpn120,cpn121 \
		./mpiGraph $size $iters $window > mpiGraph.out
	elif [ $mpi = "openmpi" ]
	then
		mpirun --mca btl openib,self,vader --mca btl_openib_if_include mlx5_2 --allow-run-as-root -n 32 -npernode 1 -host \
		cpn1,cpn2,cpn3,cpn4,cpn5,cpn6,cpn7,cpn8,cpn9,cpn10,cpn11,cpn12,cpn13,cpn14,cpn15,cpn16,cpn106,cpn107,cpn108,cpn109,cpn110,cpn111,cpn112,cpn113,cpn114,cpn115,cpn116,cpn117,cpn118,cpn119,cpn120,cpn121 \
		./mpiGraph $size $iters $window > mpiGraph.out
	fi

	end=`date +"%s"`
	let time=$end-$start
	if [ $time -ge 60 ]
	then
		echo "time = ${time}s > 60s , generate resut"
		./crunch_mpiGraph mpiGraph.out
		mv mpiGraph.out mpiGraph.out_html/
		mv mpiGraph.out_html "result$count size-$size iters-$iters window-$window"
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