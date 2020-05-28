/*
Copyright (c) 2007-2008, Lawrence Livermore National Security (LLNS), LLC
Produced at the Lawrence Livermore National Laboratory (LLNL)
Written by Adam Moody <moody20@llnl.gov>.
UCRL-CODE-232117.
All rights reserved.

This file is part of mpiGraph. For details, see
	http://www.sourceforge.net/projects/mpigraph
Please also read the Additional BSD Notice below.

Redistribution and use in source and binary forms, with or without modification,
are permitted provided that the following conditions are met:
- Redistributions of source code must retain the above copyright notice, this
	 list of conditions and the disclaimer below.
- Redistributions in binary form must reproduce the above copyright notice,
	 this list of conditions and the disclaimer (as noted below) in the documentation
	 and/or other materials provided with the distribution.
- Neither the name of the LLNL nor the names of its contributors may be used to
	 endorse or promote products derived from this software without specific prior
	 written permission.
- 
THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED.
IN NO EVENT SHALL LLNL, THE U.S. DEPARTMENT
OF ENERGY OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL,
EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION)
HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF
THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

Additional BSD Notice
1. This notice is required to be provided under our contract with the U.S. Department
	 of Energy (DOE). This work was produced at LLNL under Contract No. W-7405-ENG-48
	 with the DOE.
2. Neither the United States Government nor LLNL nor any of their employees, makes
	 any warranty, express or implied, or assumes any liability or responsibility for
	 the accuracy, completeness, or usefulness of any information, apparatus, product,
	 or process disclosed, or represents that its use would not infringe privately-owned
	 rights.
3. Also, reference herein to any specific commercial products, process, or services
	 by trade name, trademark, manufacturer or otherwise does not necessarily constitute
	 or imply its endorsement, recommendation, or favoring by the United States Government
	 or LLNL. The views and opinions of authors expressed herein do not necessarily state
	 or reflect those of the United States Government or LLNL and shall not be used for
	 advertising or product endorsement purposes.
*/

/* =============================================================
 * OVERVIEW: mpiGraph
 * Typically, one MPI task is run per node (or per interconnect link).  For a job of
 * N MPI tasks, the N tasks are logically arranged in a ring counting ranks from 0 and
 * increasing to the right, at the end rank 0 is to the right of rank N-1.  Then a
 * series of N-1 steps are executed.  In each step, each MPI task sends to the task D
 * units to the right and simultaneously receives from the task D units to the left.
 * The value of D starts at 1 and runs to N-1, so that by the end of the N-1 steps,
 * each task has sent to and received from every other task in the run, excluding itself.
 * At the end of the run, two NxN matrices of bandwidths are gathered and reported to
 * stdout -- one for send bandwidths and one for receive bandwidths.
 * =============================================================
 */

#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <mpi.h>
#include <sys/resource.h>
#include <string.h>

char  hostname[256];
char* hostnames;

char VERS[] = "1.5";

/* =============================================================
 * TIMER MACROS
 * These macros start/stop the timer and measure the difference
 * =============================================================
 */

long long int CPU_FREQUENCY=2700000000;

inline long long int getCurrentCycle() {
	unsigned low, high;
	__asm__ __volatile__("rdtsc" : "=a" (low), "=d" (high));
	return ((unsigned long long)low) | (((unsigned long long)high)<<32);
}

#define __TIME_START__ (g_timeval__start  = getCurrentCycle())
#define __TIME_END__   (g_timeval__end    = getCurrentCycle())
#define __TIME_USECS__ ((double)(g_timeval__end - g_timeval__start) / 2700)
long long int g_timeval__start, g_timeval__end;


/* =============================================================
 * MAIN TIMING LOGIC
 * Uses a ring-based (aka. shift-based) algorithm.
 * 1) First, logically arrange the MPI tasks
 *    from left to right from rank 0 to rank N-1 in a circular array.
 * 2) Then, during each step, each task sends messages to the task D uints to the right
 *    and receives from task D units to the left.
 *    In each step, each tasks measures its send and receive bandwidths.
 * 3) There are N-1 such steps so that each task has sent to and received from every task.
 * =============================================================
 */
