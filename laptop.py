from multiprocessing import current_process
from bluepy import btle
import struct, os, queue, sys 
import concurrent.futures
from crccheck.crc import Crc8
from datetime import datetime
from time import sleep, time
from bluepy.btle import BTLEDisconnectError, Scanner, DefaultDelegate, Peripheral
import threading
import zmq
import json

BLE_SERVICE_UUID = "0000dfb0-0000-1000-8000-00805f9b34fb"
BLE_CHARACTERISTIC_UUID = "0000dfb1-0000-1000-8000-00805f9b34fb"
WINDOW_SIZE = 10
TIMEOUT = 0.5 # to be defined
START = 0

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
BEETLE_1 = 'D0:39:72:BF:CA:84'
BEETLE_2 = 'D0:39:72:BF:C1:C6'
BEETLE_3 = 'D0:39:72:BF:C8:9B'
# #actual beetle mac address
# BEETLE_1 = 'D0:39:72:BF:C8:F1'
# BEETLE_2 = 'D0:39:72:BF:CA:84' - glove
# BEETLE_3 = 'D0:39:72:BF:CD:0C' 
# 'D0:39:72:BF:C3:A8'
# 'D0:39:72:BF:C8:9B' - vest
# 'D0:39:72:BF:C1:C6' - gun


ALL_BEETLE = [BEETLE_1,BEETLE_2, BEETLE_3]

#handshake status
BEETLE_HANDSHAKE_STATUS = {
    BEETLE_1 : False,
    BEETLE_2 : False,
    BEETLE_3 : False
}

