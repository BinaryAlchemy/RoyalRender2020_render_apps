from Katana import NodegraphAPI, NodeDebugOutput, KatanaFile
import sys
import os

def convert(katanaFile, renderer, outputnode, startframe, endframe, imagename, imagedir, threadId):
    KatanaFile.Load(katanaFile)

    for i in range(int(startframe), (int(endframe) + 1)):
        NodegraphAPI.SetCurrentTime(i)
        fileExtension = ''
        if renderer == 'prman':
            fileExtension = 'rib'
        elif renderer == 'arnold':
            fileExtension = 'ass'
        fileName = os.path.join(imagedir, '%s%04d.%s') %(imagename, i, fileExtension)
        print('############################', fileName, '###############################')
        NodeDebugOutput.WriteRenderOutput(NodegraphAPI.GetNode(outputnode), renderer, filename=fileName)
        sys.stdout.write('[k2rrFrameConvProgress]_' +  str(i) + '_thread_' + str(threadId) + '_')

    sys.stdout.write('[k2rrThreadFinished]_' + str(threadId) + '_')

# print sys.argv
if len(sys.argv) < 8:
    raise ValueError('wrong type of arguments')

katanaFile = sys.argv[1]
renderer = sys.argv[2]
outputnode = sys.argv[3]
startframe = sys.argv[4]
endframe = sys.argv[5]
imagename = sys.argv[6]
imagedir = sys.argv[7]
threadId = sys.argv[8]

# print(katanaFile, renderer, outputnode, startframe, endframe, imagename, imagedir, threadId)
convert(katanaFile, renderer, outputnode, startframe, endframe, imagename, imagedir, threadId)