void code(int hostid, int nnodes, int send_or_recv,int size, int iters, int window, int warmup, int warmup_memory) {
	/* arguments are: 
	 *   hostid			= rank of this host
	 *   nnodes			= number of host
	 * 	 send_or_recv	= send proccess is 0, while recv process is 1
	 *   size			= message size in bytes
	 *   iters			= number of iters to measure bandwidth between task pairs
	 *   window			= number of outstanding sends and recvs to a single rank
	 *   warmup			= warm up in second
	 *   warmup_memory  = memory used for warm up in GB
	 */
	
	if (warmup) {
		long long int warmup_size = size;
		if (warmup_size*nnodes*2 > (long long)warmup_memory/2*1024*1024*1024) {
			warmup_size = (long long)warmup_memory/2*1024*1024*1024/(nnodes*2);
		}
		char *send_buf = (char*) malloc(warmup_size);
		char *recv_buf = (char*) malloc((long long)warmup_size*nnodes*2);
		double pass = 0;
		while (pass < warmup) {
			__TIME_START__;
			MPI_Allgather(send_buf, warmup_size, MPI_BYTE, recv_buf, warmup_size, MPI_BYTE, MPI_COMM_WORLD);
			__TIME_END__;
			pass += __TIME_USECS__/1000000;
			MPI_Bcast(&pass, 1, MPI_DOUBLE, 0, MPI_COMM_WORLD);
		}
		free(send_buf);
		free(recv_buf);
	}

	int i, j, k, w;

	/* allocate memory for all of the messages */
	char* message = (char*) malloc(window*size);
	MPI_Request* request_array = (MPI_Request*) malloc(sizeof(MPI_Request)*window);
	double* times = (double*) malloc(sizeof(double)*iters*nnodes);
			
	int* message_tags = (int*) malloc(window*sizeof(int));
	for (i=0;i<window;i++) { message_tags[i] = i; }

	/* start iterating over distance */
	int distance = 1;
	while (distance < nnodes) {
		/* this test can run for a long time, so print progress to screen as we go */
		float progress = (float) distance / (float) nnodes * 100.0;
		if (hostid == 0 && send_or_recv == 0) {
			printf("%d of %d (%0.1f%%)\n", distance, nnodes, progress);
			fflush(stdout);
		}

		/* find tasks distance units to the right (send) and left (recv) */
		int sendpid = ((hostid + distance + nnodes) % nnodes)*2+1;
		int recvpid = ((hostid - distance + nnodes) % nnodes)*2;

		/* run through 'iters' iterations on a given ring */
		for (i=0; i<iters; i++) {
			/* couple of synch's to make sure everyone is ready to go */
			MPI_Barrier(MPI_COMM_WORLD);
			MPI_Barrier(MPI_COMM_WORLD);

			/* if need to reverse, modify 149 : 0->1, and add "^1 to MPI_Isend and MPI_Irecv pid parameter"*/
			if (send_or_recv == 0) {
				/* Send process*/
				__TIME_START__;
				for (w=0; w<window; w++) {
					MPI_Isend(&message[w*size], size, MPI_BYTE, 
										sendpid, message_tags[w], MPI_COMM_WORLD, &request_array[w]); 
				}
				int flag_sends = 0;
				while (!flag_sends)
					MPI_Testall(window, request_array, &flag_sends, MPI_STATUSES_IGNORE);
				__TIME_END__;
				times[(sendpid)/2*iters+i] = __TIME_USECS__ / (double) w;
			}
			else {
				/*Recv process*/
				__TIME_START__;
				for (w=0; w<window; w++) {
					MPI_Irecv(&message[w*size], size, MPI_BYTE,
										recvpid, MPI_ANY_TAG, MPI_COMM_WORLD, &request_array[w]);
				}
				int flag_recvs = 0;
				while (!flag_recvs)
					MPI_Testall(window, request_array, &flag_recvs, MPI_STATUSES_IGNORE);
				__TIME_END__;
				times[(recvpid/2)*iters+i] = __TIME_USECS__ / (double) w;
			}
		} /* end iters loop */
		/* bump up the distance for the next ring step */
		distance++;
	} /* end distance loop */

	/* for each node, compute sum of my bandwidths with that node */
	if (hostid == 0 && send_or_recv == 0)
		printf("Gathering results\n");
	double* sums = (double*) malloc(sizeof(double)*nnodes);
	for (j = 0; j<nnodes; j++) {
		sums[j] = 0.0;
		if (j == hostid) continue;
		for(i=0; i<iters; i++)
			sums[j] += times[j*iters+i];
	}
	
	/* gather send bw sums to rank 0 */
	double* allsums;
	if (hostid == 0 && send_or_recv == 0) {
		allsums = (double*) malloc(sizeof(double)*nnodes*nnodes);
	}
	int *recvcounts, *displs;
	if (hostid == 0 && send_or_recv == 0) {
		recvcounts = (int*) malloc(sizeof(int)*nnodes*2);
		displs = (int*) malloc(sizeof(int)*nnodes*2);
		for (i = 0; i < nnodes*2; i++) {
			recvcounts[i] = i%2 == 0? nnodes: 0;
			if (i > 0)
				displs[i] = displs[i-1] + recvcounts[i-1];
			else displs[i] = 0;
		}
	}
	MPI_Barrier(MPI_COMM_WORLD);
	MPI_Gatherv(sums, send_or_recv == 0? nnodes: 0, MPI_DOUBLE, allsums, recvcounts, displs, MPI_DOUBLE, 0, MPI_COMM_WORLD);
	
	/* rank 0 computes send stats and prints result */
	if (hostid == 0 && send_or_recv == 0) {
		/* compute stats over all nodes */
		double sendsum = 0.0;
		double sendmin = 10000000000000000.0;
		double MBsec   = ((double)(size)) * 1000000.0 / (1024.0*1024.0);
		for(j=0; j<nnodes; j++) {
			for(k=0; k<nnodes; k++) {
				if (j == k) continue;
				double sendval = allsums[j*nnodes+k];
				sendsum += sendval;
				sendmin = (sendval < sendmin) ? sendval : sendmin;
			}
		}

		/* print send stats */
		sendmin /= (double) iters;
		sendsum /= (double) (nnodes)*(nnodes-1)*iters;
		printf("\nSend max\t%f\n", MBsec/sendmin);
		printf("Send avg\t%f\n", MBsec/sendsum);

		/* print send bandwidth table */
		printf("\n");
		printf("Send\t");
		for(k=0; k<nnodes; k++) {
			printf("%s:%d\t", &hostnames[k*sizeof(hostname)], k);
		}
		printf("\n");
		for(j=0; j<nnodes; j++) {
			printf("%s:%d to\t", &hostnames[j*sizeof(hostname)], j);
			for(k=0; k<nnodes; k++) {
				double val = allsums[j*nnodes+k];
				if (val != 0.0) { val = MBsec * (double) iters / val; }
				printf("%0.3f\t", val);
			}
			printf("\n");
		}
	}
	
	if (hostid == 0 && send_or_recv == 0) {
		for (i = 0; i < nnodes*2; i++) {
			recvcounts[i] = i%2 == 1? nnodes: 0;
			if (i > 0)
				displs[i] = displs[i-1] + recvcounts[i-1];
			else displs[i] = 0;
		}
	}

	/* gather recv bw sums to rank 0 */
	MPI_Barrier(MPI_COMM_WORLD);
	MPI_Gatherv(sums, send_or_recv == 1? nnodes: 0, MPI_DOUBLE, allsums, recvcounts, displs, MPI_DOUBLE, 0, MPI_COMM_WORLD);
	
	/* rank 0 computes recv stats and prints result */
	if (hostid == 0 && send_or_recv == 0) {
		/* compute stats over all nodes */
		double recvsum = 0.0;
		double recvmin = 10000000000000000.0;
		double MBsec   = ((double)(size)) * 1000000.0 / (1024.0*1024.0);
		for(j=0; j<nnodes; j++) {
			for(k=0; k<nnodes; k++) {
				if (j == k) continue;
				double recvval = allsums[j*nnodes+k];
				recvsum += recvval;
				recvmin = (recvval < recvmin) ? recvval : recvmin;
			}
		}

		/* print receive stats */
		recvmin /= (double) iters;
		recvsum /= (double) (nnodes)*(nnodes-1)*iters;
		printf("\nRecv max\t%f\n", MBsec/recvmin);
		printf("Recv avg\t%f\n", MBsec/recvsum);

		/* print receive bandwidth table */
		printf("\n");
		printf("Recv\t");
		for(k=0; k<nnodes; k++) {
			printf("%s:%d\t", &hostnames[k*sizeof(hostname)], k);
		}
		printf("\n");
		for(j=0; j<nnodes; j++) {
			printf("%s:%d from\t", &hostnames[j*sizeof(hostname)], j);
			for(k=0; k<nnodes; k++) {
				double val = allsums[j*nnodes+k];
				if (val != 0.0) { val = MBsec * (double) iters / val; }
				printf("%0.3f\t", val);
			}
			printf("\n");
		}
	}
	
	/* free off memory */
	if (hostid == 0 && send_or_recv == 0) {
		free(allsums);
	}
	free(sums);
	free(message);
	free(request_array);
	free(times);
	free(message_tags);

	return;
}

