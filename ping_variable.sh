#!/bin/bash

#insert the path of the output file in path variable
#path="/home/fabio/Scrivania/out.txt"
path="/vagrant/project-7/dati.txt"

#print on the command line and read the user input
read -p 'How many packets do you want to send? ' num_pkts

#call a series of pings to all other hosts. Insert inf to send packet without stopping automatically.
if [ $num_pkts != inf ] 
then
	ping 10.0.0.1 -c $num_pkts -O | tee -a "$path" & 
	ping 10.0.0.2 -c $num_pkts -O | tee -a "$path" & 
	ping 10.0.0.3 -c $num_pkts -O | tee -a "$path" & 
	ping 10.0.0.4 -c $num_pkts -O | tee -a "$path" & 
	ping 10.0.0.5 -c $num_pkts -O | tee -a "$path" & 
	ping 10.0.0.6 -c $num_pkts -O >> "$path" 

else
	ping 10.0.0.1 -O | tee -a "$path" & 
	ping 10.0.0.2 -O | tee -a "$path" & 
	ping 10.0.0.3 -O | tee -a "$path" & 
	ping 10.0.0.4 -O | tee -a "$path" & 
	ping 10.0.0.5 -O | tee -a "$path" & 
	ping 10.0.0.6 -O >> "$path" 
	
fi

done


#ctr +| 
