from curses import raw
from dataclasses import dataclass
from bluepy import btle
import struct, os, queue 
import concurrent.futures
from crccheck.crc import Crc8
from datetime import datetime
from time import sleep, time
from bluepy.btle import BTLEDisconnectError, Scanner, DefaultDelegate, Peripheral

import laptop_client_copy

BLE_SERVICE_UUID = "0000dfb0-0000-1000-8000-00805f9b34fb"
BLE_CHARACTERISTIC_UUID = "0000dfb1-0000-1000-8000-00805f9b34fb"
WINDOW_SIZE = 10
TIMEOUT = 0.5 # to be defined
START = 0
PLAYER_NUMBER = 1


packet_queue = queue.Queue()
packet_type = ''
x_acceleration = 0
y_acceleration = 0
z_acceleration  = 0
row = 0
yaw= 0
hit = 0
shoot = 0
gun_buffer = [None] * WINDOW_SIZE
vest_buffer = [None] * WINDOW_SIZE

current_time = 0
previous_time = 0


#temp
BEETLE_1 = 'D0:39:72:BF:C3:A8'
BEETLE_2 = 'D0:39:72:BF:C1:C6'
BEETLE_3 = 'D0:39:72:BF:C8:9B'

# 'D0:39:72:BF:C3:A8' - glove (red)
# BEETLE_2 = 'D0:39:72:BF:CA:84' # glove

# PLAYER 2 BEETLES
# BEETLE_1 = # p2 wrist
# BEETLE_2 = 'D0:39:72:BF:C8:F1'    # p1 vest
# BEETLE_3 = 'D0:39:72:BF:CD:0C' # p1 gun

# PLAYER 1 BEETLES
# BEETLE_1 = # p1 wrist
# BEETLE_2 = 'D0:39:72:BF:C8:9B' # p1 vest
# BEETLE_3 = 'D0:39:72:BF:C1:C6' # p1 gun

ALL_BEETLE = [BEETLE_2]
# ALL_BEETLE = [BEETLE_1, BEETLE_2, BEETLE_3]

#handshake status
BEETLE_HANDSHAKE_STATUS = {
    BEETLE_1 : False,
    BEETLE_2 : False,
    BEETLE_3 : False
}

send_IR_NAK_flag = {
    BEETLE_1 : False,
    BEETLE_2 : False,
    BEETLE_3 : False
}

send_IR_ACK_flag = {
    BEETLE_1 : False,
    BEETLE_2 : False,
    BEETLE_3 : False
}
send_HANDSHAKE_ACK_flag = {
    BEETLE_1 : False,
    BEETLE_2 : False,
    BEETLE_3 : False
}


#reset status
BEETLE_RESET_STATUS = {
    BEETLE_1 : False,
    BEETLE_2 : False,
    BEETLE_3 : False
}

seq_num = {
    BEETLE_1 : 0,
    BEETLE_2 : 0,
    BEETLE_3 : 0
}

sequence_number = {
    BEETLE_1 : 0,
    BEETLE_2 : 0,
    BEETLE_3 : 0
}

NUM_DROP_PACKET = {
    BEETLE_1 : 0,
    BEETLE_2 : 0,
    BEETLE_3 : 0
}
NUM_GOOD_PACKET = {
    BEETLE_1 : 0,
    BEETLE_2 : 0,
    BEETLE_3 : 0
}
NUM_FRAG_PACKET = {
    BEETLE_1 : 0,
    BEETLE_2 : 0,
    BEETLE_3 : 0
}


