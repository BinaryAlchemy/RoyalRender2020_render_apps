# Royal Render Render script for Keep Scene Open 
# Author: Royal Render
# Version %rrVersion%

try:
    import socketserver
except:
    import SocketServer as socketserver
import struct
import datetime
import sys
import time
import logging

StructureID_rrCommands  =0x0B04
StructureID_RRN_TCP_HeaderData_v5 = 0x0D05
Size_RRCommands = 2032
Size_RRN_TCP_HeaderData_v5 = 206
rrnData_commands = 7
log_command="print(' \\\'"
log_command_end="')"
commandTimeout=180
PRINT_DEBUG= False
LOGGER_NAME = "rrKSO_TCP"
USE_DEFAULT_PRINT = True
LOGGER_WAS_SETUP= False
LOGGER_FILENAME=""
LOGGER_ADD_TIME = True




################ Logger Functions ################

def flushLog():
    global USE_DEFAULT_PRINT
    if USE_DEFAULT_PRINT:
        sys.stdout.flush()
        sys.stderr.flush()
    else:
        logger = logging.getLogger(LOGGER_NAME)
        for handler in logger.handlers:
            handler.flush()


def closeHandlers(logger):
    for handler in logger.handlers:
        handler.flush()
        handler.close()


def setLogger(log_level=20, log_name=LOGGER_NAME, log_file=None, log_to_stream=False):
    logger = logging.getLogger(log_name)
    logger.setLevel(log_level)
    if LOGGER_ADD_TIME:
        log_format = logging.Formatter("' %(asctime)s %(name)s %(levelname)5s: %(message)s", "%H:%M:%S")
    else: 
        log_format = logging.Formatter("' %(name)s %(levelname)5s: %(message)s")

    
    OUTFILE_LEVEL_NUM = logging.INFO + 2
    SET_LEVEL_NUM = logging.INFO + 1

    logging.addLevelName(SET_LEVEL_NUM, "SET")
    logging.addLevelName(OUTFILE_LEVEL_NUM, "FILE")

    def logSet(self, message, *args, **kws):
        if self.isEnabledFor(SET_LEVEL_NUM):
            self._log(SET_LEVEL_NUM, message, args, **kws)

    def logFILE(self, message, *args, **kws):
        if self.isEnabledFor(OUTFILE_LEVEL_NUM):
            self._log(OUTFILE_LEVEL_NUM, message, args, **kws)

    logging.Logger.set = logSet
    logging.Logger.outfile = logFILE

    handlers = logger.handlers[:]
    for handler in handlers:
        handler.close()
        logger.removeHandler(handler)
        
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(log_format)
        file_handler.setLevel(log_level)

        logger.addHandler(file_handler)

    if log_to_stream:
        str_handler = logging.StreamHandler(sys.stdout)
        str_handler.setFormatter(log_format)
        logger.addHandler(str_handler)
        
    logger.debug("Logger "+LOGGER_NAME +" was initialized." )

def rrKSO_logger_init():        
    global USE_DEFAULT_PRINT
    global PRINT_DEBUG
    LOGGER_WAS_SETUP= True
    if USE_DEFAULT_PRINT:
        setLogger(log_to_stream=True, log_level=logging.DEBUG if PRINT_DEBUG else logging.INFO)
    else:
        setLogger(log_file=LOGGER_FILENAME, log_level=logging.DEBUG if PRINT_DEBUG else logging.INFO)



def rrKSO_logger(func):
    """Wrapper for log functions, gets the "LOGGER_NAME" logger,
    makes sure to close handlers or flush the listener after message log

    :param func: function to wrap, must accept arguments "msg" and "logger"
    :return: wrapped function
    """
    logger = logging.getLogger(LOGGER_NAME)

    def wrapper(msg):
        func(msg, logger=logger)
        if USE_DEFAULT_PRINT:
            flushLog()
        else:
            closeHandlers(logger)

    return wrapper