/* =============================================================
 * MAIN DRIVER
 * Inits MPI, reads command-line parameters, and kicks off testing
 * =============================================================
 */
int main(int argc, char **argv)
{
	int rank, ranks, size, iters, window, warmup, warmup_memory;
	int args[3];

	/* start up */
	MPI_Init(&argc,&argv);
	MPI_Comm_rank(MPI_COMM_WORLD, &rank);
	MPI_Comm_size(MPI_COMM_WORLD, &ranks);
			 
	/* collect hostnames of all the processes */
	gethostname(hostname, sizeof(hostname));
	if (rank == 0)
		hostnames = (char*) malloc(sizeof(hostname)*ranks);
	MPI_Gather(hostname, sizeof(hostname), MPI_CHAR, hostnames, sizeof(hostname), MPI_CHAR, 0, MPI_COMM_WORLD);

	/* confirm */
	if (rank == 0) {
		int i;
		if (ranks % 2) {
			printf("This program must run 2 process on each node!!\n");
			MPI_Abort(MPI_COMM_WORLD, 0);
			return 0;
		}
		for (i = 0; i < ranks; i+=2)
			if (strcmp(&hostnames[i*sizeof(hostname)], &hostnames[(i+1)*sizeof(hostname)])) {
				printf("This program must run 2 process on each node!\n");
				MPI_Abort(MPI_COMM_WORLD, 0);
				return 0;
			}
		for (i = 1; i < ranks/2; i++)
			memcpy(&hostnames[i*sizeof(hostname)], &hostnames[i*2*sizeof(hostname)], sizeof(hostname));
		// for (i = 0; i < ranks/2; i++)
		// 	printf("%s\n", &hostnames[i*sizeof(hostname)]);
	}

	/* set job parameters, read values from command line if they're there */
	size = 4096*4;
	iters = 100;
	window = 50;
	warmup = 0;
	warmup_memory = 0;
	if (argc >= 4) {
		size   = atoi(argv[1]);
		iters  = atoi(argv[2]);
		window = atoi(argv[3]);
		if (argc == 6) {
			warmup = atoi(argv[4]);
			warmup_memory = atoi(argv[5]);
		}
	}
	args[0] = size;
	args[1] = iters;
	args[2] = window;

	/* print the header */
	if (rank == 0) {
		/* mark start of output */
		printf("START mpiGraph v%s\n", VERS);
		printf("MsgSize\t%d\nTimes\t%d\nWindow\t%d\n",size,iters,window);
		printf("Warmup\t%d\nWarmup_memory\t%d\n", warmup, warmup_memory);
		printf("Procs\t%d\n\n",ranks);
	}

	/* synchronize, then start the run */
	MPI_Barrier(MPI_COMM_WORLD);
	code(rank/2, ranks/2, rank%2, size, iters, window, warmup, warmup_memory);
	MPI_Barrier(MPI_COMM_WORLD);

	/* print memory usage */
/*
	if(rank == 0) { printf("\n"); }
	print_mpi_resources();
*/

	/* mark end of output */
	if (rank == 0) { printf("END mpiGraph\n"); }

	/* shut down */
	MPI_Finalize();
	return 0;
}
