# Project-7 - Failure Detection in ring (Node failure)

_Group 11: Losavio Fabio, Ferraro Luca, Colombo William, Tonelli Simone, Camajori Tedeschini Bernardo_  

The aim of the project is to build an application able to react to the failure of a switch (node), both in a _reactive_ and in a _proactive_ way, using OpenFlow switches and Ryu as network controller.  

## Demo setup
-----
To setup the project download the repository on your local machine. In order to make everything work [**mininet**](http://mininet.org/), [**ryu**](https://osrg.github.io/ryu/) and [**matplotlib**](https://matplotlib.org/) are required, install them before starting.

### Topology setup

First of all a simulated network topology is needed, to start the topology use the following command:

```
sudo mn --custom PATH_TO_FOLDER/project-7/ringTopo.py --mac --topo mytopo --controller=remote,ip=10.0.2.15,port=6633 --switch ovs,protocols=OpenFlow13
```

this will load the topology coded in the file [ringTopo.py](https://gitlab.com/switching-and-routing-polimi-code-repository/2019-2020/project-7/-/blob/master/ringTopo.py) which is a ring topology with 6 openflow switches each one linked to a single host.
Note that the program will work with any topology given that only one host is linked to each switch.

Here there is an example image of the implemented topology:  

![Image](/ReadmeMaterials/SAR2.png) 

### Controller statup

Once the topology is started, is possible to launch the Ryu network controller, here there are two choices:

* [**Reactive controller**](https://gitlab.com/switching-and-routing-polimi-code-repository/2019-2020/project-7/-/blob/master/Node_failure_reactive.py) - switches send a message when they are down and the controller recomputes the correct flow rules to install.

```
ryu-manager PATH_TO_FOLDER/project-7/Node_failure_reactive.py --observe-link
```

* [**Proactive controller**](https://gitlab.com/switching-and-routing-polimi-code-repository/2019-2020/project-7/-/blob/master/Node_failure_proactive.py) - every 5 seconds the controller sends a message to each switch to check if it is up or not, if no response is received the switch is marked as down and the controller corrects the flows. 

```
ryu-manager PATH_TO_FOLDER/project-7/Node_failure_proactive.py --observe-link
```

Now that both the network and the controller are up, the fist operation that has to be performed is a **pingall**, as shown in the following picture, so that the controller can register all the information about the hosts.  

![Image](/ReadmeMaterials/Pingall.png)

### Delay and packet loss statistics

To measure data about the delay, you can activate the [Delay_pkt_loss_statisitcs_live.py](https://gitlab.com/switching-and-routing-polimi-code-repository/2019-2020/project-7/-/blob/master/Delay_pkt_loss_statisitcs_live.py) python script using the command

```
python PATH_TO_FOLDER/project-7/Delay_pkt_loss_statisitcs_live.py
```

note that based on the python version installed on your device may be necessary to specify the correct interpreter to run the script.  
Once the script is started, a new window will open to show the computed statistics. At the beginning the window will be empty because no statistics are computed yet, if something appears on the screen check if the **dati.txt** file is empty, if not delete its content and try again. To start computing the correct statistics start an xterm terminal on any of the network hosts (for example h1) running this command on the mininet terminal,

```
mininet> xterm h1
```

this will allow you to directly control the virtual host. Now is possibile to start sending traffic from the host, using xterm terminal, in the network using the **PING tool**.  
To send packet to a single host use the ping command paired with **tee** to redirect the output on a file, the option -O allows to show on the terminal window a message when a packet is not correctly received and the option -a allows to add the output in the pre-existing file (example ping to h3 with ip 10.0.0.3):

```
ping 10.0.0.3 -O | tee -a PATH_TO_FOLDER/project-7/dati.txt
```

If you want to performa a ping to all the hosts in the network you can use a simple bash script, [ping_variable.sh](https://gitlab.com/switching-and-routing-polimi-code-repository/2019-2020/project-7/-/blob/master/ping_variable.sh), which uses bash to start a ping command directed to all the other hosts. Once the scipt is called, using the following command,

```
bash PATH_TO_FOLDER/project-7/ping_variable.sh
```

the user will visualize a message in which he will be asked to insert the numer of packets to send. The accepted values are all the natural numbers (1,2,3,...) and _inf_ which will start an unlimited packet stream between the source and all the other destinations.
In case of a finite number of packets the simulation will atuomatically stop once the correct amount of messages is sent, otherwhise the user will need to stop the simulation using the _Ctrl+C_ shotcut. During the ping process the user will visualize a live plot of the delay between the hosts and, once the ping is stopped, information about the pkt loss percentage.  
Is important to note that the bash script will work with the [ringTopo.py](https://gitlab.com/switching-and-routing-polimi-code-repository/2019-2020/project-7/-/blob/master/ringTopo.py) topology since pings will use hosts of that particular topology or with any other topology with 6 hosts with ips from **10.0.0.1 to 10.0.0.6**.  

During the ping process is also possible to stop any of the switches, even more than one, to see how the delay changes. To stop a switch a simple command on the mininet terminal can be performed:

```
mininet> switch S1 stop
```

and to reactivate it  use

```
mininet> switch S1 start
```

### Bandwidth statistics

With the same network and controller setup is possible to compute statistics about the total bandwidth available on a particular link. To do that the [**iperf tool**](https://iperf.fr/) is required.  
First of all the python script needs to be start up, the same consideration valid for the previous sections also holds for this one, to start the script the following command needs to be performed. 

```
python  PATH_TO_FOLDER/project-7/Bandwidth_statistics_live.py
```

In order to effectively use the iperf command a tcp channel will be set up between two hosts, one will act as a client and the other one will act as a server. To do so an xterm terminal has to be open on both the hosts using the mininet window and performing the following command (channel between h1 and h3 in the example).

```
mininet> xterm h1 h3

or

mininet> xterm h1
mininet> xterm h3
```

Once obtained the access to both the hosts, is possible to start a server (option -s) on one of the two (for example h3)

```
iperf -s
```

and a client (option -c) on the other one (for example h1)

```
iperf -c 10.0.0.3 -t 100 -i 1 | tee -a PATH_TO_FOLDER/project-7/dati.txt 
```

in this command the option -t identifies the time duration, in seconds, of the transmission and the option -i sets the interval time in seconds between periodic bandwidth, jitter, and loss reports. As in the previous case the output is reditected using **tee** on a dedicated file.  

Once this command is activated, a live graph should start to appear on the graph window showing the computed bandwidth between the selected hosts. Also in this case is possible to stop one or more switches to see how the bandwidth changes.
