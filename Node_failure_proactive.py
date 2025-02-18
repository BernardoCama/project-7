#!/usr/bin/env python
# -*- coding: utf-8 -*-

from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller import dpset
from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER, HANDSHAKE_DISPATCHER
from ryu.app.wsgi import ControllerBase, WSGIApplication, route
from ryu.controller.handler import set_ev_cls
from ryu.ofproto import ofproto_v1_3
from ryu.lib.packet import packet
from ryu.lib.packet import ethernet
from ryu.lib.packet import ether_types
from ryu.topology.api import get_switch, get_link, get_host, get_all_host
from ryu.topology import event, switches
import networkx as nx
import json
import logging
import struct
import time
import copy
import threading
from webob import Response
from ryu.lib.mac import haddr_to_bin
from ryu.lib.packet.packet import Packet
from ryu.lib.packet import arp
from ryu.lib.packet import ipv4
from ryu.lib.packet import tcp
from ryu.lib.packet import udp
from ryu.ofproto import ether
from ryu.app.ofctl.api import get_datapath

NUMBER_OF_SWITCHES = 6  # number of switches in the topology used


class ZodiacSwitch(app_manager.RyuApp):
	OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]
	_CONTEXTS = {'wsgi': WSGIApplication}

	def __init__(self, *args, **kwargs):
		super(ZodiacSwitch, self).__init__(*args, **kwargs)
		wsgi = kwargs['wsgi']
		self.topology_api_app = self
		self.net = nx.DiGraph()

		#variable to set threading delay between two checks of the switch status
		self.DELAY = 5.0

		#in order not to print many times the topo matrix
		self.GLOBAL_VARIABLE = 0

		self.topo_matrix = []  # matrix for topology discovery

		# internal variable used to know when all the switches are connected
		self.SWITCHES_DISCOVERED = 0

		#list of all the switches of the net
		self.ORIGINAL_SWITCHES = []

		#list of all active switches of the net
		self.ACTIVE_SWITCHES = []

		self.topology = {}

		#list of the links
		self.links = []

		#list of the active ports of the switches
		self.switch_list = []

		#-------------------- NEW

		# 1 if switch is up, 0 otherwise	
		self.switch_up = [1] * NUMBER_OF_SWITCHES

		#check the status of the switches
		self.switch_status()


