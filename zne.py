#!/usr/bin/python3

from PySide.QtCore import (Qt, QSocketNotifier)
from PySide.QtGui import (QPainter, QBrush, QPalette, QIcon)
from PySide.QtGui import (QApplication, QMainWindow, QAction, QWidget,
    QGraphicsItem, QGraphicsScene, QGraphicsView)

from zocp import ZOCP
import zmq

import logging

from qnodeseditor import QNodesEditor
from qneblock import QNEBlock
from qneport import QNEPort
from qneconnection import QNEConnection

class QNEMainWindow(QMainWindow):
    def __init__(self, parent):
        super(QNEMainWindow, self).__init__(parent)

        self.logger = logging.getLogger("zne")
        self.logger.setLevel(logging.INFO)

        self.setMinimumSize(640,480)
        self.setWindowTitle("ZOCP Node Editor")
        self.setWindowIcon(QIcon('assets/icon.png'))

        self.scene = QGraphicsScene(self)
        self.scene.setBackgroundBrush( QApplication.palette().window() )

        self.view = QGraphicsView(self)
        self.view.setScene(self.scene)
        self.view.setRenderHint(QPainter.Antialiasing)
        self.setCentralWidget(self.view)

        self.nodesEditor = QNodesEditor(self)
        self.nodesEditor.install(self.scene)

        self.nodesEditor.onAddConnection = self.onAddConnection
        self.nodesEditor.onRemoveConnection = self.onRemoveConnection
        self.nodesEditor.onBlockMoved = self.onBlockMoved

        self.scale = 1
        self.installActions()

        self.initZOCP()

        self.nodes = {}
        self.pendingSubscribers = {}


    def closeEvent(self, *args):
        self.zocp.stop()


    def installActions(self):
        quitAct = QAction("&Quit", self, shortcut="Ctrl+Q",
            statusTip="Exit the application", triggered=self.close)

        fileMenu = self.menuBar().addMenu("&File")
        fileMenu.addAction(quitAct)

        # for shortcuts
        self.view.addAction(quitAct)

        selectAllAct = QAction("Select &All", self, shortcut="Ctrl+A",
            triggered=self.nodesEditor.selectAll)
        selectInverseAct = QAction("Select &Inverse", self, shortcut="Ctrl+I",
            triggered=self.nodesEditor.selectInverse)
        deleteSelectedAct = QAction("&Delete Selected", self, shortcut="Del",
            triggered=self.nodesEditor.deleteSelected)

        editMenu = self.menuBar().addMenu("&Edit")
        editMenu.addAction(selectAllAct)
        editMenu.addAction(selectInverseAct)
        editMenu.addSeparator()
        editMenu.addAction(deleteSelectedAct)

        self.view.addAction(selectAllAct)
        self.view.addAction(selectInverseAct)
        self.view.addAction(deleteSelectedAct)

        zoomInAct = QAction("Zoom &In", self, shortcut="Ctrl++",
            triggered=self.zoomIn)
        zoomOutAct = QAction("Zoom &Out", self, shortcut="Ctrl+-",
            triggered=self.zoomOut)
        zoomResetAct = QAction("&Reset Zoom", self, shortcut="Ctrl+0",
            triggered=self.zoomReset)

        viewMenu = self.menuBar().addMenu("&View")
        viewMenu.addAction(zoomInAct)
        viewMenu.addAction(zoomOutAct)
        viewMenu.addSeparator()
        viewMenu.addAction(zoomResetAct)

        self.view.addAction(zoomInAct)
        self.view.addAction(zoomOutAct)
        self.view.addAction(zoomResetAct)


    def zoomIn(self):
        if self.scale < 4:
            self.scale *= 1.2
            self.view.scale(1.2, 1.2)


    def zoomOut(self):
        if self.scale > 0.1:
            self.scale /= 1.2
            self.view.scale(1/1.2, 1/1.2)


    def zoomReset(self):
        self.scale = 1
        self.view.setTransform(QTransform())


    #########################################
    # Node editor callbacks
    #########################################
    def onAddConnection(self, connection, fromPort, toPort):
        fromBlock = fromPort.block()
        toBlock = toPort.block()

        emitter = ("%s@%s" % (fromPort.portName(), fromBlock.uuid().hex))
        receiver = ("%s@%s" % (toPort.portName(), toBlock.uuid().hex))

        self.zocp.peer_subscribe(toBlock.uuid(), emitter, receiver)

        self.logger.debug("added subscription from %s on %s to %s on %s" %
               (fromPort.portName(), fromBlock.name(), toPort.portName(), toBlock.name()))


    def onRemoveConnection(self, connection, fromPort, toPort):
        fromBlock = fromPort.block()
        toBlock = toPort.block()

        emitter = ("%s@%s" % (fromPort.portName(), fromBlock.uuid().hex))
        receiver = ("%s@%s" % (toPort.portName(), toBlock.uuid().hex))

        self.zocp.peer_unsubscribe(toBlock.uuid(), emitter, receiver)

        self.logger.debug("removed subscription from %s on %s to %s on %s" %
               (fromPort.portName(), fromBlock.name(), toPort.portName(), toBlock.name()))


    def onBlockMoved(self, block):
        pos = block.pos()
        peer = block.uuid()
        self.zocp.peer_set(peer, {"_zne_position": [pos.x(), pos.y()]})


    #########################################
    # ZOCP implementation
    #########################################
    def initZOCP(self):
        import socket

        self.zocp = ZOCP()
        self.zocp.set_name("ZOCP Node Editor@%s" % socket.gethostname())
        self.notifier = QSocketNotifier(
            self.zocp.inbox.getsockopt(zmq.FD),
            QSocketNotifier.Read)
        self.notifier.setEnabled(True)
        self.notifier.activated.connect(self.onZOCPEvent)
        self.zocp.on_peer_enter = self.onPeerEnter
        self.zocp.on_peer_exit = self.onPeerExit
        self.zocp.on_peer_modified = self.onPeerModified
        self.zocp.on_peer_signaled = self.onPeerSignaled
        self.zocp.start()

        zl = logging.getLogger("zocp")
        zl.setLevel(logging.INFO)


    def onZOCPEvent(self):
        self.zocp.run_once(0)


    def onPeerEnter(self, peer, name, *args, **kwargs):
        # Subscribe to any and all value changes
        self.zocp.peer_subscribe(peer)

        # Add named block; ports are not known at this point
        node = {}
        node["block"] = QNEBlock(None)
        self.scene.addItem(node["block"])
        node["block"].setName(name)
        node["block"].setUuid(peer)
        node["block"].addPort(name, False, False, QNEPort.NamePort)
        node["block"].setVisible(False)
        node["ports"] = dict()

        self.nodes[peer.hex] = node


    def onPeerExit(self, peer, name, *args, **kwargs):
        # Unsibscribe from value changes
        self.zocp.peer_unsubscribe(peer)

        # Remove block
        if peer.hex in self.nodes:
            self.nodes[peer.hex]["block"].delete()
            self.nodes.pop(peer.hex)


    def onPeerModified(self, peer, data, *args, **kwargs):
        for portname in data:
            portdata = data[portname]

            if portname not in self.nodes[peer.hex]["ports"]:
                if "access" in portdata:
                    hasInput = "s" in portdata["access"]
                    hasOutput = "e" in portdata["access"]
                    port = self.nodes[peer.hex]["block"].addPort(portname, hasInput, hasOutput)
                    self.nodes[peer.hex]["ports"][portname] = port

                else:
                    # Metadata, not a capability
                    if portname == "_zne_position":
                        block = self.nodes[peer.hex]["block"]
                        block.setPos(portdata[0], portdata[1])

            else:
                #TODO: modify existing port
                port = self.nodes[peer.hex]["ports"][portname]

            if "subscribers" in portdata:
                self.updateSubscribers(port, portdata["subscribers"])

        if len(self.nodes[peer.hex]["ports"]) > 0:
            self.nodes[peer.hex]["block"].setVisible(True)
        self.updatePendingSubscribers(peer)


    def onPeerSignaled(self, peer, data, *args, **kwargs):
        pass


    def updateSubscribers(self, port, subscribers):
        connections = port.connections()
        # TODO: remove connections that are not in the new subscribers list

        port1 = port.outputPort

        for subscriber in subscribers:
            [uuid, portname] = subscriber
            if uuid in self.nodes:
                node = self.nodes[uuid]
                if portname in node["ports"]:
                    port2 = node["ports"][portname]
                    if not port2.isConnected(port1):
                        # create new connection
                        connection = QNEConnection(None)
                        connection.setPort1(port1)
                        connection.setPort2(port2)
                        connection.updatePosFromPorts()
                        connection.updatePath()
                        self.scene.addItem(connection)
                    continue

            # if the connection could not be made yet, add it to a list of
            # pending subscriber-connections
            if uuid not in self.pendingSubscribers:
                self.pendingSubscribers[uuid] = []
            self.pendingSubscribers[uuid].append([port1, portname])


    def updatePendingSubscribers(self, peer):
        if peer.hex in self.pendingSubscribers:
            for subscriber in self.pendingSubscribers[peer.hex]:
                [port1, portname] = subscriber
                if peer.hex in self.nodes and portname in self.nodes[peer.hex]["ports"]:
                    port2 = self.nodes[peer.hex]["ports"][portname]

                    connection = QNEConnection(None)
                    connection.setPort1(port1)
                    connection.setPort2(port2)
                    connection.updatePosFromPorts()
                    connection.updatePath()
                    self.scene.addItem(connection)
                else:
                    # TODO: handle case where port is still not available
                    pass

            self.pendingSubscribers.pop(peer.hex)


if __name__ == '__main__':
    import sys

    app = QApplication(sys.argv)

    widget = QNEMainWindow(None)
    widget.show()

    sys.exit(app.exec_())
