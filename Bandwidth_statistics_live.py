import math
import re
import matplotlib.pyplot as plt
import time
import matplotlib.animation as animation
import pylab
import time

# Length of the moving average filter
W = 10

# Samples to plot
S = 1000

def animate(i):

	# File from which data is taken:
	#file = "/Users/bernicama/PROGRAMMI/mag_primo anno/Switching and routing/Laboratorio_SDN/Prove Progetto S&R/dati.txt"
	#file = "/home/fabio/Scrivania/out.txt"
	file = "/Users/bernicama/PROGRAMMI/mag_primo anno/Switching and routing/Laboratorio_SDN/project-7/dati.txt"

	# Opening and reading file:
	stat_file = open(file, 'r').read()

	# x and y axis:
	x = []
	y = []

	# For min/max/avg
	z = []

	# Host between which iperf is being performed:
	ip = []

	# Splitting file in lines:
	lines = stat_file.split('\n')

	# For moving average filter of W samples
	window= [0] * W

	# For preparing x-axis	
	j = 0
		
	# Scanning lines:
	for line in lines:

		# Ensure data is valid
		if len(line) > 1 and not re.search("connecting",line) and not re.search("Sending",line) and not re.search("window",line) and not re.search("Sent",line) \
		    and not re.match("-",line):
		
			# Info about hosts between which iperf test is being performed:
			if re.search("local",line):

				# For locating all points in the current line:
				points_index = []
				line6 = line
				curr_index = 0
				aux = 0
				p = '.'

				# At the end, points_index contains the position of all the points in the 6th row:
				while curr_index < len(line6) and aux != -1:
					curr_index = line6.find(p, curr_index)
					aux = curr_index
					points_index.append(curr_index)
					curr_index += 1

				# Looking for the position of the beginning of the first IP address:
				ip1_start = points_index[0]
				while line[ip1_start] != ' ':
					ip1_start -= 1
				ip1_start += 1

				# Looking for the position of the end of the first IP:
				ip1_end = ip1_start
				while line[ip1_end] != ' ':
					ip1_end += 1

				# First IP:
				ip1 = line[ip1_start:ip1_end]
				#print(ip1)

				# Looking for the position of the beginning of the second IP address:
				ip2_start = points_index[3]
				while line[ip2_start] != ' ':
					ip2_start -= 1
				ip2_start += 1

				# Looking for the position of the end of the second IP:
				ip2_end = ip2_start
				while line[ip2_end] != ' ':
					ip2_end += 1

				# Second IP:
				ip2 = line[ip2_start:ip2_end]
				#print(ip2)

				# If the connection between ip1 and ip2 is new
				if not any( ip1 == ip_src and ip2 == ip_dst for ip_src,ip_dst in ip):

					ip.append([ip1,ip2])

					# For moving average filter of 10 samples
					window = [0] * W

					y.append([])

					# min max avg
					z.append([ 10**15 , 0 , 0])

			# Finding info about where bw info is stored	
			elif re.search("Interval",line):

				# Beginning of bw info:
				bw_index = line.find("B")

			elif re.search("sec",line):

				# Needed for measurements units (Kbps, Mbps, ...):
				nSpace = 0

				# Looking for the position of the beginning of the bw info:
				start_index = bw_index
				while line[start_index] == ' ':
					start_index += 1
					nSpace += 1

				# Looking for the position of the end of the bw info:
				end_index = start_index
				while line[end_index] != ' ':
					end_index += 1

				if line[end_index+1] == 'K':
					exp = 3

				elif line[end_index+1] == 'M':
					exp = 6

				elif line[end_index+1] == 'G':
					exp = 9

				elif line[end_index+1] == 'T':
					exp = 12

				# Setting the bw:
				power = 3*nSpace
				y_value = [float(line[start_index:end_index]) , exp]

				# Update the window
				window.pop(0)
				window.append(y_value[0]*10**(y_value[1]))
				new = sum(window)/len(window)
				new = [new/float(10**(len(str(int(new)))-1)),(len(str(int(new)))-1)] 

				# Append samples
				y[ip.index([ip1,ip2])].append(new)

				# For real representation of samples
				#y[ip.index([ip1,ip2])].append(y_value)

				# Update min
				if y_value[0]*10**(y_value[1]) < z[ip.index([ip1,ip2])][0]:
					z[ip.index([ip1,ip2])][0] = y_value[0]*10**(y_value[1])

				# Update max
				if y_value[0]*10**(y_value[1]) > z[ip.index([ip1,ip2])][1]:
					z[ip.index([ip1,ip2])][1] = y_value[0]*10**(y_value[1])


	# Preparing x axis and find avg:
	i = 0
	for ip_ in y:

		x.append(range(0,len(y[i])))

		for j in range(0,(len(y[i]))):
			z[i][2] = z[i][2]+ y[i][j][0]*10**(y[i][j][1])

		if len(y[i]):
			z[i][2] = z[i][2]/len(y[i])

		i= i + 1
	

	i = 0
	ax = []
	fig.clf()

	# Plot
	for w in range(0,(len(ip))):

		ax.append(fig.add_subplot(len(ip),1,i+1))

		ax[i].clear()
		#ax1.set_yscale('log') #logarithmic scale

		if any (12 == y_value[1] for y_value in y[i]):
			
			for j in range(0,(len(y[i]))):
				y[i][j] = y[i][j][0]*10**(-12+y[i][j][1])
			ax[i].set_ylabel('Bandwith[Tbits/s]')

			z[i][0] = z[i][0]*10**(-12)
			z[i][1] = z[i][1]*10**(-12)
			z[i][2] = z[i][2]*10**(-12)

		elif any (9 == y_value[1] for y_value in y[i]):

			for j in range(0,(len(y[i]))):
				y[i][j] = y[i][j][0]*10**(-9+y[i][j][1])
			ax[i].set_ylabel('Bandwith[Gbits/s]')

			z[i][0] = z[i][0]*10**(-9)
			z[i][1] = z[i][1]*10**(-9)
			z[i][2] = z[i][2]*10**(-9)

		elif any (6 == y_value[1] for y_value in y[i]):

			for j in range(0,(len(y[i]))):
				y[i][j] = y[i][j][0]*10**(-6+y[i][j][1])	
			ax[i].set_ylabel('Bandwith[Mbits/s]')

			z[i][0] = z[i][0]*10**(-6)
			z[i][1] = z[i][1]*10**(-6)
			z[i][2] = z[i][2]*10**(-6)

		elif any (3 == y_value[1] for y_value in y[i]):	

			for j in range(0,(len(y[i]))):
				y[i][j] = y[i][j][0]*10**(-3+y[i][j][1])
			ax[i].set_ylabel('Bandwith[Kbits/s]')

			z[i][0] = z[i][0]*10**(-3)
			z[i][1] = z[i][1]*10**(-3)
			z[i][2] = z[i][2]*10**(-3)

		# Rapresent last S samples
		x[i] = x[i][:S]
		y[i] = y[i][-S:]

		ax[i].plot(x[i], y[i])

		if i == len(ip)-1:
			ax[i].set_xlabel('Time')
			
		ax[i].set_title('client=' + (ip[i][0]) + ' server=' + (ip[i][1]) + ' min=' + str(z[i][0]) + ' max=' + str(z[i][1]) + ' avg=' + str(z[i][2]), fontsize=11)

		ax[i].tick_params(axis='both', which='major', labelsize=8)

		ax[i].grid()

		i = i + 1

ax = []

fig = plt.figure()

ani = animation.FuncAnimation(fig, animate, interval=1000)

plt.show()