# ---EVENT MANAGEMENT--------------------------------------------------------------------------------
	@set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
	def switch_features_handler(self, ev):
		datapath = ev.msg.datapath
		ofproto = datapath.ofproto
		parser = datapath.ofproto_parser

		# install table-miss flow entry
		match = parser.OFPMatch()
		actions = [parser.OFPActionOutput(ofproto.OFPP_CONTROLLER,
											ofproto.OFPCML_NO_BUFFER)]
		self.add_flow(datapath, 0, match, actions)


	#aAn event to notify the correct receipt of flow stats
	@set_ev_cls(ofp_event.EventOFPFlowStatsReply, MAIN_DISPATCHER)
	def _flow_stats_reply_handler(self, ev):

		datapath = ev.msg.datapath

		#print ('Switch %d alive'% datapath.id)

		#The switch that has replied is still up
		self.switch_up[self.ORIGINAL_SWITCHES.index(datapath.id)] = 1

	#An event to notify connection of a switch
	@set_ev_cls(dpset.EventDP, MAIN_DISPATCHER)
	def _event_dp_handler(self, ev):

		pid = ev.dp.id

		#Updating net topology
		self.net = nx.DiGraph()

		#In order to leave the time to switches to go up
		if self.GLOBAL_VARIABLE == 1:
			time.sleep(2)

		switch_list = get_switch(self.topology_api_app, None)
		switches = [switch.dp.id for switch in switch_list]
		self.net.add_nodes_from(switches)
		links_list = get_link(self.topology_api_app, None)
		links = [(link.src.dpid, link.dst.dpid, {
		          'port': link.src.port_no}) for link in links_list]
		self.net.add_edges_from(links)
		links = [(link.dst.dpid, link.src.dpid, {
		          'port': link.dst.port_no}) for link in links_list]
		self.net.add_edges_from(links)
		

		#If a switch enters
		if ev.enter:

			print('Switch %d enters\n' % pid)

			self.SWITCHES_DISCOVERED = self.SWITCHES_DISCOVERED + 1  # Incremented every time a switch wakes up

			#Add flow to reach host linked to the switch that woke up
			if self.GLOBAL_VARIABLE == 1:

				#Switch is up
				self.switch_up[self.ORIGINAL_SWITCHES.index(pid)] = 1

				for ip in self.topology:
					if self.topology[ip][0] == pid:
						ip_dst = ip
						in_port = self.topology[ip][1]
										
				datapath = get_datapath(self, pid)

				match = datapath.ofproto_parser.OFPMatch(eth_type = 0x0800, ipv4_dst = ip_dst)
				
				actions = [datapath.ofproto_parser.OFPActionOutput(in_port,
													datapath.ofproto.OFPCML_NO_BUFFER)]
				
				self.add_flow(datapath, 2, match, actions)	
				print ('Add flow in switch s%d with match=%s output=%s'%(pid, ip_dst, in_port  ))


			#When all the switches are up compute the matrix from scratch
			if self.SWITCHES_DISCOVERED == NUMBER_OF_SWITCHES:

				#Save the list of original switches
				self.ORIGINAL_SWITCHES=switches

				self.ACTIVE_SWITCHES=copy.copy(self.ORIGINAL_SWITCHES)

				#Save the list of original links
				self.links = [(link.src.dpid, link.dst.dpid, {
					'port': link.src.port_no}) for link in links_list]

				#Save the list of active ports
				self.switch_list = switch_list


				self.topo_matrix = []


				for src in switches:
					self.topo_matrix.append([])
					for dst in switches:
						index = switches.index(src)
						#Shortest path between each pair
						path = nx.shortest_path(self.net, src, dst)
						self.topo_matrix[index].append(path)

				#Restore original flows
				if self.GLOBAL_VARIABLE == 1:

					i = 0

					for row in self.topo_matrix:

						j = 0

						for column in row:

							if i != j:

								s2 = self.topo_matrix[i][j][1]
						
								for ip in self.topology:
									if self.topology[ip][0] == self.ORIGINAL_SWITCHES[j]:
										ip_dst = ip
							
								for link in self.links:
									if link[0] == self.ORIGINAL_SWITCHES[i] and link[1]==s2:
										out_port = link[2]['port']					
								
								datapath = get_datapath(self, self.ORIGINAL_SWITCHES[i])
								
								match = datapath.ofproto_parser.OFPMatch( eth_type = 0x0800, ipv4_dst = ip_dst)
								
								actions = [datapath.ofproto_parser.OFPActionOutput(out_port, datapath.ofproto.OFPCML_NO_BUFFER)]
								
								#Add flows in the switch just woke up
								if self.ORIGINAL_SWITCHES[i] == pid:

									self.add_flow(datapath, 1, match, actions)
									#print ('Add flow in switch s%d with match=%s output=%s'%(datapath.id, ip_dst, out_port  ))

								#Modify flows in the other switches
								else:

									self.modify_flow( datapath , match, actions)
									#print ('Modify flow in switch s%d with match=%s output=%s'%(datapath.id, ip_dst, out_port  ))

							j = j + 1

						i = i + 1
		
				self.GLOBAL_VARIABLE = 1

				#update switches list    
				print('Switches in the net: %s\n'% switches)
				print("\nTopology Matrix")
				print(self.topo_matrix)
				print('\n\n')

			#If not all switches are up
			else:

				self.ACTIVE_SWITCHES.append(pid)

				i = 0

				for row in self.topo_matrix:

					j = 0

					for column in row:

						if column == []:

							#Updating flows of ACTIVE switches
							if self.ORIGINAL_SWITCHES[i] in switches:

								#If destination switch is ACTIVE
								if self.ORIGINAL_SWITCHES[j] in switches:

									#If there exists a path
									try:

										path = nx.shortest_path(self.net, self.ORIGINAL_SWITCHES[i], self.ORIGINAL_SWITCHES[j])

										#Update topo_matrix
										self.topo_matrix[i][j] = path
									
										#If all switches has been discovered
										if self.GLOBAL_VARIABLE == 1:

											s2 = self.topo_matrix[i][j][1]
									
											for ip in self.topology:
												if self.topology[ip][0] == self.ORIGINAL_SWITCHES[j]:
													ip_dst = ip
										
											for link in self.links:
												if link[0] == self.ORIGINAL_SWITCHES[i] and link[1] == s2:
													out_port = link[2]['port']					
											
											datapath = get_datapath(self, self.ORIGINAL_SWITCHES[i])
											
											match = datapath.ofproto_parser.OFPMatch( eth_type = 0x0800, ipv4_dst = ip_dst)
											
											actions = [datapath.ofproto_parser.OFPActionOutput(out_port, datapath.ofproto.OFPCML_NO_BUFFER)]
											
											#Add flows to the switch that woke up
											if datapath.id == pid:
												
												#Add flows to reach other host
												self.add_flow(datapath, 1, match, actions)
												print('Add flow in switch s%d with match=%s output=%s'%(datapath.id, ip_dst, out_port  ))

											#Modify flows of other switches
											else:

												self.modify_flow(datapath , match, actions)
												print('Modify flow in switch s%d with match=%s output=%s'%(datapath.id, ip_dst, out_port  ))
											

									#If the two switches are inable to communicate
									except:
										
										#If all switches has been discovered
										if self.GLOBAL_VARIABLE == 1:

											#Add flows of dropping packets towards switches ACTIVE and UNREACHABLE in the switch just woke up
											if self.ORIGINAL_SWITCHES[i] == pid and self.ORIGINAL_SWITCHES[j] != pid:

												datapath = get_datapath(self, self.ORIGINAL_SWITCHES[i])

												for ip in self.topology:
													if self.topology[ip][0] == self.ORIGINAL_SWITCHES[j]:
														ip_dst = ip

												match = datapath.ofproto_parser.OFPMatch(eth_type = 0x0800, ipv4_dst = ip_dst)

												actions = []

												self.add_flow(datapath, 1 ,match, actions)
												print('Add flow in switch s%d with match=%s with dropping'%(datapath.id, ip_dst))

								#If destination switch is DOWN
								else:

									#Add flows of dropping packets towards switches DOWN in the switch just woke up
									if self.ORIGINAL_SWITCHES[i] == pid:

										datapath = get_datapath(self, self.ORIGINAL_SWITCHES[i])

										for ip in self.topology:
											if self.topology[ip][0] == self.ORIGINAL_SWITCHES[j]:
												ip_dst = ip

										match = datapath.ofproto_parser.OFPMatch( eth_type = 0x0800, ipv4_dst = ip_dst)

										actions = []

										self.add_flow(datapath, 1, match, actions)
										print('Add flow in switch s%d with match=%s with dropping'%(datapath.id, ip_dst))

						j = j + 1

					i = i + 1

				if self.GLOBAL_VARIABLE == 1:
					#Update switches's list    
					print('Switches in the net: %s\n'% switches)
					print("\nTopology Matrix")
					print(self.topo_matrix)
					print('\n\n')


	@set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
	def packet_in_handler(self, event):
		msg = event.msg
		datapath = msg.datapath
		ofproto = datapath.ofproto
		in_port = msg.match["in_port"]
		parser = datapath.ofproto_parser

		pkt = packet.Packet(msg.data)
		ethframe = pkt.get_protocol(ethernet.ethernet)

		self.set_topology(pkt, in_port, datapath)

		ethframe = pkt.get_protocol(ethernet.ethernet)

	# HANDLE ARP PACKETS--------------------------------------------

		# If it is an ARP packet
		if ethframe.ethertype == ether_types.ETH_TYPE_ARP:
			arp_packet = pkt.get_protocol(arp.arp)
			arp_dst_ip = arp_packet.dst_ip
			arp_src_ip = arp_packet.src_ip

			# If it is an ARP request
			if arp_packet.opcode == 1:	

				#Forwarding the ARP request to all other hosts
				for switch in self.ACTIVE_SWITCHES:

					if switch != datapath.id:

						#Ports of the switch in which to forward ARP request
						ports = self.port_to_host(switch)

						for port in ports:

							#print ('Try to send arp request from switch %d, to port %d,\n of host with ip %s, mac %s,\n to host with ip %s'%(switch,port,arp_src_ip, ethframe.src,  arp_dst_ip))
							
							dp = get_datapath(self, switch)

							if dp is not None:

								self.send_arp(dp, 1, ethframe.src, arp_src_ip, ethframe.dst, arp_dst_ip, port)


			# If it is an ARP reply
			else:

				#Forwarding the ARP reply to the host target of the ARP reply
				switch = self.topology[arp_dst_ip][0]

				if switch in self.ACTIVE_SWITCHES:

					port = self.topology[arp_dst_ip][1]

					#print ('Try to send arp reply from switch %d, to port %d,\n of host with ip %s, mac %s,\n to host with ip %s'%(switch,port,arp_src_ip, ethframe.src,  arp_dst_ip))
						
					dp = get_datapath(self, switch)

					if dp is not None:

						self.send_arp(dp, 2, ethframe.src, arp_src_ip, ethframe.dst, arp_dst_ip, port)




			# when all the switches are up go on installing flows
			if self.SWITCHES_DISCOVERED == NUMBER_OF_SWITCHES:


				#Add flow to reach host linked to the switch
				match = parser.OFPMatch(eth_type = 0x0800, ipv4_dst=arp_src_ip)
				actions = [parser.OFPActionOutput(in_port,
													ofproto.OFPCML_NO_BUFFER)]
				self.add_flow(datapath, 2, match, actions)	


				#Installing flows in every switch to reach the host that has send or request the arp packet
				for switch in self.ACTIVE_SWITCHES:

					if switch != datapath.id:

						dp = get_datapath(self, switch)

						if dp is not None:

							match = dp.ofproto_parser.OFPMatch(eth_type = 0x0800, ipv4_dst = arp_src_ip)

							#Search in topo_matrix which is the switch towards which forward the packet 
							s2 = self.topo_matrix[self.ORIGINAL_SWITCHES.index(switch)][self.ORIGINAL_SWITCHES.index(datapath.id)]

							if s2 != []:

								s2 = s2[1]
								#print (switch, s2)

								for link in self.links:
									if link[0] == switch and link[1] == s2:
										out_port = link[2]['port']
										#print out_port

								actions = [dp.ofproto_parser.OFPActionOutput(out_port, dp.ofproto.OFPCML_NO_BUFFER)]

								priority = 1

								self.add_flow(dp, priority, match, actions)
								#print ('add flow in switch s%d with match=%s output=%s'%(dp.id, arp_src_ip, out_port  ))


	# HANDLE IP PACKETS--------------------------------------------
	#In order NOT to loose the first IP packet

		#If it is an IP packet
		if ethframe.ethertype == 2048:

			frame = pkt.get_protocol(ipv4.ipv4)
			ip_src = frame.src
			ip_dst = frame.dst

			switch_dst = self.topology[ip_dst][0]

			#Search in topo_matrix which is the switch towards which forward the packet 
			s2 = self.topo_matrix[self.ORIGINAL_SWITCHES.index(datapath.id)][self.ORIGINAL_SWITCHES.index(switch_dst)][1]


			for link in self.links:
				if link[0] == datapath.id and link[1] == s2:
					out_port = link[2]['port']
					#print out_port

			actions = [datapath.ofproto_parser.OFPActionOutput(out_port)]
			data = msg.data
			pkt = packet.Packet(data)
			eth = pkt.get_protocols(ethernet.ethernet)[0]

			pkt.serialize()
			out = datapath.ofproto_parser.OFPPacketOut(
			datapath = datapath, buffer_id = 0xffffffff, in_port = datapath.ofproto.OFPP_CONTROLLER,
				actions = actions, data = pkt.data)

			#Forward the packet in the right direction
			datapath.send_msg(out)

