all: clean
	mpiicc -O3 -xhost -ipo -o mpiGraph mpiGraph.c

debug:
	mpiicc -g -O0 -o mpiGraph mpiGraph.c

clean:
	rm -rf mpiGraph.o mpiGraph
