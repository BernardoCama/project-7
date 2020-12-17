import re
import matplotlib.pyplot as plt
import time
import matplotlib.animation as animation
import pylab

# Length of the moving average filter
W = 10

# Samples to plot
S = 50

def animate(i):

	# FIle from which data is taken:
	#file = "/Users/bernicama/PROGRAMMI/mag_primo anno/Switching and routing/Laboratorio_SDN/Prove Progetto S&R/dati.txt"
	#file = "/home/fabio/Scrivania/out.txt"
	file = "/Users/bernicama/PROGRAMMI/mag_primo anno/Switching and routing/Laboratorio_SDN/project-7/dati.txt"

	# Opening and reading delay statistics file 
	stat_file = open(file, 'r').read()

	# x and y axis:
	x = []
	y = []

	# For min/max/avg/pkt_loss
	z = []

	# IP address
	ip = []

	lines = stat_file.split('\n')

	# For moving average filter of W samples
	window = [0] * W

	# Index of the line
	line_index = 0

	# Scanning lines:
	for line in lines:

		# Ensure data is valid
		if len(line) > 1:

			if re.match("P",line):

				# Separate words of the line
				words = line.split(' ')

				# Recover ip address
				words = words[1]

				if not any( words == ip_dst for ip_dst in ip):

					# Save new ip address
					ip.append(words)

					# For moving average filter of 10 samples
					window= [0] * W

					y.append([])

					# min max avg pkt_loss
					z.append([1000 , 0 , 0, -1])


			elif not re.search("---",line) and not re.search("packets",line) \
			and not re.search("rtt",line) and not re.search("Unreachable",line)\
			 and not re.search("no",line) and not re.search("pipe",line):

				# Separate words of the line
				words = line.split(' ')

				# Recover ip address
				words = words[3]
				words = words[:-1]

				# Count the occurence of '=':
				count = 0

				# Indicates where the information about delay starts:
				index = 0

				for c in line:
					if c == "=":
						count = count + 1
					index = index + 1
					if count == 3:

						# Update the window
						window.pop(0)
						i = index
						while (line[i] != " "):
							i = i + 1 
						new=float(line[index:i])
						window.append(new)


						# Append samples
						y[ip.index(words)].append(sum(window)/len(window))

						# Update min
						if new < z[ip.index(words)][0]:
							z[ip.index(words)][0] = new

						# Update max
						if new > z[ip.index(words)][1]:
							z[ip.index(words)][1] = new

						# Negative pkt loss
						z[ip.index(words)][3] = -1

						# For real representation of samples
						#y[ip.index(words)].append(new)

						break

			# Packet loss			
			elif re.search("packets transmitted",line):

					# Separate words of the line
					index1 = line.index('%')
					index2 = index1

					# Recover pkt loss
					while line[index2] != ' ':
						index2 = index2 - 1
					words1 = line[index2:index1]
					
					# Separate words of the line
					words2 = lines[line_index-1].split(' ')
					# Recover ip address
					words2 = words2[1]

					# Update pkts loss
					z[ip.index(words2)][3] = words1

		line_index = line_index + 1
			
	# Preparing x axis and find avg:
	i = 0
	for ip_ in ip:

		x.append(range(0,len(y[i])))

		if len(y[i]):

			# Avg
			z[i][2] = sum(y[i])/len(y[i])

		i = i + 1
	
	i = 0
	ax = []
	fig.clf()

	# Plot
	for w in range(0,(len(ip))):

		if len(ip) < 2:

			ax.append(fig.add_subplot( len(ip)/2 + 1 , 1 , i+1 ))

		else: 

			ax.append(fig.add_subplot( len(ip)/2 + 1 , 2 , i+1 ))

		ax[i].clear()
		#ax1.set_yscale('log') #logarithmic scale

		# Rapresent last S samples
		x[i] = x[i][-S:]
		y[i] = y[i][-S:]

		ax[i].plot(x[i], y[i])

		if i == len(ip)-1 or i == len(ip)-2:
			ax[i].set_xlabel('Time')
			
		ax[i].set_ylabel('Delay')

		# If statistics are collected
		if z[i][3] != -1:

			ax[i].set_title(ip[i] + ' min=' + str(z[i][0]) + ' max=' + str(z[i][1]) +' avg=' + str(z[i][2]) + ' pkt_loss=' + str(z[i][3]) + '%', fontsize=11)
		
		else:

			ax[i].set_title(ip[i] + ' min=' + str(z[i][0]) + ' max=' + str(z[i][1]) +' avg=' + str(z[i][2]) , fontsize=11)
		
		ax[i].tick_params(axis='both', which='major', labelsize=8)

		ax[i].grid()

		i= i + 1

ax = []

fig = plt.figure()

ani = animation.FuncAnimation(fig, animate, interval=1000)

plt.show()

