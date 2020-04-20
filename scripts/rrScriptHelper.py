    
class rrOS(object):   
	Any=0
	Windows=1
	Linux=2
	Osx=3
    
    
def getRR_Root():
    # findRR_Root adds the RR path as search path for the module
    # This function will only work if RR was installed on the machine
    # If you are using it from an external machine, you have to add the path to the rrPy module yourself
    # sys.path.append(MyModulePath)
    import os
    if (not os.environ.has_key('RR_ROOT')):
        return ""
    rrRoot=os.environ['RR_ROOT']
    rrRoot= rrRoot.replace("_debug", "_release")
    return  rrRoot
    

def getOS():
    import sys
    if (sys.platform.lower() == "win32"):
        return rrOS.Windows
    elif (sys.platform.lower() == "darwin"):
        return rrOS.Osx
    else:
        return rrOS.Linux


def ireplaceStartsWith(text, old, new ):
    idx = 0
    while idx < len(text):
        index_l = text.lower().find(old.lower(), idx)
        if index_l == -1:
            return text
        if index_l > 0:
            return text
        text = text[:index_l] + new + text[index_l + len(old):]
        idx = index_l + len(old)
    return text
                    
    

class rrOSConversion(object):

    def __init__(self):
        self.clear()
    
    def clear(self):
        self.errorString=""
        self.currentOS=""
        self.tableWin=[]
        self.tableLx=[]
        self.tableOsx=[]
        self.settingsLoaded= False
    
    def loadSettings(self):
        if (self.settingsLoaded):
            return True
        self.clear()
        iniLocation=(getRR_Root()+ "/sub/cfg_global/OSConversion.ini")
        import ConfigParser
        config = ConfigParser.ConfigParser()
        if (len(config.read(iniLocation))<=0):
            errorString="Unable to read ini file or file does not exist: '"+iniLocation+"'"
            return False
        if (len(config.sections())<=0):
            errorString="Ini file is empty: '"+iniLocation+"'"
            return False
        try:
            options = config.options("OSConversion")
        except:        
            errorString="Ini file has no section 'OSConversion': '"+iniLocation+"'"
            return False
        
        for option in options:
            try:
                value= config.get("OSConversion", option)
                splitVal=value.split('?')
                if (len(splitVal)==3):
                    winValue=splitVal[0]
                    winValue= winValue.replace("\\\\","\\")
                    self.tableWin.append(winValue)
                    self.tableLx.append(splitVal[1])
                    self.tableOsx.append(splitVal[2])
            except:
                pass
        self.settingsLoaded= True
        return True    
            
    def getTableOS(self, fromOS, toOS, onlySlashes):
        if len(self.tableWin)==0:
            return [], []
        if (fromOS==toOS):
            return [], []
        if (fromOS==rrOS.Any or toOS==rrOS.Any):
            return [], []
        import copy
        if (fromOS==rrOS.Osx):
            fromTable= copy.deepcopy(self.tableOsx)
        elif (fromOS==rrOS.Linux):
            fromTable= copy.deepcopy(self.tableLx)
        else:
            fromTable= copy.deepcopy(self.tableWin)
        if (toOS==rrOS.Osx):
            toTable= copy.deepcopy(self.tableOsx)
        elif (toOS==rrOS.Linux):
            toTable= copy.deepcopy(self.tableLx)
        else:
            toTable= copy.deepcopy(self.tableWin)
        for i in range(len(fromTable)-1,-1,-1):
            if (len(fromTable[i])==0 or len(toTable[i])==0):
                fromTable.pop(i)
                toTable.pop(i)
                i-=1
                continue
            if (onlySlashes):
                toTable[i]= toTable[i].replace("\\","/")
                fromTable[i]= fromTable[i].replace("\\","/")
        return fromTable, toTable
        
    def getTable(self, fromOS, onlySlashes=False):
        return self.getTableOS(fromOS, getOS(), onlySlashes)
        
    def replaceString(self, inputString, fromOS, toOS, onlySlashes):
        fromOSlist, toOSlist = self.getTableOS(fromOS,toOS,False)
        if (len(fromOSlist)>0):
            for i in range(len(fromOSlist)):
                inputString= ireplaceStartsWith(inputString, fromOSlist[i], toOSlist[i])  
        return inputString
    
def xmlIndent(elem, level=0):
    i = "\n" + level * ' '
    if len(elem):
        if not elem.text or not elem.text.strip():
            elem.text = i + " "
        for e in elem:
            xmlIndent(e, level + 1)
            if not e.tail or not e.tail.strip():
                e.tail = i + " "
        if not e.tail or not e.tail.strip():
            e.tail = i
    else:
        if level and (not elem.tail or not elem.tail.strip()):
            elem.tail = i
    return True
    
def createVRayRemapFile(filename, fromOS):    
    osConvert= rrOSConversion()
    osConvert.loadSettings()
    from xml.etree.ElementTree import ElementTree, Element, SubElement
    rootElement = Element("RemapPaths")
    fromOSlist, toOSlist = osConvert.getTableOS(fromOS,getOS(),False)
    if (len(fromOSlist)>0):
        for i in range(len(fromOSlist)):
            RemapItem = SubElement(rootElement, "RemapItem")
            sub = SubElement(RemapItem, "From")
            sub.text = fromOSlist[i]
            sub = SubElement(RemapItem, "To")
            sub.text = toOSlist[i]
    xml = ElementTree(rootElement)
    xmlIndent(xml.getroot())
    tmpFile = open(filename, "w")
    if not tmpFile == None:
        xml.write(tmpFile)
        tmpFile.close()
    else:
        print("No valid filename has been passed to the function")
        try:
            tmpFile.close()
        except:
            pass
        return False
    print("Saved "+str(len(fromOSlist))+" OS path conversions into "+filename+"\n\n")
    return True    
    