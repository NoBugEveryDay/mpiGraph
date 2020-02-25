# -*- coding: UTF-8 -*-

import os, sys, getopt

sys.path.append(sys.path[0]+"/pip-lib")
from PIL import Image

def print_usage():
    print('''Usage : /usr/bin/python3 mpiGraph_render/html_generator.py [-h] -i INPUT_FILE_NAME [-o OUTPUT_DIR_NAME]
    -h : Print this help
    -i INPUT_FILE_NAME : mpiGraph output file name, default mpiGraph.out
    -o OUTPUT_DIR_NAME : html output file name, default INPUT_FILE_NAME_html''')

if __name__ == "__main__":

    print("Program html_generator.py start")

    input_file_name = "mpiGraph.out"
    output_dir_name = None
    shift_flag = False

    # 参数处理
    try:
        opts, args = getopt.getopt(sys.argv[1:],"hsi:o:")
    except getopt.GetoptError:
        print_usage()
        sys.exit(0)
    for opt, arg in opts:
        if opt == "-h":
            print_usage()
            sys.exit()
        elif opt == "-s":
            shift_flag = True
        elif opt == "-i" :
            input_file_name = arg
        elif opt == "-o" :
            output_dir_name = arg
    if os.path.exists(input_file_name) == False:
        print(input_file_name, "doesn't exist!")
        print_usage()
        sys.exit()
    if output_dir_name == None:
        output_dir_name = input_file_name + "_html"
    # print(input_file_name)
    # print(output_dir_name)
    
    # 将输入文件转换为二维数组
    fp = open(input_file_name, "r")
    input_file_lines = fp.readlines()
    for i in range(len(input_file_lines)):
        input_file_lines[i] = input_file_lines[i].replace("\n", "").split('\t')
    # print(input_file_lines)

    # 确定节点数量及其hostname_list
    host_num = None
    hostname_list = None
    for line in input_file_lines:
        if line[0] == "Send":
            while line[-1] == "":
                line = line[1:-1]
            host_num = int(line[-1].split(":")[1]) + 1
            print("host_num =", host_num)
            if len(line) != host_num:
                print("ERROR : len(line) != host_num")
                exit(0)
            hostname_list = [i.split(":")[0] for i in line]
            print("hostname_list =", hostname_list)
            break
    
    # 读入各种参数
    arg_list = {
        "MsgSize": None, 
        "Times": None, 
        "Window": None, 
        "Procs": None, 
        "Send max": None, 
        "Send avg": None, 
        "Recv max": None, 
        "Recv avg": None,
        "Send min": None, # 额外添加需要求
        "Recv min": None  # 额外添加需要求
    }
    for arg_name in arg_list:
        for line in input_file_lines:
            if line[0] == arg_name:
                arg_list[arg_name] = float(line[1])
                break
    for arg_name in arg_list:
        print(arg_name, arg_list[arg_name])
    
    # 读入两张表
    send_sheet = [[None for _ in range(host_num)] for _ in range(host_num)]
    for row_offset in range(len(input_file_lines)):
        if (input_file_lines[row_offset][0] == "Send"):
            row_offset += 1
            col_offset = 1
            for row in range(host_num):
                for col in range(host_num):
                    if row != col:
                        send_sheet[row][col] = float(input_file_lines[row+row_offset][col+col_offset])
                    else:
                        send_sheet[row][col] = arg_list["Send max"]
                    if arg_list["Send max"] >= 10:
                        send_sheet[row][col] = int(send_sheet[row][col])
                    if arg_list["Send min"] == None or arg_list["Send min"] > send_sheet[row][col]:
                        arg_list["Send min"] = send_sheet[row][col]
    # for i in send_sheet:
    #     print(i)

    recv_sheet = [[None for _ in range(host_num)] for _ in range(host_num)]
    for row_offset in range(len(input_file_lines)):
        if (input_file_lines[row_offset][0] == "Recv"):
            row_offset += 1
            col_offset = 1
            for row in range(host_num):
                for col in range(host_num):
                    if row != col:
                        recv_sheet[row][col] = float(input_file_lines[row+row_offset][col+col_offset])
                    else:
                        recv_sheet[row][col] = arg_list["Recv max"]
                    if arg_list["Send max"] >= 10:
                        recv_sheet[row][col] = int(recv_sheet[row][col])
                    if arg_list["Recv min"] == None or arg_list["Recv min"] > recv_sheet[row][col]:
                        arg_list["Recv min"] = recv_sheet[row][col]
    # for i in recv_sheet:
    #     print(i)

    # 创建输出目录
    if os.path.exists(output_dir_name):
        if os.path.isdir(output_dir_name):
            print("Dir", output_dir_name, "exists")
        else:
            print(output_dir_name, "is a file! Please delete it!")
            sys.exit()
    else:
        print("mkdir", output_dir_name)
        os.mkdir(output_dir_name)
    
    # 输出位图，顺便做直方图的频率统计，顺便做放大的sheet
    factor = 1 # 图像放大倍数
    while factor*host_num < 200:
        factor *= 2
    send_count = [0 for _ in range(256)]
    recv_count = [0 for _ in range(256)]
    send_sheet_big = [[None for _ in range(host_num*factor)] for _ in range(host_num*factor)]
    recv_sheet_big = [[None for _ in range(host_num*factor)] for _ in range(host_num*factor)]

    print("Generate send.bmp")
    send_img = Image.new( 'RGB', (host_num*factor, host_num*factor), "white")
    pixels = send_img.load()
    # pixels[col,row] = (r,g,b) # 注意行和列是反着的！
    for i in range(host_num*factor):
        for j in range(host_num*factor):
            tmp = send_sheet[int(i/factor)][int(j/factor)]
            send_sheet_big[i][j] = tmp
            tmp = int(tmp/arg_list["Send max"]*255)
            pixels[j, i] = (tmp, tmp, tmp)
            if i != j:
                send_count[tmp] += 1
    send_img.save(output_dir_name+"/send.bmp")

    print("Generate send_shift.bmp")
    send_shift_img = Image.new( 'RGB', (host_num*factor, host_num*factor), "white")
    pixels = send_shift_img.load()
    for i in range(host_num*factor):
        for j in range(host_num*factor):
            tmp = send_sheet[int(i/factor)][(int(i/factor)+int(j/factor))%host_num]
            tmp = int(tmp/arg_list["Send max"]*255)
            pixels[j, i] = (tmp, tmp, tmp)
    send_shift_img.save(output_dir_name+"/send_shift.bmp")

    print("Generate recv.bmp")
    recv_img = Image.new( 'RGB', (host_num*factor, host_num*factor), "white")
    pixels = recv_img.load()
    # pixels[col,row] = (r,g,b) # 注意行和列是反着的！
    for i in range(host_num*factor):
        for j in range(host_num*factor):
            tmp = recv_sheet[int(i/factor)][int(j/factor)]
            recv_sheet_big[i][j] = tmp
            tmp = int(tmp/arg_list["Recv max"]*255)
            pixels[j, i] = (tmp, tmp, tmp)
            if i != j:
                recv_count[tmp] += 1
    recv_img.save(output_dir_name+"/recv.bmp")

    print("Generate recv_shift.bmp")
    recv_shift_img = Image.new( 'RGB', (host_num*factor, host_num*factor), "white")
    pixels = recv_shift_img.load()
    for i in range(host_num*factor):
        for j in range(host_num*factor):
            tmp = recv_sheet[int(i/factor)][(int(i/factor)+int(j/factor))%host_num]
            tmp = int(tmp/arg_list["Recv max"]*255)
            pixels[j, i] = (tmp, tmp, tmp)
    recv_shift_img.save(output_dir_name+"/recv_shift.bmp")

    # 生成直方图
    print("Generate send_hist.png")
    send_hist_img = Image.new( 'RGB', (256, 200), "black")
    pixels = send_hist_img.load()
    for i in range(256):
        for j in range(int(send_count[i]/(host_num*(host_num-1)*factor*factor)*199)):
            pixels[i,199-j] = (255,255,255)
    send_hist_img.save(output_dir_name+"/send_hist.png")

    print("Generate recv_hist.png")
    recv_hist_img = Image.new( 'RGB', (256, 200), "black")
    pixels = recv_hist_img.load()
    for i in range(256):
        for j in range(int(recv_count[i]/(host_num*(host_num-1)*factor*factor)*199)):
            pixels[i,199-j] = (255,255,255)
    recv_hist_img.save(output_dir_name+"/recv_hist.png")

    # 生成map.txt
    print("Generate map.txt")
    map_file = open(output_dir_name+"/map.txt", "w")
    map_file.write("Rank\tNode\n")
    for i in range(host_num):
        map_file.write(str(i)+"\t"+hostname_list[i]+"\n")

    # 生成HTML
    print("Generate HTML")
    html_file = open(output_dir_name+"/index.html", "w")
    html_file.write('''
<html>
<script type="text/javascript">
var border = 1;
var width  = {factor};
var count  = {host_num};
var zoomflag = 1;

var sendstats = [];
sendstats['min'] = {send_min};
sendstats['max'] = {send_max};
sendstats['avg'] = {send_avg};

var recvstats = [];
recvstats['min'] = {recv_min};
recvstats['max'] = {recv_max};
recvstats['avg'] = {recv_avg};
var rankmap = ["{hostname_list}"];

var sendimgjs = {send_sheet_big};

var recvimgjs = {recv_sheet_big};

'''.format(
    factor = factor,
    host_num = host_num,
    send_min = arg_list["Send min"],
    send_max = arg_list["Send max"],
    send_avg = arg_list["Send avg"],
    recv_min = arg_list["Recv min"],
    recv_max = arg_list["Recv max"],
    recv_avg = arg_list["Recv avg"],
    hostname_list = "\",\"".join([str(i) for i in range(host_num)]) if shift_flag else "\",\"".join(hostname_list),
    send_sheet_big = send_sheet_big[::-1],
    recv_sheet_big = recv_sheet_big[::-1]
))

    html_file.write(r'''
var tooltip;

function loading() {
  var sendimg = document.getElementById("send_img");
  sendimg.onmousemove=sendtrack;
  sendimg.onmouseout=hidetip;
  var recvimg = document.getElementById("recv_img");
  recvimg.onmousemove=recvtrack;
  recvimg.onmouseout=hidetip;

  tooltip = document.createElement("div");
  tooltip.style.visibility = "hidden";
  document.body.appendChild(tooltip);
}

function sendtrack(e) {
  var img  = document.getElementById("send_img");
  var zoom = document.getElementById("send_zoom");
  track(e,img," ==> ",sendimgjs,sendstats["max"],zoom);
}

function recvtrack(e) {
  var img  = document.getElementById("recv_img");
  var zoom = document.getElementById("recv_zoom");
  track(e,img," <== ",recvimgjs,recvstats["max"],zoom);
}

function track(e,img,dir,imgjs,max,zoom) {
  var relX = e.pageX - img.offsetLeft;
  var relY = e.pageY - img.offsetTop;
  var col = Math.floor((relX - border) / width);
  var row = Math.floor((relY - border) / width);

  document.body.style.cursor = "crosshair";

  if (row >= 0 && col >= 0 && row < count && col < count) {
    if (zoomflag) {
      var pixval = imgjs[(count*width)-1-row*width][col*width];
      var bw     = pixval;
      tooltip.innerHTML = '<div style="background-color: #AAFFFF;border: solid 1px; font-size: large;">' +
	"(" + relX + ", " + relY + ")<br>" +
	rankmap[row] + dir + rankmap[col] + "<br>" + bw + " MB/sec" + "<br>Measured by: " + rankmap[row] +
	zoomed(row,col,imgjs,dir,max) + '</div>';
    } else {
      tooltip.innerHTML = '<div style="background-color: #AAFFFF;border: solid 1px; font-size: large;">' +
	"(" + relX + ", " + relY + ")<br>" +
	rankmap[row] + dir + rankmap[col] + "<br>Measured by: " + rankmap[row] +
	'</div>';
    }
    tooltip.style.position = "absolute";
    tooltip.style.left = e.pageX + 20;
    tooltip.style.top    = "";
    tooltip.style.bottom = "";
    if ((e.pageY-window.pageYOffset) < window.innerHeight / 2) {
      tooltip.style.top = e.pageY + 20;
    } else {
      tooltip.style.bottom = window.innerHeight - e.pageY + 20;
    }
    tooltip.style.visibility = "visible"; 
  } else {
    hidetip();
  }
}

function hidetip() {
  tooltip.style.visibility = "hidden";
  document.body.style.cursor = "auto";
}

function zoomed(row,col,imgjs,dir,max) {
  var rows = "";
  var pad = 5;
  var header = "<td></td>";
  for(c=pad*2; c>=0; c--) {
    //var c2 = col*width+pad-c;
    //header += "<td style=\"background-color:#AAFFFF;\">" + rankmap[Math.floor(c2/width)] + "</td>";
    var c2 = col+pad-c;
    header += "<td style=\"background-color:#AAFFFF;\">" + rankmap[c2] + "</td>";
  }
  header = "<tr>" + header + "</tr>\n";
  for(r=pad*2; r>=0; r--) {
    var cell = "";
    for(c=pad*2; c>=0; c--) {
      //var r2 = row*width+pad-r;
      //var c2 = col*width+pad-c;
      var r2 = row*width+(pad-r)*width;
      var c2 = col*width+(pad-c)*width;
      if (r2 >= 0 && c2 >= 0 && r2 < count*width && c2 < count*width) {
        var pixval = imgjs[(count*width)-1-r2][c2];
        var bw     = pixval;
        pixval     = Math.round(pixval/max*255)
        var color  = (pixval < 128) ? "color: #FFFFFF;" : "";
        var border = (r == pad && c == pad) ? "border: solid 2px #FF0000;" : "";
        cell += "<td style=\"background-color: rgb(" + pixval + "," + pixval + "," + pixval + ");" + color + border + "\">" + bw + "</td>";
      } else {
        cell += "<td></td>";
      }
    }
    rows += "<tr>" + "<td style=\"background-color:#AAFFFF\">" 
            + rankmap[Math.floor(r2/width)] + dir + cell + "</td></tr>\n"; 
  }
  return "<table>" + header + rows + "</table>";
}
</script>
''')

    html_file.write(
'''
<body onload="loading();">
<h1>mpiGraph Details</h1>
<table>
<tr><td>Nodes:</td><td>{host_num}</td></tr>
<tr><td>MsgSize:</td><td>{MsgSize}</td></tr>
<tr><td>Times:</td><td>{Times}</td></tr>
<tr><td>Window:</td><td>{Window}</td></tr>
</table><br>
<a href="map.txt">MPI rank to node mapping</a><br>
<h1>Send Bandwidth</h1>
<table border="1">
<tr><td>min MB/s</td><td>max MB/s</td><td>avg MB/s</td></tr>
<tr><td>{send_min}</td><td>{send_max}</td><td>{send_avg}</td>
<tr><td>{send_min_percentage}%</td><td>{send_max_percentage}%</td><td>{send_avg_percentage}%</td></tr>
</table>
<img id="send_img" src="send{shift_flag}.bmp" border="1"/>
<img src="send_hist.png" border="1"/><div id="send_zoom"></div>
<h1>Receive Bandwidth</h1>
<table border="1"><tr><td>min MB/s</td><td>max MB/s</td><td>avg MB/s</td></tr>
<tr><td>{recv_min}</td><td>{recv_max}</td><td>{recv_avg}</td>
<tr><td>{recv_min_percentage}</td><td>{recv_max_percentage}</td><td>{recv_avg_percentage}%</td></tr>
</table>
<img id="recv_img" src="recv{shift_flag}.bmp" border="1"/>
<img src="recv_hist.png" border="1"/>
<div id="recv_zoom"></div>
</body></html>
'''.format(
    host_num = host_num,
    MsgSize = arg_list["MsgSize"],
    Times = arg_list["Times"],
    Window = arg_list["Window"],
    send_min = arg_list["Send min"],
    send_max = arg_list["Send max"],
    send_avg = arg_list["Send avg"],
    recv_min = arg_list["Recv min"],
    recv_max = arg_list["Recv max"],
    recv_avg = arg_list["Recv avg"],
    send_min_percentage = round(arg_list["Send min"]/arg_list["Send max"]*100, 2),
    send_max_percentage = round(arg_list["Send max"]/arg_list["Send max"]*100, 2),
    send_avg_percentage = round(arg_list["Send avg"]/arg_list["Send max"]*100, 2),
    recv_min_percentage = round(arg_list["Recv min"]/arg_list["Recv max"]*100, 2),
    recv_max_percentage = round(arg_list["Recv max"]/arg_list["Recv max"]*100, 2),
    recv_avg_percentage = round(arg_list["Recv avg"]/arg_list["Recv max"]*100, 2),
    shift_flag = "_shift" if shift_flag else ""
))

    if shift_flag:
        html_file.write(
            '''<h1>Send Shift</h1><table border="1">
<tr><td>shift</td><td>min MB/s</td><td>min %</td><td>avg MB/s</td><td>avg %</td><td>max MB/s</td></tr>
    ''')
        for shift in range(1, host_num):
            min_value = min([send_sheet[i][(i+shift)%host_num] for i in range(host_num)])
            min_percentage = int(min_value/arg_list["Send max"]*100)
            max_value = max([send_sheet[i][(i+shift)%host_num] for i in range(host_num)])
            avg_value = sum([send_sheet[i][(i+shift)%host_num] for i in range(host_num)])/host_num
            avg_percentage = int(avg_value/arg_list["Send max"]*100)
            if (avg_value >= 10):
                avg_value = int(avg_value)
            html_file.write("<tr><td>{shift}</td><td>{min_value} MB/s</td><td>{min_percentage}%</td><td>{avg_value} MB/s</td><td>{avg_percentage}%</td><td>{max_value} MB/s</td></tr>".format(
                shift=shift, min_value = min_value, min_percentage = min_percentage, avg_value = avg_value, avg_percentage = avg_percentage, max_value = max_value
            ))
        html_file.write("</table>")

    print("Program html_generator.py Finish")