#Notification Class definition
class NotificationDelegate(DefaultDelegate):
    #initialise defualtdelegate for each device id, create message queue for that device
    def __init__(self,mac_address):
        DefaultDelegate.__init__(self)
        self.mac_address = mac_address
        self.buffer = b''
        self.sequence = 0   #for IR
        send_HANDSHAKE_ACK_flag[self.mac_address] = False
        send_IR_ACK_flag[self.mac_address] = False
        send_IR_NAK_flag[self.mac_address] = False

    #handleNotification: This function handles notifications
    ##check if handshake is completed
    ##completed_handshake, incoming_data, adding data to fragmented data buffer, check for fragmentation
    def handleNotification(self, cHandle, raw_packet_data):
        # print("in handleNotification", self.mac_address)
        #This handles the packet fragmentation
        self.buffer += raw_packet_data
        if(len(self.buffer) < 20):
            NUM_FRAG_PACKET[self.mac_address]+=1
            # print("data fragmented")
            # self.buffer = b''
        
        else:
            #there is  a full packet
            #send the data packet to unpack data 
            #shift buffer data down by 20 bytes 
            self.handle_packet_data(raw_packet_data[0:20])
            self.buffer = self.buffer[20:]

    #handle_packet_data: This function identifies either packet type to handle or drop corrupted data
    def handle_packet_data(self, raw_packet_data):
        #check validity by crc
        # print("in handle_packet_data")
        #password: yscd100Plus3/1
        # print("before:" ,len(raw_packet_data))
        if len(raw_packet_data)< 20:
            return

        if not self.CRCcheck(raw_packet_data):
            NUM_DROP_PACKET[self.mac_address] +=1
            return

        # #unpack for handling 
        # packetFormat = 'c' + 19*'B'
        # unpacked_packet = struct.unpack(packetFormat, raw_packet_data[0:20])
        
        # #convert packet type from byte to char
        # my_list = list(unpacked_packet)
        
        # my_list[0] = my_list[0].decode("utf-8")
        # # print(my_list)
        # unpacked_packet = tuple(my_list)
        # print(raw_packet_data[0])
        try:
            #bluno handshake ACK
            if(raw_packet_data[0] == 65):
                BEETLE_HANDSHAKE_STATUS[self.mac_address] = True
                send_HANDSHAKE_ACK_flag[self.mac_address] = True
                print(BEETLE_HANDSHAKE_STATUS[self.mac_address] )
                        
            #handshake completed
            elif BEETLE_HANDSHAKE_STATUS[self.mac_address]:
                #identify packet type and handle respectively
                #handle wrist data, W = 87
                # print("AM HERE")
                if(raw_packet_data[0]== 87):
                    self.unpack_wrist_data(raw_packet_data)
                #handle IR_data: gun data, G = 71 || vest data, V = 86
                elif(raw_packet_data[0]== 71 or raw_packet_data[0]== 86):
                    self.unpack_IR_data(raw_packet_data)
                #is corrupted and just dropped
                else: 
                    NUM_DROP_PACKET[self.mac_address] +=1


            #reset if the 20bytes is corrutped data and dropped
            else:
                BEETLE_RESET_STATUS[self.mac_address] = True
                NUM_DROP_PACKET[self.mac_address] +=1
        except Exception as e: 
            print("handle_packet_data exception: ", e)




    #CRCcheck: This function calculates and compare checksum to ensure packet is not corrupted
    def CRCcheck(self, raw_packet_data):
        checksum = Crc8.calc(raw_packet_data[0:19])
        # print("inside:" ,len(raw_packet_data))
        if checksum == raw_packet_data[19]:
            return True
        return False

    def unpack_wrist_data(self, raw_packet_data):
        try: 
            # print(len(raw_packet_data))
            packetFormat = '!c'+ (6)*'h'+7*'b'
            
            unpacked_packet = struct.unpack(packetFormat, raw_packet_data)
            my_list = list(unpacked_packet)
            my_list[0] = my_list[0].decode("utf-8")
            unpacked_packet = tuple(my_list)
            # print("unpacked_packet: ", unpacked_packet[0:7])
            lp_client.getData(unpacked_packet[0:7])
            NUM_GOOD_PACKET[self.mac_address] += 1
        except Exception as e:
            print("wrist.exception: ", e)
    
    def unpack_IR_data(self, raw_packet_data):
        try: 
            packetFormat = '!c'+ 19*'B'
            
            unpacked_packet = struct.unpack(packetFormat, raw_packet_data)
            my_list = list(unpacked_packet)
            my_list[0] = my_list[0].decode("utf-8")
            unpacked_packet = tuple(my_list)
            # print("unpacked_packet: ", unpacked_packet)

            #drop duplicate packets
            if(unpacked_packet[1]== self.sequence):
                NUM_DROP_PACKET[self.mac_address] += 1
                return
            
            self.sequence = unpacked_packet[1]
            send_IR_ACK_flag[self.mac_address] = True
            sequence_number[self.mac_address] = self.sequence
            print("unpacked_packet: ", unpacked_packet)
            send_data = (unpacked_packet[0],unpacked_packet[2])
            # print(send_data)
            lp_client.getData(send_data)
            NUM_GOOD_PACKET[self.mac_address] += 1

        except Exception as e:
            print("IR.exception: ",self.mac_address, " error: ", e)
            #  if(packet_type == 71):
            #         num_packet_received[self.mac_address] = num_packet_received[self.mac_address] + 1
            #         seq_num[self.mac_address] = raw_packet_data[1]
            #         pad = (0,)
            #         padding = pad *18
            #         packetFormat = 'c'+ (19)*'B'
            #         # print("seq_num: ", seq_num[self.mac_address], "stored_seq:", sequence_number[self.mac_address])
            #         try: 
            #             if(sequence_number[self.mac_address]==seq_num[self.mac_address]):
            #                 #send ACK
            #                 send_ACK_flag[self.mac_address] = True
            #                 gun_buffer[seq_num[self.mac_address]] = None
            #                 #send data to ext
            #                 ir_emitter = raw_packet_data[2]

            #                 sequence_number[self.mac_address] = (sequence_number[self.mac_address] + 1) % 10
            #                 #To communicate with external Comms to for the arrangement of packet
            #                 dataPkt = [packet_type, ir_emitter]            
            #                 lp_client.getData(unpacked_packet)
            #                 # print( "stored_seq:", sequence_number[self.mac_address])
                            

            #                 #empty gun_buffer, update seq num
            #                 while(gun_buffer[sequence_number[self.mac_address]]!=None):
            #                     #send ACK
            #                     send_ACK_flag[self.mac_address] = True
            #                     #send data to ext
            #                     ir_emitter = gun_buffer[sequence_number[self.mac_address]]
            #                     gun_buffer[sequence_number[self.mac_address]] = None
            #                     # print ('(Bluno' + str(self.mac_address) + ') packet_type: ' + str(packet_type) )
            #                     sequence_number[self.mac_address] = (sequence_number[self.mac_address] + 1) % 10
            #                     #To communicate with external Comms to for the arrangement of packet
            #                     dataPkt = [packet_type, ir_emitter]            
            #                     packet_queue.put(dataPkt) 
            #             else:
            #                 # print("am here", sequence_number[self.mac_address])
            #                 num_packet_fragmented[self.mac_address] = num_packet_fragmented[self.mac_address] + 1
            #                 #request for sequence again
            #                 send_NAK_flag[self.mac_address] = True;  
            #                 #store next seq values, else trash
                            
            #                 if(seq_num[self.mac_address]>sequence_number[self.mac_address]):
            #                     vest_buffer[seq_num[self.mac_address]] = raw_packet_data[2]
            #                     send_specific_ACK_flag[self.mac_address] = True
            #                 #If repeated seq, done nothing n trash
            #                 else:
            #                     num_packet_dropped[self.mac_address] = num_packet_dropped[self.mac_address] + 1