send_NAK_flag = {
    BEETLE_1 : False,
    BEETLE_2 : False,
    BEETLE_3 : False
}
send_ACK_flag = {
    BEETLE_1 : False,
    BEETLE_2 : False,
    BEETLE_3 : False
}
send_specific_ACK_flag = {
    BEETLE_1 : False,
    BEETLE_2 : False,
    BEETLE_3 : False
}
send_handshake_ACK_flag = {
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

num_packet_dropped = {
    BEETLE_1 : 0,
    BEETLE_2 : 0,
    BEETLE_3 : 0
}
num_packet_received = {
    BEETLE_1 : 0,
    BEETLE_2 : 0,
    BEETLE_3 : 0
}
num_packet_fragmented = {
    BEETLE_1 : 0,
    BEETLE_2 : 0,
    BEETLE_3 : 0
}

first_connection = 1

#Notification Class definition
class NotificationDelegate(DefaultDelegate):
    #initialise defualtdelegate for each device id, create message queue for that device
    def __init__(self,mac_address):
        DefaultDelegate.__init__(self)
        self.mac_address = mac_address
        self.fragmentation_data = b''

    #handleNotification: This function handles notifications
    ##check if handshake is completed
    ##completed_handshake, incoming_data, adding data to fragmented data buffer, check for fragmentation
    def handleNotification(self, cHandle, data):
        # print("in handleNotification", self.mac_address)
            
        self.fragmentation_data += data
        if(len(self.fragmentation_data)>=20):
            raw_packet_data = self.fragmentation_data[0:20]
            self.handleRawPacket(raw_packet_data)

        
    #handleFragmentationPacket: This function handles the packet fragmentation
    def handleRawPacket(self, raw_packet_data):
        # print("in handleRawPacket_ func")
        try:  
            if(len(raw_packet_data)>=20): 
                #there is  a full packet
                #send the data packet to unpack data 
                #shift fragmentation data down by 20 bytes 
                self.unpack_data_packet(raw_packet_data[0:20])
                self.fragmentation_data = self.fragmentation_data[20:]
        except Exception:
            #In event of any error, return an empty byte array to the buffer
            print("data fragmented")
            self.fragmentation_data = b''


    #unpack_data_packet: This function unpacks data from bluno, to put into queueu to ExtComm  
    def unpack_data_packet(self, raw_packet_data):
        # print("in unpack_data_packet_func")

        global packet_type
        global x_acceleration 
        global y_acceleration    
        global z_acceleration 
        global row   
        global pitch
        global yaw
        global packet_queue 
        global hit
        global shoot
        global send_ACK_flag
        global send_NAK_flag
        global seq_num
        global send_specific_ACK_flag
        global send_handshake_ACK_flag
        global sequence_number

        
                
        #handshke completed
        if(BEETLE_HANDSHAKE_STATUS[self.mac_address]):
            packet_type = raw_packet_data[0]
            packetFormat = 'c'+ (19)*'B'
            print("data: ", struct.unpack(packetFormat, raw_packet_data[0:20]))
            #Compute the CRC of the packet excluding the start, CRC-8bit and end byte
            # print("packet_type =", raw_packet_data[0])
            checksum = Crc8.calc(raw_packet_data[0:19])
            # print("crc: ", raw_packet_data[19], "checksum: ", checksum)
            if(checksum == raw_packet_data[19]):
            
                
                #for wrist
                
                if(packet_type == 87):
                    num_packet_received[self.mac_address] = num_packet_received[self.mac_address] + 1
                    try: 
                        
                        #little endiean , short inT
                        x_acceleration = raw_packet_data[1:3]
                        y_acceleration = raw_packet_data[3:5]
                        z_acceleration = raw_packet_data[5:7]
                        row = raw_packet_data[7:9]
                        pitch = raw_packet_data[9:11]
                        yaw = raw_packet_data[11:13]
                        # send_ACK_flag[self.mac_address] = True
                        # print ('(Bluno' + str(self.mac_address) + ') packet_type: ' + str(packet_type) )
                        #To communicate with external Comms to for the arrangement of packet
                        dataPkt = [packet_type, x_acceleration, y_acceleration, z_acceleration, row, pitch, yaw]
                        # print("wrist: ", dataPkt)
                        packet_queue.put(dataPkt)
                    except Exception:
                        print("wrist.exception")
                        
                # #for gun data
                if(packet_type == 71):
                    num_packet_received[self.mac_address] = num_packet_received[self.mac_address] + 1
                    seq_num[self.mac_address] = raw_packet_data[1]
                    pad = (0,)
                    padding = pad *18
                    packetFormat = 'c'+ (19)*'B'
                    # print("seq_num: ", seq_num[self.mac_address], "stored_seq:", sequence_number[self.mac_address])
                    try: 
                        if(sequence_number[self.mac_address]==seq_num[self.mac_address]):
                            #send ACK
                            send_ACK_flag[self.mac_address] = True
                            gun_buffer[seq_num[self.mac_address]] = None
                            #send data to ext
                            ir_emitter = raw_packet_data[2]

                            # print ('(Bluno' + str(self.mac_address) + ') packet_type: ' + str(packet_type) )
                            sequence_number[self.mac_address] = (sequence_number[self.mac_address] + 1) % 10
                            #To communicate with external Comms to for the arrangement of packet
                            dataPkt = [packet_type, ir_emitter]            
                            packet_queue.put(dataPkt) 
                            # print( "stored_seq:", sequence_number[self.mac_address])
                            

                            #empty gun_buffer, update seq num
                            while(gun_buffer[sequence_number[self.mac_address]]!=None):
                                #send ACK
                                send_ACK_flag[self.mac_address] = True
                                #send data to ext
                                ir_emitter = gun_buffer[sequence_number[self.mac_address]]
                                gun_buffer[sequence_number[self.mac_address]] = None
                                # print ('(Bluno' + str(self.mac_address) + ') packet_type: ' + str(packet_type) )
                                sequence_number[self.mac_address] = (sequence_number[self.mac_address] + 1) % 10
                                #To communicate with external Comms to for the arrangement of packet
                                dataPkt = [packet_type, ir_emitter]            
                                packet_queue.put(dataPkt) 
                        else:
                            # print("am here", sequence_number[self.mac_address])
                            num_packet_fragmented[self.mac_address] = num_packet_fragmented[self.mac_address] + 1
                            #request for sequence again
                            send_NAK_flag[self.mac_address] = True;  
                            #store next seq values, else trash
                            
                            if(seq_num[self.mac_address]>sequence_number[self.mac_address]):
                                vest_buffer[seq_num[self.mac_address]] = raw_packet_data[2]
                                send_specific_ACK_flag[self.mac_address] = True
                            #If repeated seq, done nothing n trash
                            else:
                                num_packet_dropped[self.mac_address] = num_packet_dropped[self.mac_address] + 1
                    except Exception as e:
                        print("gun.exception, error: ", e)
                #for vest data
                try:
                    if(packet_type == 86):
                        num_packet_received[self.mac_address] = num_packet_received[self.mac_address] + 1
                        seq_num[self.mac_address] = raw_packet_data[1]
                        pad = (0,)
                        padding = pad *18
                        packetFormat = 'c'+ (19)*'B'
                        # print("seq_num: ", seq_num[self.mac_address], "stored_seq:", sequence_number[self.mac_address])
                        if(sequence_number[self.mac_address]==seq_num[self.mac_address]):
                            #send ACK
                            vest_buffer[seq_num[self.mac_address]] = None
                            #send data to ext
                            ir_receiver = raw_packet_data[2]

                            # print ('(Bluno' + str(self.mac_address) + ') packet_type: ' + str(packet_type) )
                            sequence_number[self.mac_address] = (sequence_number[self.mac_address] + 1) % 10
                            #To communicate with external Comms to for the arrangement of packet
                            dataPkt = [packet_type, ir_receiver]            
                            packet_queue.put(dataPkt) 
                            # print( "stored_seq:", sequence_number[self.mac_address])
                            send_ACK_flag[self.mac_address] = True

                            #empty vest_buffer, update seq num
                            while(vest_buffer[sequence_number[self.mac_address]]!=None):
                                #send ACK
                                send_ACK_flag[self.mac_address] = True
                                #send data to ext
                                ir_receiver = vest_buffer[sequence_number[self.mac_address]]
                                vest_buffer[sequence_number[self.mac_address]] = None
                                # print ('(Bluno' + str(self.mac_address) + ') packet_type: ' + str(packet_type) )
                                sequence_number[self.mac_address] = (sequence_number[self.mac_address] + 1) % 10
                                #To communicate with external Comms to for the arrangement of packet
                                dataPkt = [packet_type, ir_receiver]            
                                packet_queue.put(dataPkt) 
                        else:
                            # print("am here", sequence_number[self.mac_address])
                            num_packet_fragmented[self.mac_address] = num_packet_fragmented[self.mac_address] + 1
                            #request for sequence again
                            send_NAK_flag[self.mac_address] = True;  
                            #store next seq values, else trash
                            if(seq_num[self.mac_address]>sequence_number[self.mac_address]):
                                vest_buffer[seq_num[self.mac_address]] = raw_packet_data[2]
                                send_specific_ACK_flag[self.mac_address] = True
                                
                            #If repeated seq, done nothing n trash
                            else:
                                #drop packet for assesement:
                                num_packet_dropped[self.mac_address] = num_packet_dropped[self.mac_address] + 1
                except Exception as e:
                    print("Vest.exception, error: ",e)
            else:
                print('(Bluno' + str(self.mac_address) + ') CRC failed')
                num_packet_dropped[self.mac_address] = num_packet_dropped[self.mac_address] + 1
        elif(BEETLE_HANDSHAKE_STATUS[self.mac_address]==False and raw_packet_data[0] == 65 ):
            #ack from handshake
            # print("changing handshake status")
            send_handshake_ACK_flag[self.mac_address] = True
            BEETLE_HANDSHAKE_STATUS[self.mac_address] = True
            # BEETLE_HANDSHAKE_STATUS[self.mac_address] = True
        
        # else:
        #     print("changing reset status")
        #     BEETLE_RESET_STATUS[self.mac_address] = True


class beetleThread():
    def __init__(self,beetle_peripheral_object):
        self.beetle_periobj = beetle_peripheral_object
        self.serial_service = self.beetle_periobj.getServiceByUUID(BLE_SERVICE_UUID)
        self.serial_characteristic = self.serial_service.getCharacteristics()[0]
        self.establish_handshake()


    def establish_handshake(self):
        timeout_counter = 0
        global send_handshake_ACK_flag
        try:
            while BEETLE_HANDSHAKE_STATUS[self.beetle_periobj.addr]==False:
                
                timeout_counter+=1
                pad = (0,)
                padding = pad *19
                packetFormat = 'c'+ (19)*'B'
                # print(self)
                self.serial_characteristic.write(struct.pack(packetFormat, bytes('H', 'utf-8'), *padding),withResponse=False)
                print("H sent for: " , self.beetle_periobj.addr) 
                if(timeout_counter%15==0 and not first_connection):
                    print("handshake timeout")
                    self.reset()

                
                if self.beetle_periobj.waitForNotifications(5.0):
                    #return handshake ack
                    pad = (0,)
                    padding = pad *19
                    packetFormat = 'c'+ (19)*'B'
                    if(send_handshake_ACK_flag[self.beetle_periobj.addr] == True):
                        self.serial_characteristic.write(struct.pack(packetFormat, bytes('A', 'utf-8'), *padding),withResponse=False)
                        # print('A for handshake sent : ', self.beetle_periobj.addr)
                        send_handshake_ACK_flag[self.beetle_periobj.addr] = False
                        BEETLE_HANDSHAKE_STATUS[self.beetle_periobj.addr] = True
                first_connection = 0
                
            return True

        except BTLEDisconnectError:
            print("in handshake_exception")
            self.reconnect()
           

    def reconnect(self):
        try:
            self.beetle_periobj.disconnect()
            sleep(1.0)
            self.beetle_periobj.connect(self.beetle_periobj.addr)
            self.beetle_periobj.withDelegate(NotificationDelegate(self.beetle_periobj.addr))
            print("reconnection successful for ", self.beetle_periobj.addr)
        except Exception:
            print("in reconnect.exception")
            self.reconnect()

    def reset(self):
        global BEETLE_HANDSHAKE_STATUS
        global BEETLE_RESET_STATUS
        global send_handshake_ACK_flag
        # print('in reset')
        pad = (0,)
        padding = pad *19
        packetFormat = 'c'+ (19)*'B'
        self.serial_characteristic.write(struct.pack(packetFormat, bytes('R', 'utf-8'), *padding),withResponse=False)
        BEETLE_HANDSHAKE_STATUS[self.beetle_periobj.addr] = False
        BEETLE_RESET_STATUS[self.beetle_periobj.addr] = False
        send_handshake_ACK_flag[self.beetle_periobj.addr] = False
        self.reconnect()
        

    
    def run(self):
        global send_ACK_flag
        global send_NAK_flag
        global send_specific_ACK_flag
        global seq_num
        global sequence_number
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
                    if(send_ACK_flag[self.beetle_periobj.addr] ==True):
                        self.serial_characteristic.write(struct.pack(packetFormat, bytes('A', 'utf-8'), sequence_number[self.beetle_periobj.addr], *padding),withResponse=False)
                        send_ACK_flag[self.beetle_periobj.addr] = False
                        # print("sent ack")
                    if(send_NAK_flag[self.beetle_periobj.addr]==True):
                        self.serial_characteristic.write(struct.pack(packetFormat, bytes('N', 'utf-8'), sequence_number[self.beetle_periobj.addr], *padding),withResponse=False)
                        send_NAK_flag[self.beetle_periobj.addr] = False
                        # print("sent nak")
                    if(send_specific_ACK_flag[self.beetle_periobj.addr]==True):
                        self.serial_characteristic.write(struct.pack(packetFormat, bytes('A', 'utf-8'), seq_num[self.beetle_periobj.addr], *padding),withResponse=False)
                        send_specific_ACK_flag[self.beetle_periobj.addr] = False
                        # print("sent specific ack") 
                    
                
                # print("current: ", current_time)
                # if((time()-current_time)>=5):
                #     time_elapsed = time()-START
                #     current_time = time()
                    # print("packet_recevied: ", num_packet_dropped[self.beetle_periobj.addr])
                    # print("packet_dropped: ", num_packet_dropped[self.beetle_periobj.addr])
                    # print("packet_fragmented: ", num_packet_dropped[self.beetle_periobj.addr])
                    # print("rate: ", (num_packet_received[self.beetle_periobj.addr]*20)/time_elapsed)
                
            self.reset()
            self.establish_handshake()
            self.run()
        
        except Exception as e:
            print("run.exception")
            print("issue ", e, "for: ", self.beetle_periobj.addr)
            self.reconnect()
            self.reset()
            self.establish_handshake()
            self.run()

class LaptopClient(threading.Thread):
    def __init__(self):
        super(LaptopClient, self).__init__()
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.REQ)

    def init_socket_connection(self):
        #  Socket to talk to server
        print("Connecting to Ultra96 server…")
        self.socket.connect("tcp://localhost:5550")

    def send_message(self):
        while True:
            new_action = [123.00,234.0,345.0]#assign the data you get from the bettle
            new_action_json = json.dumps(new_action)
            new_action_json = new_action_json.encode("utf8")
            self.socket.send(new_action_json)
            message = self.socket.recv()
            message = message.decode("utf8")
            print(message)

#main function
if __name__=='__main__':
    lp_client = LaptopClient()
    lp_client.init_socket_connection()
    lp_client.send_message()
    

    beetles = []
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
               
 