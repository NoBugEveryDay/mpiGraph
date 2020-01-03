#!/bin/bash

set -e

size=1024
iters=131072
window=1
count=100

mpi="openmpi"

module purge

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

while [ $window -le 131072 ]
do
	echo "=============== Running size=$size iters=$iters window=$window ========================="
	start=`date +"%s"`

	if [ $mpi = "intel" ]
	then
		mpirun -n 64 -ppn 2 -hosts \
		cpn1,cpn2,cpn3,cpn4,cpn5,cpn6,cpn7,cpn8,cpn9,cpn10,cpn11,cpn12,cpn13,cpn14,cpn15,cpn16,cpn106,cpn107,cpn108,cpn109,cpn110,cpn111,cpn112,cpn113,cpn114,cpn115,cpn116,cpn117,cpn118,cpn119,cpn120,cpn121 \
		./mpiGraph $size $iters $window > mpiGraph.out
	elif [ $mpi = "mvapich" ]
	then
		MV2_IBA_HCA=mlx5_2 mpirun -n 64 -ppn 2 -hosts \
		cpn1,cpn2,cpn3,cpn4,cpn5,cpn6,cpn7,cpn8,cpn9,cpn10,cpn11,cpn12,cpn13,cpn14,cpn15,cpn16,cpn106,cpn107,cpn108,cpn109,cpn110,cpn111,cpn112,cpn113,cpn114,cpn115,cpn116,cpn117,cpn118,cpn119,cpn120,cpn121 \
		./mpiGraph $size $iters $window > mpiGraph.out
	elif [ $mpi = "openmpi" ]
	then
		mpirun --mca btl openib,self,vader --mca btl_openib_if_include mlx5_2 -x LD_LIBRARY_PATH --allow-run-as-root -n 64 -npernode 2 -host \
		cpn1:2,cpn2:2,cpn3:2,cpn4:2,cpn5:2,cpn6:2,cpn7:2,cpn8:2,cpn9:2,cpn10:2,cpn11:2,cpn12:2,cpn13:2,cpn14:2,cpn15:2,cpn16:2,cpn106:2,cpn107:2,cpn108:2,cpn109:2,cpn110:2,cpn111:2,cpn112:2,cpn113:2,cpn114:2,cpn115:2,cpn116:2,cpn117:2,cpn118:2,cpn119:2,cpn120:2,cpn121:2 \
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
		let window=$window*2
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
