#!/usr/bin/python

import sys, rospy, math
from PyQt4 import QtGui, QtCore
import numpy as np

from sphero_swarm_node.msg import SpheroTwist, SpheroColor
from multi_apriltags_tracker.msg import april_tag_pos

STEP_LENGTH = 85
RADIUS = 85
MAXSPEED = 256
KP = 0.65
KD = 0.45


class SpheroSwarmLineForm(QtGui.QWidget):
    def __init__(self):
        super(QtGui.QWidget, self).__init__()
        self.resize(600, 480)
        self.sphero_dict = {}
        self.initUI()
        self.initialized = False
        '''The Sphero bluetooth controller maps string names to addresses, The camera maps num to locations numToSphero
        and spheroToNum are dictoinaries that will map back and forth'''
        self.numToSphero = {}
        self.spheroToNum = {}
        self.order = []  # used to keep a follow the leadrer order
        self.location = {}  # dictionary that maps sphero id nums to last known location
        self.error = {}
        self.destination = {}
        self.count = 0
        rospy.init_node('sphero_swarm_line_gui', anonymous=True)

        self.cmdVelPub = rospy.Publisher('cmd_vel', SpheroTwist,
                                         queue_size=1)  # self.cmdVelPub is who we tell about to move sphero
        self.cmdVelSub = rospy.Subscriber("cmd_vel", SpheroTwist, self.cmdVelCallback)

        self.colorPub = rospy.Publisher('set_color', SpheroColor,
                                        queue_size=1)  # who we tell if we want to update the color
        self.aprtSub = rospy.Subscriber('april_tag_pos', april_tag_pos, self.aprtCallback)
        # aprtSub tells us when april tags are updated. When this happens the callback function is called.

    def initUI(self):

        key_instruct_label = """
    Control Your Sphero!
    ---------------------------
    Moving around:
       u    i    o
       j    k    l
       m    ,    .
    """
        self.keyInstructLabel = QtGui.QLabel(key_instruct_label)
        self.cmdVelLabel = QtGui.QLabel("cmd_vel")
        self.cmdVelTextbox = QtGui.QTextEdit()
        self.cmdVelTextbox.setReadOnly(True)
        self.connect(self, QtCore.SIGNAL("sendCmdVelText(PyQt_PyObject)"), self.updateCmdVelTextbox)

        self.spheroLabel = QtGui.QLabel("Spheros:")
        self.spheroListWidget = QtGui.QListWidget()
        self.refreshBtn = QtGui.QPushButton("Refresh")
        self.refreshBtn.clicked.connect(self.refreshDevices)
        btnGridLayout = QtGui.QGridLayout()
        btnGridLayout.addWidget(self.refreshBtn, 0, 4)

        layout = QtGui.QVBoxLayout()
        layout.addWidget(self.keyInstructLabel)
        layout.addWidget(self.cmdVelLabel)
        layout.addWidget(self.cmdVelTextbox)
        layout.addWidget(self.spheroLabel)
        layout.addWidget(self.spheroListWidget)
        layout.addLayout(btnGridLayout)
        self.setLayout(layout)

        self.setWindowTitle("Sphero Swarm Teleop")
        self.show()

    def keyPressEvent(self, e):
        twist = None

        #print "key pressed"
        selected_items = self.spheroListWidget.selectedItems()
        if len(selected_items) == 0:
            return

        #print "selected"

        if e.key() == QtCore.Qt.Key_U:
            twist = SpheroTwist()
            twist.linear.x = -STEP_LENGTH
            twist.linear.y = STEP_LENGTH
            twist.linear.z = 0
            twist.angular.x = 0
            twist.angular.y = 0
            twist.angular.z = 0
        elif e.key() == QtCore.Qt.Key_I:
            twist = SpheroTwist()
            twist.linear.x = 0
            twist.linear.y = STEP_LENGTH
            twist.linear.z = 0
            twist.angular.x = 0
            twist.angular.y = 0
            twist.angular.z = 0
        elif e.key() == QtCore.Qt.Key_O:
            twist = SpheroTwist()
            twist.linear.x = STEP_LENGTH
            twist.linear.y = STEP_LENGTH
            twist.linear.z = 0
            twist.angular.x = 0
            twist.angular.y = 0
            twist.angular.z = 0
        elif e.key() == QtCore.Qt.Key_J:
            twist = SpheroTwist()
            twist.linear.x = -STEP_LENGTH
            twist.linear.y = 0
            twist.linear.z = 0
            twist.angular.x = 0
            twist.angular.y = 0
            twist.angular.z = 0
        elif e.key() == QtCore.Qt.Key_K:
            twist = SpheroTwist()
            twist.linear.x = 0
            twist.linear.y = 0
            twist.linear.z = 0
            twist.angular.x = 0
            twist.angular.y = 0
            twist.angular.z = 0
        elif e.key() == QtCore.Qt.Key_L:
            twist = SpheroTwist()
            twist.linear.x = STEP_LENGTH
            twist.linear.y = 0
            twist.linear.z = 0
            twist.angular.x = 0
            twist.angular.y = 0
            twist.angular.z = 0
        elif e.key() == QtCore.Qt.Key_M:
            twist = SpheroTwist()
            twist.linear.x = -STEP_LENGTH
            twist.linear.y = -STEP_LENGTH
            twist.linear.z = 0
            twist.angular.x = 0
            twist.angular.y = 0
            twist.angular.z = 0
        elif e.key() == QtCore.Qt.Key_Comma:
            twist = SpheroTwist()
            twist.linear.x = 0
            twist.linear.y = -STEP_LENGTH
            twist.linear.z = 0
            twist.angular.x = 0
            twist.angular.y = 0
            twist.angular.z = 0
        elif e.key() == QtCore.Qt.Key_Period:
            twist = SpheroTwist()
            twist.linear.x = STEP_LENGTH
            twist.linear.y = -STEP_LENGTH
            twist.linear.z = 0
            twist.angular.x = 0
            twist.angular.y = 0
            twist.angular.z = 0

        if twist != None:
            twist.name = str(selected_items[0].text())
            self.cmdVelPub.publish(twist)

    def cmdVelCallback(self, msg):
        cmd_vel_text = "(" + str(msg.name) + "),x=" + str(msg.linear.x) + " y=" + str(msg.linear.y)
        self.emit(QtCore.SIGNAL("sendCmdVelText(PyQt_PyObject)"), cmd_vel_text)

    def updateCmdVelTextbox(self, value):
        self.cmdVelTextbox.moveCursor(QtGui.QTextCursor.End)
        self.cmdVelTextbox.ensureCursorVisible()
        self.cmdVelTextbox.append(str(value))
        self.cmdVelTextbox.update()

    ### called when refreshDevices is clicked.
    def refreshDevices(self):
        self.initialized = False
        self.spheroListWidget.clear()
        self.sphero_dict = rospy.get_param('/sphero_swarm/connected')
        self.numToSphero = {}
        self.spheroToNum = {}
        self.order = list()
        self.location = {}
        self.destination = {}
        self.error = {}
        print(self.sphero_dict)

        for name in self.sphero_dict:
            num, ok = QtGui.QInputDialog.getInt(self, "Sphero num input", "Enter April Tag number for %s:" % name)
            self.numToSphero[num] = name
            self.spheroToNum[name] = name
            self.order[len(self.order):] = [num]
            self.location[num] = (-1, -1)
            self.destination[num] = (-1, -1)
            self.error[num] = 0
            self.spheroListWidget.addItem(name)
        self.spheroListWidget.setCurrentRow(0)
        print self.order
        self.initialized = True
        self.update()

    ### main body of algorithm should go here. MSG contains an id, x,y and orientation deta members
    def aprtCallback(self, msg):
       # print msg.id
        if not self.initialized:  # still initializing
            return

        for i in msg.id:
            if self.order[0] == i:
                
                firstInd = msg.id.index(self.order[0])
                self.location[self.order[0]] = (msg.pose[firstInd].x, msg.pose[firstInd].y)
                continue
            twist = SpheroTwist()
            twist.name = self.numToSphero[i]
            twist.linear.z = 0
            twist.angular.x = 0
            twist.angular.y = 0
            twist.angular.z = 0

            msgIndex = msg.id.index(i)
            self.location[i] = (msg.pose[msgIndex].x, msg.pose[msgIndex].y)
            me = i
           

            e_x = self.destination[me][0] - self.location[me][0]
            e_y = self.destination[me][1] - self.location[me][1]
           # print self.numToSphero[i]
           # print "Location (%d,%d)" % self.location[me]
           # print "Destination (%d,%d)" % self.destination[me]
            distance = math.sqrt((e_x * e_x) + (e_y * e_y))
            #print "Distance: %d" % distance
            #print "(ex,ey): (%d,%d)" %(e_x, e_y)
            if  distance <= RADIUS or self.destination[me] == (-1, -1):
                print "Radius"
                leader = self.order[self.order.index(me) - 1]
                self.destination[me] = self.location[leader]
                self.error[me] = 0
                continue
            elif self.count % 8 == 0:
                print "reset"
                leader = self.order[self.order.index(me) - 1]
                self.destination[me] = self.location[leader]
                self.error[me] = (0,0)
                e_x = self.destination[me][0] - self.location[me][0]
                e_y = self.destination[me][1] - self.location[me][1]
                distance = math.sqrt((e_x * e_x) + (e_y * e_y))
            distance -= RADIUS
            omega = math.atan2(e_y, e_x)
            de = distance - self.serror
            self.error[me] = distance
            v = (KP * distance) + (KD * de)
            max(v, MAXSPEED)
            twist.linear.x = v * math.cos(omega)
            twist.linear.y = -v * math.sin(omega)
            self.cmdVelPub.publish(twist)
        self.count += 1
        print "count: %d" % self.count


