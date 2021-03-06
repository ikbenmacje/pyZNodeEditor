# Copyright (c) 2014, ALDO HOEBEN
# Copyright (c) 2012, STANISLAW ADASZEWSKI
#All rights reserved.
#
#Redistribution and use in source and binary forms, with or without
#modification, are permitted provided that the following conditions are met:
#    * Redistributions of source code must retain the above copyright
#      notice, this list of conditions and the following disclaimer.
#    * Redistributions in binary form must reproduce the above copyright
#      notice, this list of conditions and the following disclaimer in the
#      documentation and/or other materials provided with the distribution.
#    * Neither the name of STANISLAW ADASZEWSKI nor the
#      names of its contributors may be used to endorse or promote products
#      derived from this software without specific prior written permission.
#
#THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
#ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
#WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
#DISCLAIMED. IN NO EVENT SHALL STANISLAW ADASZEWSKI BE LIABLE FOR ANY
#DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
#(INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
#LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
#ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
#(INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
#SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.


from PySide.QtCore import (Qt)
from PySide.QtGui import (QBrush, QColor, QPainter, QPainterPath, QPen)
from PySide.QtGui import (QApplication, QGraphicsItem, QGraphicsPathItem, 
    QGraphicsDropShadowEffect)

from qneport import QNEPort

class QNEBlock(QGraphicsPathItem):
    (Type) = (QGraphicsItem.UserType +3)

    def __init__(self, parent):
        super(QNEBlock, self).__init__(parent)

        self.m_nodeEditor = None
        self.m_name = ""
        self.m_uuid = ""

        self.normalBrush = QApplication.palette().dark()
        normalColor = self.normalBrush.color()
        normalColor.setAlphaF(0.8)
        self.normalBrush.setColor(normalColor)

        self.selectedBrush = QApplication.palette().light()
        selectedColor = self.selectedBrush.color()
        selectedColor.setAlphaF(0.8)
        self.selectedBrush.setColor(selectedColor)

        self.pen = QPen(QApplication.palette().text().color(), 1)

        path = QPainterPath()
        path.addRoundedRect(-50, -15, 100, 30, 5, 5)
        self.setPath(path)
        self.setBrush(self.normalBrush)
        self.setFlag(QGraphicsItem.ItemIsMovable)
        self.setFlag(QGraphicsItem.ItemIsSelectable)

        self.effect = QGraphicsDropShadowEffect(None)
        self.effect.setBlurRadius(8)
        self.effect.setOffset(2,2)
        self.setGraphicsEffect(self.effect)

        self.horzMargin = 20
        self.vertMargin = 5
        self.width = self.horzMargin
        self.height = self.vertMargin


    def __del__(self):
        #print("Del QNEBlock")
        pass


    def delete(self):
        for port in self.ports():
            for connection in port.connections():
                connection.delete()
            port.delete()
        if self.scene():
            self.scene().removeItem(self)


    def paint(self, painter, option, widget):
        if self.isSelected():
            painter.setBrush(self.selectedBrush)
        else:
            painter.setBrush(self.normalBrush)
        painter.setPen(self.pen)

        painter.drawPath(self.path())


    def itemChange(self, change, value):
        if change == QGraphicsItem.ItemSelectedHasChanged:
            self.setZValue( 1 if value else 0 )

        return value


    def addPort(self, name, hasInput = False, hasOutput = False, flags = 0):
        port = QNEPort(self)
        port.setName(name)
        port.setCanConnect(hasInput, hasOutput)
        port.setNEBlock(self)
        port.setPortFlags(flags)

        innerSize = port.innerSize()
        width = innerSize.width()
        height = innerSize.height()
        if width > self.width - self.horzMargin:
            self.width = width + self.horzMargin
        self.height += height

        path = QPainterPath()
        path.addRoundedRect(-self.width/2, -self.height/2, self.width, self.height, 5, 5)
        self.setPath(path)

        y = -self.height / 2 + self.vertMargin + port.radius()
        for port_ in self.childItems():
            if port_.type() != QNEPort.Type:
                continue

            port_.setPos(-self.width/2 - port.radius(), y)
            port_.setWidth(self.width)
            y += port_.innerSize().height()

        return port

        
    def addNonePort(self, name):
        self.addPort(name, False, False)


    def addInputPort(self, name):
        self.addPort(name, True, False)


    def addOutputPort(self, name):
        self.addPort(name, False, True)


    def addInputOutputPort(self, name):
        self.addPort(name, True, True)


    def addNonePorts(self, names):
        for name in names:
            self.addNonePort(name)


    def addInputPorts(self, names):
        for name in names:
            self.addInputPort(name)


    def addOutputPorts(self, names):
        for name in names:
            self.addOutputPort(name)


    def addInputOutputPorts(self, names):
        for name in names:
            self.addInputOutputPort(name)


    def clone(self):
        block = QNEBlock(None)
        self.scene().addItem(block)

        for port_ in self.childItems():
            block.addPort(port_.portName(), port_.hasInput(), port_.hasOutput(), port_.portFlags())

        return block


    def ports(self):
        result = []
        for port_ in self.childItems():
            if port_.type() == QNEPort.Type:
                result.append(port_)

        return result


    def type(self):
        return self.Type


    def setName(self, name):
        self.m_name = name


    def name(self):
        return self.m_name


    def setUuid(self, uuid):
        self.m_uuid = uuid


    def uuid(self):
        return self.m_uuid


    def setNodeEditor(self, editor):
        self.m_nodeEditor = editor


    def nodeEditor(self):
        return self.m_nodeEditor