class beetleThread():
    def __init__(self,beetle_peripheral_object):
        self.beetle_periobj = beetle_peripheral_object
        self.serial_service = self.beetle_periobj.getServiceByUUID(BLE_SERVICE_UUID)
        self.serial_characteristic = self.serial_service.getCharacteristics()[0]
        self.establish_handshake()

    #establish_handshake: This function establish handshake w bluno
    def establish_handshake(self):
        timeout_counter = 0
        try:
            while BEETLE_HANDSHAKE_STATUS[self.beetle_periobj.addr]==False:
                
                timeout_counter+=1
                pad = (0,)
                padding = pad *19
                packetFormat = 'c'+ (19)*'B'
                # print(self)
                self.serial_characteristic.write(struct.pack(packetFormat, bytes('H', 'utf-8'), *padding),withResponse=False)
                print("H sent for: " , self.beetle_periobj.addr) 

                #no response after 5 H-pkts, reset
                if(timeout_counter%5==0):
                    print("handshake timeout")
                    timeout_counter = 0
                    self.reset()

                
                if self.beetle_periobj.waitForNotifications(3.0):
                    #return handshake ack
                    pad = (0,)
                    padding = pad *19
                    packetFormat = 'c'+ (19)*'B'
                    if(send_HANDSHAKE_ACK_flag[self.beetle_periobj.addr] == True):
                        self.serial_characteristic.write(struct.pack(packetFormat, bytes('A', 'utf-8'), *padding),withResponse=False)
                        # print('A for handshake sent : ', self.beetle_periobj.addr)
                        # send_HANDSHAKE_ACK_flag[self.beetle_periobj.addr] = False                
            return True

        except BTLEDisconnectError:
            print("in handshake_exception")
            self.reconnect()
            self.establish_handshake()
           
    #reconnect: This function reconnects the bluno
    def reconnect(self):
        BEETLE_HANDSHAKE_STATUS[self.beetle_periobj.addr] = False
        try:
            #drop the beetle
            self.beetle_periobj.disconnect()
            #start new connection with beetle
            self.beetle_periobj.connect(self.beetle_periobj.addr)
            self.beetle_periobj.withDelegate(NotificationDelegate(self.beetle_periobj.addr))
            print("reconnection successful for ", self.beetle_periobj.addr)
        except Exception:
            print("in reconnect.exception")
            self.reconnect()

    #reset: This funtion reset the bluno
    def reset(self):
        pad = (0,)
        padding = pad *19
        packetFormat = 'c'+ (19)*'B'
        self.serial_characteristic.write(struct.pack(packetFormat, bytes('R', 'utf-8'), *padding),withResponse=False)
        BEETLE_RESET_STATUS[self.beetle_periobj.addr] = False
        self.reconnect()
        

    
    def run(self):
        try:
            while True:
                #break and reset
                current_time = START
                if BEETLE_RESET_STATUS[self.beetle_periobj.addr]:
                    break

                #keep waiting for response
                if self.beetle_periobj.waitForNotifications(2.0):
                    pad = (0,)
                    padding = pad *18
                    packetFormat = 'c'+ (19)*'B'
                    # if(send_ACK_flag[self.beetle_periobj.addr] ==True):
                    #     self.serial_characteristic.write(struct.pack(packetFormat, bytes('A', 'utf-8'), sequence_number[self.beetle_periobj.addr], *padding),withResponse=False)
                    #     send_ACK_flag[self.beetle_periobj.addr] = False
                    #     # print("sent ack")
                    if(send_IR_NAK_flag[self.beetle_periobj.addr]==True):
                        self.serial_characteristic.write(struct.pack(packetFormat, bytes('N', 'utf-8'), sequence_number[self.beetle_periobj.addr], *padding),withResponse=False)
                        send_IR_NAK_flag[self.beetle_periobj.addr] = False
                        # print("sent nak")
                    if(send_IR_ACK_flag[self.beetle_periobj.addr]==True):
                        self.serial_characteristic.write(struct.pack(packetFormat, bytes('A', 'utf-8'), sequence_number[self.beetle_periobj.addr], *padding),withResponse=False)
                        send_IR_ACK_flag[self.beetle_periobj.addr] = False
                        # print("sent specific ack") 
                    
                
                # print("current: ", current_time)
                # if((time()-current_time)>=5):
                #     time_elapsed = time()-START
                #     current_time = time()
                    # print("packet_recevied: ", num_packet_dropped[self.beetle_periobj.addr])
                    # print("packet_dropped: ", num_packet_dropped[self.beetle_periobj.addr])
                    # print("packet_fragmented: ", num_packet_dropped[self.beetle_periobj.addr])
                    # print("rate: ", (num_packet_received[self.beetle_periobj.addr]*20)/time_elapsed)  
            self.reconnect()
            self.establish_handshake()
            self.run()
        
        except Exception as e:
            print("run.exception")
            print("issue ", e, "for: ", self.beetle_periobj.addr)
            self.reconnect()
            self.establish_handshake()
            self.run()


