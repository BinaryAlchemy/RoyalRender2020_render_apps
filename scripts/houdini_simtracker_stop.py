
import socket
import argparse
parser = argparse.ArgumentParser()
parser.add_argument("-slicerClient")
parser.add_argument("-slicerPort", type=int)
parser.add_argument("-parentRRJob")
args = parser.parse_args()
tracker_port=int(args.slicerPort)
tracker_host=args.slicerClient
parentRRJob=args.parentRRJob

if tracker_port is None:
    tracker_port=8000
    
if tracker_host is None:
    if tracker_host is None:
        print("simTracker_stop: Error: slicerClient nor parentRRJob defined")
        exit(1)
    print("simTracker_stop: Error: getting slicerClient via parent rrJob is not implemented yet")
    exit(2)
    


print("Connecting to {}:{}".format(tracker_host, tracker_port))
# Connect to the tracker.
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.connect((tracker_host, tracker_port))

# Send the quit message.
msg = "quit"
msg_len = struct.pack("!L", len(msg))
msg = msg_len + msg
print("simTracker_stop: Sending quit...")
s.send(msg)

# Read the ack from tracker and send back an empty message to indicate success.
s.recv(1)
s.send('')

s.close()
print("simTracker_stop: Done")