# ---Additional functions------------------------------------------------------
	def add_flow(self, datapath, priority, match, actions, buffer_id=None):
		ofproto = datapath.ofproto
		parser = datapath.ofproto_parser

		inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS,
												actions)]
		if buffer_id:
			mod = parser.OFPFlowMod(datapath = datapath, buffer_id = buffer_id,
									priority = priority, match = match,
									instructions = inst)
		else:
			mod = parser.OFPFlowMod(datapath = datapath, priority = priority,
									match = match, instructions = inst)
		datapath.send_msg(mod)

	def modify_flow(self, datapath, match, actions):

		ofproto = datapath.ofproto
		parser = datapath.ofproto_parser

		inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS,
												actions)]
		mod = parser.OFPFlowMod(
				datapath, command = ofproto.OFPFC_MODIFY,
				out_port = ofproto.OFPP_ANY, out_group = ofproto.OFPG_ANY,
				priority = 1,
				match = match, instructions = inst)

		datapath.send_msg(mod)


	def set_topology(self, pkt, in_port, datapath):
		ethframe = pkt.get_protocol(ethernet.ethernet)

		if ethframe.ethertype == 2048:  # frame ip
			frame = pkt.get_protocol(ipv4.ipv4)
			ip = frame.src
			#print('it is a pkt ip in switch %d from %s to %s'%(datapath.id, ip,frame.dst))

		elif ethframe.ethertype == 2054:  # frame arp
			frame = pkt.get_protocol(arp.arp)
			ip = frame.src_ip
			
		else:
			return

		#self.topology.setdefault(datapath.id, {})
		self.topology.setdefault(ip , {})
		#self.topology[datapath.id][ethframe.src] = [in_port, ip]
		self.topology[ip] = [datapath.id, in_port, ethframe.src]

		# DEBUG -> stampa a schermo il dizionario topologia contenete mac, ip e porta di ogni host divisi per switch
		#self.logger.info(self.topology)
		#self.logger.info('\n')

	def send_arp(self, datapath, opcode, srcMac, srcIp, dstMac, dstIp, outPort):
		# If it is an ARP request
		if opcode == 1:
			targetMac = "00:00:00:00:00:00"
			targetIp = dstIp
		# If it is an ARP reply
		elif opcode == 2:
			targetMac = dstMac
			targetIp = dstIp

		e = ethernet.ethernet(dstMac, srcMac, ether.ETH_TYPE_ARP)
		a = arp.arp(1, 0x0800, 6, 4, opcode, srcMac, srcIp, targetMac, targetIp)
		p = Packet()
		p.add_protocol(e)
		p.add_protocol(a)
		p.serialize()
	
		actions = [datapath.ofproto_parser.OFPActionOutput(outPort)]
		out = datapath.ofproto_parser.OFPPacketOut(
				datapath = datapath,
				buffer_id = 0xffffffff,
				in_port = datapath.ofproto.OFPP_CONTROLLER,
				actions = actions,
				data = p.data)
		datapath.send_msg(out)

	#Return the list of ports in which there is an host
	def port_to_host (self, dpid):
		ports1 = []
		ports2 = []

		for switch in self.switch_list:
			for s1 in switch.ports:
				if s1.dpid == dpid:
					ports1.append(s1.port_no)

		for link in self.links:
			if link[0] == dpid:
				ports2.append(link[2]['port'])

		#print ('ports live of switch %d: %s'%(dpid, ports1))
		#print ('ports towards switches %s'%ports2)

		return[x for x in ports1 if x not in ports2]

	#Request of flow status
	def _request_stats(self, datapath):
		self.logger.debug('send stats request: %016x', datapath.id)
		ofproto = datapath.ofproto
		parser = datapath.ofproto_parser

		req = parser.OFPFlowStatsRequest(datapath)
		datapath.send_msg(req)

	#Check if switches are alive		
	def switch_status(self):

		#Set TIMER every DELAY seconds
		threading.Timer(self.DELAY, self.switch_status).start()

		if self.GLOBAL_VARIABLE == 1:

			for i in range(0,NUMBER_OF_SWITCHES):

				if self.switch_up[i] == 1:
					print ('Switch %d is up' %self.ORIGINAL_SWITCHES[i])

				else:
					print ('Switch %d is down' %self.ORIGINAL_SWITCHES[i])

					#If the switch is down AND we have not modified the topo_matrix YET
					if self.topo_matrix[i][i] != []:

						#Updating net topology
						self.net = nx.DiGraph()

						#In order to leave the time to switches to go up
						if self.GLOBAL_VARIABLE == 1:
							time.sleep(2)

						#Topology discovery
						switch_list = get_switch(self.topology_api_app, None)
						switches = [switch.dp.id for switch in switch_list]
						self.net.add_nodes_from(switches)
						links_list = get_link(self.topology_api_app, None)
						links = [(link.src.dpid, link.dst.dpid, {
						          'port': link.src.port_no}) for link in links_list]
						self.net.add_edges_from(links)
						links = [(link.dst.dpid, link.src.dpid, {
						          'port': link.dst.port_no}) for link in links_list]
						self.net.add_edges_from(links)
						
						#Update switches's list    
						print('Switches in the net: %s\n'% switches)

						#Decremented every time a switch wakes up
						self.SWITCHES_DISCOVERED = self.SWITCHES_DISCOVERED - 1

						pid = self.ORIGINAL_SWITCHES[i]

						self.ACTIVE_SWITCHES.remove(pid)

						for row in self.topo_matrix:
							for column in row:

								#If we have to recalculate the path
								if any (element == pid for element in column):

									#If we are in the row or column of the switch that leaves
									if column[0] == pid or column[-1] == pid:

										#Delete flows towards switch that leaves
										if column[-1] == pid and column[0] != pid:

											s2 = self.topo_matrix[self.topo_matrix.index(row)][row.index(column)][1]

											for ip in self.topology:
												if self.topology[ip][0] == pid:
													ip_dst = ip

											datapath = get_datapath(self, column[0])

											match = datapath.ofproto_parser.OFPMatch(eth_type = 0x0800, ipv4_dst = ip_dst)

											actions = []

											self.modify_flow(datapath, match, actions)
											print('Modify flow in switch s%d with match=%s with dropping'%(datapath.id, ip_dst))

										self.topo_matrix[self.topo_matrix.index(row)][row.index(column)] = []


									#If the switch that leaves was in the middle of the path
									else:	

										#If there exists a path
										try:
											path = nx.shortest_path(self.net, column[0], column[-1])

											#Save the index of the column
											j = row.index(column)

											#Update topo_matrix
											self.topo_matrix[self.topo_matrix.index(row)][row.index(column)] = path							
											
											s2 = self.topo_matrix[self.topo_matrix.index(row)][j][1]

											for ip in self.topology:
												if self.topology[ip][0] == column[-1]:
													ip_dst = ip

											for link in self.links:
												if link[0] == column[0] and link[1] == s2:
													out_port = link[2]['port']					

											datapath = get_datapath(self, column[0])

											match = datapath.ofproto_parser.OFPMatch( eth_type = 0x0800, ipv4_dst = ip_dst)

											actions = [datapath.ofproto_parser.OFPActionOutput(out_port, datapath.ofproto.OFPCML_NO_BUFFER)]

											#Modify flow
											self.modify_flow( datapath , match, actions)
											print('Modify flow in switch s%d with match=%s output=%s'%(datapath.id, ip_dst, out_port))


										#If the two switches are inable to communicate
										except nx.NetworkXNoPath:

											for ip in self.topology:
												if self.topology[ip][0] == column[-1]:
													ip_dst = ip

											datapath = get_datapath(self, column[0])

											match = datapath.ofproto_parser.OFPMatch( eth_type = 0x0800, ipv4_dst = ip_dst)

											actions = []

											self.modify_flow(datapath, match, actions)
											print('Modify flow in switch s%d with match=%s with dropping'%(datapath.id, ip_dst))


											#Update topo_matrix
											self.topo_matrix[self.topo_matrix.index(row)][row.index(column)] = []

						print("\nTopology Matrix")
						print(self.topo_matrix)
						print('\n\n')

			print ('\n')

			#Set switches's status to down
			i = 0
			for switch in self.ORIGINAL_SWITCHES:

				try:
					self._request_stats(get_datapath(self, switch))

				#Impossible to recover the datapath of the switch
				except:
					pass

				self.switch_up[i] = 0
				i = i + 1 

# -----------------------------------------------------------------------------

"""
app_manager.require_app('ryu.app.ws_topology')
app_manager.require_app('ryu.app.ofctl_rest')
app_manager.require_app('ryu.app.gui_topology.gui_topology')	
"""