#main function
if __name__=='__main__':
    # new_queue = queue.Queue()
    lp_client = laptop_client_copy.LaptopClient()
    lp_client.start()
    beetles = []
    # laptopClient = laptop_client.LaptopClient
    #declare relay
    # # make the send to u96 a new thread with queue
    # while True:
    #     while q.notempty():
    #         daat = q.pop()
    for beetle_mac in ALL_BEETLE:
        beetle_periobj = Peripheral(beetle_mac)
        beetle_periobj.withDelegate(NotificationDelegate(beetle_mac))
        beetle = beetleThread(beetle_periobj)
        beetles.append(beetle)
    with concurrent.futures.ThreadPoolExecutor() as executor:
        threads = []
        for beetle in beetles:
            thread = executor.submit(beetle.run)
            threads.append(thread)
            # beetle_inst = Peripheral(beetle_mac)
            # beetle_inst.withDelegate(NotificationDelegate(beetle_mac))
            # executor.submit(beetleThread(beetle_inst).reset(), beetle_inst)
            # executor.submit(bluno_thread, connected_dev[1], 1)
            # executor.submit(bluno_thread, connected_dev[2], 2)

    


    # for mac in ALL_BEETLE:
    #     pid = os.fork()

    #     if pid>0:
    #         print("spawning child")
    #     else:
    #         #connect to mac
    #         try:
    #             beetle = Peripheral(mac)
    #         except:
    #             #retry connection
    #             sleep(2.0)
    #             beetle = Peripheral(mac)
    #         beetle.withDelegate(NotificationDelegate(mac))
    #         beetleThread(beetle).run()
               
 