def io_retry(func, wait_secs=0.35, num_tries=3):
    """Wrapper that re-executes given function num_tries times, waiting wait_time between tries.
    Used to avoid write error when the log file is busy, as the rrClient moves it

    :param func: function to wrap
    :param wait_secs:
    :param num_tries:
    :return: wrapped function
    """
    def wrapper(msg, logger):

        if USE_DEFAULT_PRINT:
            func(msg, logger)
            return

        try:
            func(msg, logger)
        except IOError:
            for _ in range(num_tries):
                time.sleep(wait_secs)
                try:
                    func(msg, logger)
                except IOError:
                    continue
                else:
                    break

    return wrapper


@rrKSO_logger
@io_retry
def logMessage(msg, logger=None):
    logger.info(msg)


@rrKSO_logger
@io_retry
def logMessageSET(msg, logger=None):
    logger.set(msg)


@rrKSO_logger
@io_retry
def logMessageWarn(msg, logger=None):
    logger.warning(msg)


@rrKSO_logger
@io_retry
def logMessageDebug(msg, logger=None):
    logger.debug(msg)


@rrKSO_logger
@io_retry
def logMessageFile(msg, logger=None):
    logger.outfile(msg)
    
@rrKSO_logger
@io_retry
def logMessageError(msg, logger=None):
    logger.error(msg)
   

class _RRCommands():
    StructureID=StructureID_rrCommands
    ctype=4 
    command=0
    userID=0
    paramID=0
    paramX=0
    paramY=0
    paramS=""
    paramSlength=0
    paramSType=0
    threads=0
   

    #def toBinary(self):
        #keptfree=0
        #return struct.pack("=HBBhbbQii1002sHH1000?bb",self.StructureID,self.ctype, self.command, keptfree, keptfree,keptfree,self.paramID, self.paramX, self.paramY, keptfree, keptfree, self.paramS, self.paramSlength,self.paramSType)

    def fromBinary(self, buf):
        tmp= struct.unpack("=HBBhbbQiiHH1002s1000?bb",buf)
        #= Native byte order, standard var size, no alignment
        #0     H  uInt16 
        #1,2   BB uChar  
        #3     h  Int16
        #4,5   bb Char
        #6     Q  uInt64
        #7,8   ii Int32
        #9,10  HH uInt16
        #11    s  Char[]
        #12    ?  bool[]
        #13,14 bb Char
        self.StructureID= tmp[0] 
        self.ctype= tmp[1] 
        self.command= tmp[2] 
        self.paramID= tmp[6] 
        self.paramX= tmp[7] 
        self.paramY= tmp[8]
        self.paramSlength= tmp[9]
        self.paramSType= tmp[10]
        paramsTemp=tmp[11]
        self.paramS=""   
        if (sys.version_info > (3, 0)):
            paramsTemp= paramsTemp[:(self.paramSlength*2)]
            self.paramS= paramsTemp.decode(encoding="utf_16_le", errors="strict")
            #logMessage("paramSlength: "+str(self.paramSlength))
            #logMessage("len paramS: "+str(len(self.paramS)))
            #hexStr=paramsTemp.hex()
            #logMessage("paramS: "+str(hexStr))
            #logMessage("paramS: "+str(self.paramS))
        else:
            for c in range(0, self.paramSlength):  #string is actually unicode 16bit, but for these commands a dirty ANSI conversion is fine 
                self.paramS= self.paramS+ paramsTemp[c*2]
        
    def rightStructure(self):
        return (self.StructureID== StructureID_rrCommands)



    
class _RRN_TCP_HeaderData_v5():
    StructureID= StructureID_RRN_TCP_HeaderData_v5
    dataLen=0   
    dataType=0  
    dataNrElements=0
    appType=14  

    #def toBinary(self):
        #keptfree=0
        #keptfreeS=""
        #return struct.pack("=HIIHbhB190s",self.StructureID,keptfree,self.dataLen,keptfree,self.dataType,self.dataNrElements,self.appType,keptfreeS)

    def fromBinary(self, buf):
        tmp= struct.unpack("=H??IIHbB190s",buf)
        self.StructureID= tmp[0] 
        self.dataLen= tmp[4] 
        self.dataNrElements= tmp[5] 
        self.dataType= tmp[6] 
        self.appType= tmp[7] 

    def rightStructure(self):
        return (self.StructureID== StructureID_RRN_TCP_HeaderData_v5)

