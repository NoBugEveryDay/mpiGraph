intel: clean
	mpiicc -O3 -xhost -ipo -o mpiGraph mpiGraph.c

mvapich: clean
	mpicc -O3 -xhost -ipo -o mpiGraph mpiGraph.c

openmpi: clean
	mpicc -O3 -xhost -ipo -o mpiGraph mpiGraph.c

debug:
	mpicc -g -O0 -o mpiGraph mpiGraph.c

clean:
	rm -rf mpiGraph.o mpiGraph
