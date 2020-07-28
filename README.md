# mpiGraph Advanced

## 简介

基于 https://github.com/LLNL/mpiGraph 进行了多项优化的版本，修复了bug，提高了测试结果准确性，重写了html结果渲染器

## 使用方法

```bash
# Intel MPI
make intel
mpirun -n 8 -ppn 2 -hosts cpn1,cpn2,cpn3,cpn4 ./mpiGraph $size $iters $window > mpiGraph.out
# Mvapich
make mvapich
mpirun -n 64 -ppn 2 -hosts cpn1,cpn2,cpn3,cpn4 ./mpiGraph $size $iters $window > mpiGraph.out
# OpenMPI
make openmpi
mpirun -n 64 -npernode 2 -host cpn1:2,cpn2:2,cpn3:2,cpn4:2 ./mpiGraph $size $iters $window > mpiGraph.out

# html版结果渲染
python3 html_generator.py -i mpiGraph.out [-o OUTPUT_DIR_NAME]
```

## 修复的bug

`mpiGraph`超级坑的bug，要不是openmpi给我报错了，还真发现不了它的下标写错了……

（源码）第171行两个数组下标计算错误，都多了一个`-1`

将

```c
MPI_Testall((k+1)/2, &request_array[(k+1)/2-1], &flag_sends, &status_array[(k+1)/2-1]);
```

改为

```c
MPI_Testall((k+1)/2, &request_array[(k+1)/2], &flag_sends, &status_array[(k+1)/2]);
```

## 计时准确性优化

因为对小消息计时非常不准，所以使用CPU周期计时器对代码进行优化

将（源码）81行至116行的代码替换为如下

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

另外，使用同一个进程同时对收和发计时并不科学，所以将代码优化为了一个节点上跑两个进程，一个进程负责发送，另一个进程负责接收。

## 新增了warmup参数（可选）

第四个参数为需要warmup的迭代次数
这个参数必须要与前三个参数一起使用，即不能只使用这个参数，而不指定size、iters、window

## 生成的结果说明

每一行对角线上的元素为全局带宽最大值！

## HTML结果渲染器

不再依赖于perl，而是使用python3.8，不需要任何其他的包
如果遇到包不可用的问题，可以尝试重新在`pip-lib`中安装相应的包