rrKSONextCommand=""



class rrKSOTCPHandler(socketserver.BaseRequestHandler):
    def handle(self):
        logMessageDebug("rrKSOTCPHandler")
        headerData=_RRN_TCP_HeaderData_v5()
        headerData.fromBinary(self.request.recv(Size_RRN_TCP_HeaderData_v5))
        if ((not headerData.rightStructure()) or (headerData.dataType!=rrnData_commands) or (headerData.dataLen!=Size_RRCommands) ):
            self.server.continueLoop=False
            logMessageError("TCP header wrong! "
                   + " ID:"+ str(headerData.StructureID)+"!=" +str(StructureID_RRN_TCP_HeaderData_v5)
                   + " type:"+ str(headerData.dataType)+"!=" +str(rrnData_commands)
                   + " len:"+ str(headerData.dataLen)+"!=" +str(Size_RRCommands)
                   )
            return
        logMessageDebug("rrKSOTCPHandler - right header")
        command = _RRCommands()
        command.fromBinary(self.request.recv(Size_RRCommands))
        if (( not command.rightStructure())):
            self.server.continueLoop=False
            logMessageError("TCP data wrong! "
                           + "ID:"+ str(command.StructureID)+"!=" +str(StructureID_rrCommands)
                           )
            return
        logMessageDebug("rrKSOTCPHandler - right structure")
        if (( command.paramSlength==0)):
            logMessageError("Empty command received.")
            return
        logMessageDebug("rrKSOTCPHandler - not an empty command")
        global rrKSONextCommand
        rrKSONextCommand= command.paramS
        rrKSONextCommand= rrKSONextCommand.replace("\\n","\n")
        rrKSONextCommand= rrKSONextCommand.replace("\n ","\n")
        rrKSONextCommand= rrKSONextCommand.replace("\n ","\n")



    



class rrKSOServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    timeout = commandTimeout
    daemon_threads = True
    allow_reuse_address = True
    continueLoop = True
    
    def __init__(self, server_address_in, RequestHandlerClass):
        logMessageDebug("rrKSOServer init")
        socketserver.TCPServer.__init__(self, server_address_in, RequestHandlerClass)
    
    def handle_timeout(self):
        logMessageError('Timeout!')
        self.continueLoop=False
    
    def handle_error(self, request, client_address):
        logMessageError(" Issue while handline connection to " + str(client_address))
        self.continueLoop=False
        import traceback
        logMessageError(traceback.format_exc())

    def print_port(self):
        logMessage("Server is listening on port "+str(self.server_address))

    def closeTCP(self):
        logMessageDebug("rrKSOServer closeTCP")
        #self.shutdown()
        #logMessageDebug("rrKSOServer shutdown executed")
        self.server_close()
        logMessageDebug("rrKSOServer server_close executed")
        


def writeRenderPlaceholder(filename):
    logMessage(filename )
    import socket
    hostName = socket.gethostname()
    hostName = hostName[:100]
    img_file = open(filename, "wb")
    img_file.write(str("rrDB").encode("ascii"))  # Magic ID
    img_file.write(str("\x02\x0B").encode("ascii"))  # DataType ID
    img_file.write(str(chr(len(hostName))).encode("ascii"))
    img_file.write(str("\x00").encode("ascii"))
    img_file.write(str("\x00\x00").encode("ascii"))
    for x in range(0, len(hostName)):
        img_file.write(str(hostName[x]).encode("ascii"))
        img_file.write(str("\x00").encode("ascii"))  # unicode
    for x in range(len(hostName), 51):
        img_file.write(str("\x00\x00").encode("ascii"))
    img_file.close()   


def writeRenderPlaceholder_nr(filename, frameNr, padding, ext):
    padding=int(padding)
    if (padding==0):
        padding=4
    filenameFinal=filename +str(frameNr).zfill(int(padding)) + ext
    writeRenderPlaceholder(filenameFinal)


#logMessageDebug("KSO_IMPORTED__KSO_IMPORTED__KSO_IMPORTED__KSO_IMPORTED__KSO_IMPORTED__KSO_IMPORTED__KSO_IMPORTED")