'''
        for key in self.location:
            self.location[key] = (-1,-1)

        for i in range(0,len(msg.id)):
            self.location[msg.id[i]] = (msg.pose[i].x, msg.pose[i].y)

        for key in msg.id:
            toHere = self.location[key]
            if toHere[0] == -1:
                continue
            nextIndx = self.order.index(key) + 1
            if nextIndx >= len(self.order):
                continue
            nextSpher = self.order[nextIndx]
            fromHere = self.location[nextSpher]
            if fromHere[0] == -1:
                continue
            diffX = toHere[0] - fromHere[0]
            diffY = toHere[1] - fromHere[1]

            distance = math.sqrt((diffX * diffX) + (diffY * diffY))
            twist = SpheroTwist()
            twist.name = self.numToSphero[nextSpher]
            print distance
            if distance < RADIUS:

            else:
                omega = math.atan2(diffY, diffX)
                deltaX = FOLLOW_SPPED * math.cos(omega)
                deltaY = -FOLLOW_SPPED * math.sin(omega)
                twist.linear.x = deltaX
                twist.linear.y = deltaY
                twist.linear.z = 0
                twist.angular.x = 0;
                twist.angular.y = 0;
                twist.angular.z = 0
            self.cmdVelPub.publish(twist) # how to tell sphero to move. all fields in twist must be explicitly set.

'''

if __name__ == '__main__':
    app = QtGui.QApplication(sys.argv)
    w = SpheroSwarmLineForm()
    w.show()
    sys.exit(app.exec_())
