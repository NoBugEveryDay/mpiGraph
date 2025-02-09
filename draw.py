# -*- coding: UTF-8 -*-

# Convert results generated by auto-size.sh or auto-windows.sh to line chart

import os
import re
import matplotlib.pyplot as plt

# target_list = ["auto-window-mvapich", "auto-window-intel", "auto-window-openmpi"]
# label = ["mvapich", "intel", "openmpi"]
# color = ["r", "g", "b"]

# target_list = ["auto-size-mvapich", "auto-size-intel", "auto-size-openmpi"]
# label = ["mvapich", "intel", "openmpi"]
# color = ["r", "g", "b"]

# target_list = ["auto-size-th16", "auto-size-th32", "auto-size-th32-contiguous"]
# label = ["th-mpich16", "th-mpich32", "th-mpich32-contiguous"]
# color = ["g", "r", "b"]

# target_list = ["result-2020-07-15-17.03.44", "result-2020-07-20-15.33.57", "result-2020-07-24-16.45.47", "result-2020-07-24-15.51.17"]
# label = ["new rt, er=0", "new rt, er=1", "old rt, er=0", "old rt, er=1"]
# color = ["r", "g", "b", "y"]

target_list = [	"result-2020-09-07-16.54.00", 	"result-2020-09-07-17.53.59", 	"result-2020-09-08-18.04.46", 	"result-2020-09-08-19.04.45"]
label = [		"old rt, er=1", 				"old rt, er=0",					"new rt, er=1",					"new rt, er=0"]
color = ["r", "g", "b", "y"]

def main():
	for index in range(len(target_list)):
		sub_dir_list = [ "./"+target_list[index]+'/'+dir for dir in  os.listdir("./"+target_list[index]) ]
		# print(sub_dir_list)
		sub_dir_contain = []
		for dir in sub_dir_list:
			if (os.path.isdir(dir)):
				sub_dir_contain += [ dir+'/'+file for file in os.listdir(dir) ]
		file_list = []
		for file in sub_dir_contain:
			if file.endswith("mpiGraph.out"):
				file_list.append(file)
		# print(file_list)
		send_max = []
		send_avg = []
		recv_max = []
		recv_avg = []
		for i in range(len(file_list)):
			with open(file_list[i], "r") as file:
				content = file.read()
			send_max.append(re.search(r"(?<=(Send\smax\s))\d+\.\d+", content).group())
			send_avg.append(re.search(r"(?<=(Send\savg\s))\d+\.\d+", content).group())
			recv_max.append(re.search(r"(?<=(Recv\smax\s))\d+\.\d+", content).group())
			recv_avg.append(re.search(r"(?<=(Recv\savg\s))\d+\.\d+", content).group())
		send_max = [float(i) for i in send_max]
		send_avg = [float(i) for i in send_avg]
		recv_max = [float(i) for i in recv_max]
		recv_avg = [float(i) for i in recv_avg]
		# recv_avg = recv_avg[:15]
		x = range(len(recv_avg))
		plt.plot(x, send_avg, color=color[index], linestyle='--', label=label[index]+" send avg")
		# plt.plot(x, send_max, color=color[index], linestyle=':', label=label[index]+" send max")
		# plt.plot(x, recv_avg, color=color[index], linestyle='-', label=label[index]+" recv avg")
		# plt.plot(x, recv_max, color=color[index], linestyle='-.', label=label[index]+" recv max")
	plt.legend()
	plt.show()

 
if __name__ == "__main__":
	main()