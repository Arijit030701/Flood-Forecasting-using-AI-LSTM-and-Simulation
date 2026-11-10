/* MPI ping-pong: how long one message takes between two processes (latency) and how fast big
   messages go (bandwidth). Run once with both processes on ONE machine, once on TWO machines. */
#include <mpi.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

int main(int argc, char **argv) {
    MPI_Init(&argc, &argv);
    int rank, size, len;
    MPI_Comm_rank(MPI_COMM_WORLD, &rank);
    MPI_Comm_size(MPI_COMM_WORLD, &size);
    if (size != 2) {
        if (rank == 0) printf("run with exactly 2 processes\n");
        MPI_Finalize();
        return 1;
    }
    char me[MPI_MAX_PROCESSOR_NAME], other[MPI_MAX_PROCESSOR_NAME];
    memset(me, 0, sizeof me);
    MPI_Get_processor_name(me, &len);
    if (rank == 0) MPI_Recv(other, MPI_MAX_PROCESSOR_NAME, MPI_CHAR, 1, 9, MPI_COMM_WORLD, MPI_STATUS_IGNORE);
    else           MPI_Send(me, MPI_MAX_PROCESSOR_NAME, MPI_CHAR, 0, 9, MPI_COMM_WORLD);

    const int sizes[] = {8, 1024, 65536, 1048576, 8388608};
    char *buf = malloc(8388608);
    memset(buf, 1, 8388608);
    if (rank == 0) printf("rank 0 on %s, rank 1 on %s\n%10s %14s %12s\n", me, other, "bytes", "one-way (us)", "MB/s");
    for (int k = 0; k < 5; k++) {
        int n = sizes[k];
        int reps = n < 65536 ? 2000 : (n < 1048576 ? 200 : 20);
        MPI_Barrier(MPI_COMM_WORLD);
        double t0 = MPI_Wtime();
        for (int r = 0; r < reps; r++) {
            if (rank == 0) {
                MPI_Send(buf, n, MPI_CHAR, 1, 0, MPI_COMM_WORLD);
                MPI_Recv(buf, n, MPI_CHAR, 1, 0, MPI_COMM_WORLD, MPI_STATUS_IGNORE);
            } else {
                MPI_Recv(buf, n, MPI_CHAR, 0, 0, MPI_COMM_WORLD, MPI_STATUS_IGNORE);
                MPI_Send(buf, n, MPI_CHAR, 0, 0, MPI_COMM_WORLD);
            }
        }
        double t = (MPI_Wtime() - t0) / reps / 2.0;
        if (rank == 0) printf("%10d %14.2f %12.1f\n", n, t * 1e6, n / t / 1e6);
    }
    free(buf);
    MPI_Finalize();
    return 0;
}
