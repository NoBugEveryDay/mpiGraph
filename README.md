# mpiGraph运行方法

## 下载

到GitHub上下载源码即可 https://github.com/LLNL/mpiGraph 

## 编译

#### 编译安装主程序

```shell
unzip mpiGraph-master.zip
cd mpiGraph-master/
module load IMPI/2018.1.163-icc-18.0.1
```

编辑`makefile`

```makefile
all: clean
        mpiicc -O3 -xhost -ipo -o mpiGraph mpiGraph.c

debug:
        mpiicc -g -O0 -o mpiGraph mpiGraph.c

clean:
        rm -rf mpiGraph.o mpiGraph
```

然后直接`make`

#### 安装netpbm

```shell
wget http://hfs.sysu.tech/software/linux/mpiGraph/netpbm/netpbm-10.79.00-7.el7.x86_64.rpm
wget http://hfs.sysu.tech/software/linux/mpiGraph/netpbm/netpbm-progs-10.79.00-7.el7.x86_64.rpm
rpm2cpio netpbm-10.79.00-7.el7.x86_64.rpm | cpio -idvm
rpm2cpio netpbm-progs-10.79.00-7.el7.x86_64.rpm | cpio -idvm
```

## 运行

参数

```shell
mpiGraph <size> <iters> <window>
```

第一个参数`size` 为消息大小，单位为byte

第二个参数`iters `为迭代次数

第三个参数`window`为每次迭代同时发送的消息的数量

```shell
srun -N 32 -p test_docker ./mpiGraph 1048576 1000 30 > mpiGraph.out
```

或者

```shell
mpirun -n 32 -ppn 1 -hosts cpn1,cpn2,cpn3,cpn4,cpn5,cpn6,cpn7,cpn8,cpn9,cpn10,cpn11,cpn12,cpn13,cpn14,cpn15,cpn16,cpn106,cpn107,cpn108,cpn109,cpn110,cpn111,cpn112,cpn113,cpn114,cpn115,cpn116,cpn117,cpn118,cpn119,cpn120,cpn121 ./mpiGraph 1048576 1000 30 > mpiGraph.out
```

## 后处理

```shell
export PATH=$PATH:/GPUFS/nsccgz_yfdu_16/fgn/sriov-test/mpigraph/usr/bin
export LD_LIBRARY_PATH=$LD_LIBRARY_PATH:/GPUFS/nsccgz_yfdu_16/fgn/sriov-test/mpigraph/usr/lib64
./crunch_mpiGraph mpiGraph.out
```

生成带图的html网页

## debug

### bug1

`crunch_mpiGraph`第120行

```perl
push @ret, sprintf("%3.1f%", $val / $base * 100);
改为
push @ret, sprintf("%3.1f%%", $val / $base * 100);
```

不改会出现如下bug

```
Missing argument in sprintf at ./crunch_mpiGraph line 120.
Invalid conversion in sprintf: end of string at ./crunch_mpiGraph line 120.
```

生成的HTML在有些地方会有undefined，不知道这个算不算bug

### bug2

`crunch_mpiGraph`注释掉305行的

```perl
print HTML "<tr><td>Run by:</td><td>" . $parts[0] . " (" . $parts[4]. ")</td></tr>\n";
```

因为有的HPC集群上无法正确获取用户名

### bug3

`mpiGraph`超级坑的bug，要不是openmpi给我报错了，还真发现不了它的下标写错了……

第171行两个数组下标计算错误，都多了一个`-1`

将

```c
MPI_Testall((k+1)/2, &request_array[(k+1)/2-1], &flag_sends, &status_array[(k+1)/2-1]);
```

改为

```c
MPI_Testall((k+1)/2, &request_array[(k+1)/2], &flag_sends, &status_array[(k+1)/2]);
```

## 优化

因为对小消息计时非常不准，所以使用CPU周期计时器对代码进行优化

将81行至116行的代码替换为如下

```c++
long long int CPU_FREQUENCY=2700000000;

inline long long int getCurrentCycle() {
	unsigned low, high;
	__asm__ __volatile__("rdtsc" : "=a" (low), "=d" (high));
	return ((unsigned long long)low) | (((unsigned long long)high)<<32);
}

#define __TIME_START__    (g_timeval__start    = getCurrentCycle())
#define __TIME_END_SEND__ (g_timeval__end_send = getCurrentCycle())
#define __TIME_END_RECV__ (g_timeval__end_recv = getCurrentCycle())
#define __TIME_USECS_SEND__ ((g_timeval__end_send - g_timeval__start) / 2700)
#define __TIME_USECS_RECV__ ((g_timeval__end_recv - g_timeval__start) / 2700)
long long int g_timeval__start, g_timeval__end_send, g_timeval__end_recv;
```

## 生成的结果说明

每一行对角线上的元素为全局带宽最大值！