# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'Gen2OpsConsole.ui'
##
## Created by: Qt User Interface Compiler version 6.8.0
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide6.QtCore import (QCoreApplication, QDate, QDateTime, QLocale,
    QMetaObject, QObject, QPoint, QRect,
    QSize, QTime, QUrl, Qt)
from PySide6.QtGui import (QAction, QBrush, QColor, QConicalGradient,
    QCursor, QFont, QFontDatabase, QGradient,
    QIcon, QImage, QKeySequence, QLinearGradient,
    QPainter, QPalette, QPixmap, QRadialGradient,
    QTransform)
from PySide6.QtWidgets import (QApplication, QCheckBox, QGridLayout, QGroupBox,
    QHBoxLayout, QLabel, QMainWindow, QMenu,
    QMenuBar, QPushButton, QRadioButton, QSizePolicy,
    QSpacerItem, QStatusBar, QTextEdit, QVBoxLayout,
    QWidget)

class Ui_MasterControl(object):
    def setupUi(self, MasterControl):
        if not MasterControl.objectName():
            MasterControl.setObjectName(u"MasterControl")
        MasterControl.resize(794, 602)
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(MasterControl.sizePolicy().hasHeightForWidth())
        MasterControl.setSizePolicy(sizePolicy)
        font = QFont()
        font.setHintingPreference(QFont.PreferFullHinting)
        MasterControl.setFont(font)
        self.actionExit = QAction(MasterControl)
        self.actionExit.setObjectName(u"actionExit")
        self.centralwidget = QWidget(MasterControl)
        self.centralwidget.setObjectName(u"centralwidget")
        self.gridLayout = QGridLayout(self.centralwidget)
        self.gridLayout.setObjectName(u"gridLayout")
        self.groupBox_4 = QGroupBox(self.centralwidget)
        self.groupBox_4.setObjectName(u"groupBox_4")
        font1 = QFont()
        font1.setPointSize(11)
        font1.setBold(True)
        font1.setHintingPreference(QFont.PreferFullHinting)
        self.groupBox_4.setFont(font1)
        self.verticalLayout_11 = QVBoxLayout(self.groupBox_4)
        self.verticalLayout_11.setObjectName(u"verticalLayout_11")
        self.horizontalLayout_15 = QHBoxLayout()
        self.horizontalLayout_15.setObjectName(u"horizontalLayout_15")
        self.verticalLayout_3 = QVBoxLayout()
        self.verticalLayout_3.setObjectName(u"verticalLayout_3")
        self.horizontalLayout_11 = QHBoxLayout()
        self.horizontalLayout_11.setObjectName(u"horizontalLayout_11")
        self.verticalLayout = QVBoxLayout()
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.FullAutoRadioButton = QRadioButton(self.groupBox_4)
        self.FullAutoRadioButton.setObjectName(u"FullAutoRadioButton")

        self.verticalLayout.addWidget(self.FullAutoRadioButton)

        self.SemiAutoRadioButton = QRadioButton(self.groupBox_4)
        self.SemiAutoRadioButton.setObjectName(u"SemiAutoRadioButton")

        self.verticalLayout.addWidget(self.SemiAutoRadioButton)

        self.SequencerOffRadioButton = QRadioButton(self.groupBox_4)
        self.SequencerOffRadioButton.setObjectName(u"SequencerOffRadioButton")

        self.verticalLayout.addWidget(self.SequencerOffRadioButton)


        self.horizontalLayout_11.addLayout(self.verticalLayout)

        self.horizontalSpacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_11.addItem(self.horizontalSpacer)

        self.verticalLayout_Sun = QVBoxLayout()
        self.verticalLayout_Sun.setObjectName(u"verticalLayout_Sun")
        self.horizontalLayout_6 = QHBoxLayout()
        self.horizontalLayout_6.setObjectName(u"horizontalLayout_6")
        self.label_3 = QLabel(self.groupBox_4)
        self.label_3.setObjectName(u"label_3")

        self.horizontalLayout_6.addWidget(self.label_3)

        self.SunriseLabel = QLabel(self.groupBox_4)
        self.SunriseLabel.setObjectName(u"SunriseLabel")
        font2 = QFont()
        font2.setPointSize(11)
        font2.setBold(False)
        font2.setKerning(True)
        font2.setHintingPreference(QFont.PreferFullHinting)
        self.SunriseLabel.setFont(font2)

        self.horizontalLayout_6.addWidget(self.SunriseLabel)


        self.verticalLayout_Sun.addLayout(self.horizontalLayout_6)

        self.horizontalLayout_5 = QHBoxLayout()
        self.horizontalLayout_5.setObjectName(u"horizontalLayout_5")
        self.label_4 = QLabel(self.groupBox_4)
        self.label_4.setObjectName(u"label_4")

        self.horizontalLayout_5.addWidget(self.label_4)

        self.SunsetLabel = QLabel(self.groupBox_4)
        self.SunsetLabel.setObjectName(u"SunsetLabel")
        self.SunsetLabel.setFont(font2)

        self.horizontalLayout_5.addWidget(self.SunsetLabel)


        self.verticalLayout_Sun.addLayout(self.horizontalLayout_5)

        self.horizontalLayout_7 = QHBoxLayout()
        self.horizontalLayout_7.setObjectName(u"horizontalLayout_7")
        self.label_2 = QLabel(self.groupBox_4)
        self.label_2.setObjectName(u"label_2")

        self.horizontalLayout_7.addWidget(self.label_2)

        self.NipStateLabel = QLabel(self.groupBox_4)
        self.NipStateLabel.setObjectName(u"NipStateLabel")
        self.NipStateLabel.setFont(font2)

        self.horizontalLayout_7.addWidget(self.NipStateLabel)


        self.verticalLayout_Sun.addLayout(self.horizontalLayout_7)


        self.horizontalLayout_11.addLayout(self.verticalLayout_Sun)


        self.verticalLayout_3.addLayout(self.horizontalLayout_11)

        self.horizontalLayout_8 = QHBoxLayout()
        self.horizontalLayout_8.setObjectName(u"horizontalLayout_8")
        self.label_7 = QLabel(self.groupBox_4)
        self.label_7.setObjectName(u"label_7")
        sizePolicy1 = QSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Preferred)
        sizePolicy1.setHorizontalStretch(0)
        sizePolicy1.setVerticalStretch(0)
        sizePolicy1.setHeightForWidth(self.label_7.sizePolicy().hasHeightForWidth())
        self.label_7.setSizePolicy(sizePolicy1)

        self.horizontalLayout_8.addWidget(self.label_7)

        self.MasterStateLabel = QLabel(self.groupBox_4)
        self.MasterStateLabel.setObjectName(u"MasterStateLabel")
        sizePolicy2 = QSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Preferred)
        sizePolicy2.setHorizontalStretch(0)
        sizePolicy2.setVerticalStretch(0)
        sizePolicy2.setHeightForWidth(self.MasterStateLabel.sizePolicy().hasHeightForWidth())
        self.MasterStateLabel.setSizePolicy(sizePolicy2)
        self.MasterStateLabel.setFont(font2)

        self.horizontalLayout_8.addWidget(self.MasterStateLabel)


        self.verticalLayout_3.addLayout(self.horizontalLayout_8)


        self.horizontalLayout_15.addLayout(self.verticalLayout_3)

        self.horizontalSpacer_2 = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_15.addItem(self.horizontalSpacer_2)

        self.verticalLayout_9 = QVBoxLayout()
        self.verticalLayout_9.setObjectName(u"verticalLayout_9")
        self.horizontalLayout_14 = QHBoxLayout()
        self.horizontalLayout_14.setObjectName(u"horizontalLayout_14")
        self.verticalLayout_8 = QVBoxLayout()
        self.verticalLayout_8.setObjectName(u"verticalLayout_8")
        self.horizontalLayout_9 = QHBoxLayout()
        self.horizontalLayout_9.setObjectName(u"horizontalLayout_9")
        self.label_5 = QLabel(self.groupBox_4)
        self.label_5.setObjectName(u"label_5")

        self.horizontalLayout_9.addWidget(self.label_5)

        self.GhiLabel = QLabel(self.groupBox_4)
        self.GhiLabel.setObjectName(u"GhiLabel")
        self.GhiLabel.setFont(font2)

        self.horizontalLayout_9.addWidget(self.GhiLabel)


        self.verticalLayout_8.addLayout(self.horizontalLayout_9)

        self.horizontalLayout_10 = QHBoxLayout()
        self.horizontalLayout_10.setObjectName(u"horizontalLayout_10")
        self.label_6 = QLabel(self.groupBox_4)
        self.label_6.setObjectName(u"label_6")

        self.horizontalLayout_10.addWidget(self.label_6)

        self.DniLabel = QLabel(self.groupBox_4)
        self.DniLabel.setObjectName(u"DniLabel")
        self.DniLabel.setFont(font2)

        self.horizontalLayout_10.addWidget(self.DniLabel)


        self.verticalLayout_8.addLayout(self.horizontalLayout_10)

        self.verticalSpacer = QSpacerItem(20, 18, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.verticalLayout_8.addItem(self.verticalSpacer)


        self.horizontalLayout_14.addLayout(self.verticalLayout_8)

        self.horizontalSpacer_3 = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_14.addItem(self.horizontalSpacer_3)

        self.horizontalLayout_12 = QHBoxLayout()
        self.horizontalLayout_12.setObjectName(u"horizontalLayout_12")
        self.verticalLayout_5 = QVBoxLayout()
        self.verticalLayout_5.setObjectName(u"verticalLayout_5")
        self.label_8 = QLabel(self.groupBox_4)
        self.label_8.setObjectName(u"label_8")

        self.verticalLayout_5.addWidget(self.label_8)

        self.label_9 = QLabel(self.groupBox_4)
        self.label_9.setObjectName(u"label_9")

        self.verticalLayout_5.addWidget(self.label_9)

        self.label_10 = QLabel(self.groupBox_4)
        self.label_10.setObjectName(u"label_10")

        self.verticalLayout_5.addWidget(self.label_10)

        self.label_11 = QLabel(self.groupBox_4)
        self.label_11.setObjectName(u"label_11")

        self.verticalLayout_5.addWidget(self.label_11)


        self.horizontalLayout_12.addLayout(self.verticalLayout_5)

        self.verticalLayout_4 = QVBoxLayout()
        self.verticalLayout_4.setObjectName(u"verticalLayout_4")
        self.StanleyTempLabel = QLabel(self.groupBox_4)
        self.StanleyTempLabel.setObjectName(u"StanleyTempLabel")
        self.StanleyTempLabel.setFont(font2)

        self.verticalLayout_4.addWidget(self.StanleyTempLabel)

        self.ElecTempLabel = QLabel(self.groupBox_4)
        self.ElecTempLabel.setObjectName(u"ElecTempLabel")
        self.ElecTempLabel.setFont(font2)

        self.verticalLayout_4.addWidget(self.ElecTempLabel)

        self.DomeTempLabel = QLabel(self.groupBox_4)
        self.DomeTempLabel.setObjectName(u"DomeTempLabel")
        self.DomeTempLabel.setFont(font2)

        self.verticalLayout_4.addWidget(self.DomeTempLabel)

        self.OutsideTempLabel = QLabel(self.groupBox_4)
        self.OutsideTempLabel.setObjectName(u"OutsideTempLabel")
        self.OutsideTempLabel.setFont(font2)

        self.verticalLayout_4.addWidget(self.OutsideTempLabel)


        self.horizontalLayout_12.addLayout(self.verticalLayout_4)


        self.horizontalLayout_14.addLayout(self.horizontalLayout_12)

        self.horizontalSpacer_4 = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_14.addItem(self.horizontalSpacer_4)

        self.horizontalLayout_13 = QHBoxLayout()
        self.horizontalLayout_13.setObjectName(u"horizontalLayout_13")
        self.verticalLayout_7 = QVBoxLayout()
        self.verticalLayout_7.setObjectName(u"verticalLayout_7")
        self.label_12 = QLabel(self.groupBox_4)
        self.label_12.setObjectName(u"label_12")

        self.verticalLayout_7.addWidget(self.label_12)

        self.label_13 = QLabel(self.groupBox_4)
        self.label_13.setObjectName(u"label_13")

        self.verticalLayout_7.addWidget(self.label_13)

        self.label_14 = QLabel(self.groupBox_4)
        self.label_14.setObjectName(u"label_14")

        self.verticalLayout_7.addWidget(self.label_14)

        self.label_15 = QLabel(self.groupBox_4)
        self.label_15.setObjectName(u"label_15")

        self.verticalLayout_7.addWidget(self.label_15)


        self.horizontalLayout_13.addLayout(self.verticalLayout_7)

        self.verticalLayout_6 = QVBoxLayout()
        self.verticalLayout_6.setObjectName(u"verticalLayout_6")
        self.BoxTempLabel = QLabel(self.groupBox_4)
        self.BoxTempLabel.setObjectName(u"BoxTempLabel")
        self.BoxTempLabel.setFont(font2)

        self.verticalLayout_6.addWidget(self.BoxTempLabel)

        self.SandTopTempLabel = QLabel(self.groupBox_4)
        self.SandTopTempLabel.setObjectName(u"SandTopTempLabel")
        self.SandTopTempLabel.setFont(font2)

        self.verticalLayout_6.addWidget(self.SandTopTempLabel)

        self.SandMidTempLabel = QLabel(self.groupBox_4)
        self.SandMidTempLabel.setObjectName(u"SandMidTempLabel")
        self.SandMidTempLabel.setFont(font2)

        self.verticalLayout_6.addWidget(self.SandMidTempLabel)

        self.SanBotTempLabel = QLabel(self.groupBox_4)
        self.SanBotTempLabel.setObjectName(u"SanBotTempLabel")
        self.SanBotTempLabel.setFont(font2)

        self.verticalLayout_6.addWidget(self.SanBotTempLabel)


        self.horizontalLayout_13.addLayout(self.verticalLayout_6)


        self.horizontalLayout_14.addLayout(self.horizontalLayout_13)


        self.verticalLayout_9.addLayout(self.horizontalLayout_14)

        self.verticalSpacer_2 = QSpacerItem(20, 18, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.verticalLayout_9.addItem(self.verticalSpacer_2)


        self.horizontalLayout_15.addLayout(self.verticalLayout_9)


        self.verticalLayout_11.addLayout(self.horizontalLayout_15)


        self.gridLayout.addWidget(self.groupBox_4, 1, 0, 1, 1)

        self.groupBox_3 = QGroupBox(self.centralwidget)
        self.groupBox_3.setObjectName(u"groupBox_3")
        self.groupBox_3.setFont(font1)
        self.verticalLayout_10 = QVBoxLayout(self.groupBox_3)
        self.verticalLayout_10.setObjectName(u"verticalLayout_10")
        self.MasterLogTextEdit = QTextEdit(self.groupBox_3)
        self.MasterLogTextEdit.setObjectName(u"MasterLogTextEdit")
        font3 = QFont()
        font3.setPointSize(10)
        font3.setBold(False)
        font3.setHintingPreference(QFont.PreferFullHinting)
        self.MasterLogTextEdit.setFont(font3)
        self.MasterLogTextEdit.setReadOnly(True)

        self.verticalLayout_10.addWidget(self.MasterLogTextEdit)


        self.gridLayout.addWidget(self.groupBox_3, 3, 0, 1, 1)

        self.horizontalLayout_3 = QHBoxLayout()
        self.horizontalLayout_3.setObjectName(u"horizontalLayout_3")
        self.groupBox = QGroupBox(self.centralwidget)
        self.groupBox.setObjectName(u"groupBox")
        self.groupBox.setFont(font1)
        self.verticalLayout_2 = QVBoxLayout(self.groupBox)
        self.verticalLayout_2.setObjectName(u"verticalLayout_2")
        self.horizontalLayout_4 = QHBoxLayout()
        self.horizontalLayout_4.setObjectName(u"horizontalLayout_4")
        self.MotorPowerCheckBox = QCheckBox(self.groupBox)
        self.MotorPowerCheckBox.setObjectName(u"MotorPowerCheckBox")
        self.MotorPowerCheckBox.setFont(font1)
        self.MotorPowerCheckBox.setTristate(False)

        self.horizontalLayout_4.addWidget(self.MotorPowerCheckBox)

        self.UsbPowerCheckBox = QCheckBox(self.groupBox)
        self.UsbPowerCheckBox.setObjectName(u"UsbPowerCheckBox")
        self.UsbPowerCheckBox.setFont(font1)
        self.UsbPowerCheckBox.setTristate(False)

        self.horizontalLayout_4.addWidget(self.UsbPowerCheckBox)


        self.verticalLayout_2.addLayout(self.horizontalLayout_4)


        self.horizontalLayout_3.addWidget(self.groupBox)

        self.groupBox_2 = QGroupBox(self.centralwidget)
        self.groupBox_2.setObjectName(u"groupBox_2")
        self.groupBox_2.setFont(font1)
        self.horizontalLayout_2 = QHBoxLayout(self.groupBox_2)
        self.horizontalLayout_2.setObjectName(u"horizontalLayout_2")
        self.horizontalLayout = QHBoxLayout()
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.OffPushButton = QPushButton(self.groupBox_2)
        self.OffPushButton.setObjectName(u"OffPushButton")

        self.horizontalLayout.addWidget(self.OffPushButton)

        self.HomePushButton = QPushButton(self.groupBox_2)
        self.HomePushButton.setObjectName(u"HomePushButton")

        self.horizontalLayout.addWidget(self.HomePushButton)

        self.TrackPushButton = QPushButton(self.groupBox_2)
        self.TrackPushButton.setObjectName(u"TrackPushButton")

        self.horizontalLayout.addWidget(self.TrackPushButton)

        self.StowPushButton = QPushButton(self.groupBox_2)
        self.StowPushButton.setObjectName(u"StowPushButton")

        self.horizontalLayout.addWidget(self.StowPushButton)

        self.SetTimePushButton = QPushButton(self.groupBox_2)
        self.SetTimePushButton.setObjectName(u"SetTimePushButton")

        self.horizontalLayout.addWidget(self.SetTimePushButton)


        self.horizontalLayout_2.addLayout(self.horizontalLayout)


        self.horizontalLayout_3.addWidget(self.groupBox_2)


        self.gridLayout.addLayout(self.horizontalLayout_3, 2, 0, 1, 1)

        self.horizontalLayout_16 = QHBoxLayout()
        self.horizontalLayout_16.setObjectName(u"horizontalLayout_16")
        self.label = QLabel(self.centralwidget)
        self.label.setObjectName(u"label")
        font4 = QFont()
        font4.setPointSize(14)
        font4.setBold(True)
        font4.setHintingPreference(QFont.PreferFullHinting)
        self.label.setFont(font4)
        self.label.setMidLineWidth(7)
        self.label.setAlignment(Qt.AlignmentFlag.AlignLeading|Qt.AlignmentFlag.AlignLeft|Qt.AlignmentFlag.AlignVCenter)

        self.horizontalLayout_16.addWidget(self.label)

        self.horizontalSpacer_5 = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_16.addItem(self.horizontalSpacer_5)

        self.SystemTimeLabel = QLabel(self.centralwidget)
        self.SystemTimeLabel.setObjectName(u"SystemTimeLabel")
        font5 = QFont()
        font5.setPointSize(12)
        font5.setBold(True)
        font5.setHintingPreference(QFont.PreferFullHinting)
        self.SystemTimeLabel.setFont(font5)
        self.SystemTimeLabel.setAlignment(Qt.AlignmentFlag.AlignRight|Qt.AlignmentFlag.AlignTrailing|Qt.AlignmentFlag.AlignVCenter)

        self.horizontalLayout_16.addWidget(self.SystemTimeLabel)


        self.gridLayout.addLayout(self.horizontalLayout_16, 0, 0, 1, 1)

        MasterControl.setCentralWidget(self.centralwidget)
        self.menubar = QMenuBar(MasterControl)
        self.menubar.setObjectName(u"menubar")
        self.menubar.setGeometry(QRect(0, 0, 794, 21))
        self.menuWindsorOps = QMenu(self.menubar)
        self.menuWindsorOps.setObjectName(u"menuWindsorOps")
        MasterControl.setMenuBar(self.menubar)
        self.statusbar = QStatusBar(MasterControl)
        self.statusbar.setObjectName(u"statusbar")
        MasterControl.setStatusBar(self.statusbar)

        self.menubar.addAction(self.menuWindsorOps.menuAction())
        self.menuWindsorOps.addAction(self.actionExit)

        self.retranslateUi(MasterControl)

        QMetaObject.connectSlotsByName(MasterControl)
    # setupUi

    def retranslateUi(self, MasterControl):
        MasterControl.setWindowTitle(QCoreApplication.translate("MasterControl", u"MasterControl", None))
        self.actionExit.setText(QCoreApplication.translate("MasterControl", u"Exit", None))
        self.groupBox_4.setTitle(QCoreApplication.translate("MasterControl", u"Automation", None))
        self.FullAutoRadioButton.setText(QCoreApplication.translate("MasterControl", u"Full Auto", None))
        self.SemiAutoRadioButton.setText(QCoreApplication.translate("MasterControl", u"Semi Auto", None))
        self.SequencerOffRadioButton.setText(QCoreApplication.translate("MasterControl", u"Sequencer Off", None))
        self.label_3.setText(QCoreApplication.translate("MasterControl", u"Sunrise:", None))
        self.SunriseLabel.setText(QCoreApplication.translate("MasterControl", u"HH:MM:SS", None))
        self.label_4.setText(QCoreApplication.translate("MasterControl", u"Sunset:", None))
        self.SunsetLabel.setText(QCoreApplication.translate("MasterControl", u"HH:MM:SS", None))
        self.label_2.setText(QCoreApplication.translate("MasterControl", u"NIP State:", None))
        self.NipStateLabel.setText(QCoreApplication.translate("MasterControl", u"Off", None))
        self.label_7.setText(QCoreApplication.translate("MasterControl", u"Master State:", None))
        self.MasterStateLabel.setText(QCoreApplication.translate("MasterControl", u"WhoKnows", None))
        self.label_5.setText(QCoreApplication.translate("MasterControl", u"GHI:", None))
        self.GhiLabel.setText(QCoreApplication.translate("MasterControl", u"0000", None))
        self.label_6.setText(QCoreApplication.translate("MasterControl", u"DNI:", None))
        self.DniLabel.setText(QCoreApplication.translate("MasterControl", u"0000", None))
        self.label_8.setText(QCoreApplication.translate("MasterControl", u"Stanley:", None))
        self.label_9.setText(QCoreApplication.translate("MasterControl", u"Elect:", None))
        self.label_10.setText(QCoreApplication.translate("MasterControl", u"Dome:", None))
        self.label_11.setText(QCoreApplication.translate("MasterControl", u"Outside:", None))
        self.StanleyTempLabel.setText(QCoreApplication.translate("MasterControl", u"0000", None))
        self.ElecTempLabel.setText(QCoreApplication.translate("MasterControl", u"0000", None))
        self.DomeTempLabel.setText(QCoreApplication.translate("MasterControl", u"0000", None))
        self.OutsideTempLabel.setText(QCoreApplication.translate("MasterControl", u"0000", None))
        self.label_12.setText(QCoreApplication.translate("MasterControl", u"Box Air:", None))
        self.label_13.setText(QCoreApplication.translate("MasterControl", u"Sand Top:", None))
        self.label_14.setText(QCoreApplication.translate("MasterControl", u"Sand Mid:", None))
        self.label_15.setText(QCoreApplication.translate("MasterControl", u"Sand Bot:", None))
        self.BoxTempLabel.setText(QCoreApplication.translate("MasterControl", u"0000", None))
        self.SandTopTempLabel.setText(QCoreApplication.translate("MasterControl", u"0000", None))
        self.SandMidTempLabel.setText(QCoreApplication.translate("MasterControl", u"0000", None))
        self.SanBotTempLabel.setText(QCoreApplication.translate("MasterControl", u"0000", None))
        self.groupBox_3.setTitle(QCoreApplication.translate("MasterControl", u"Log", None))
        self.groupBox.setTitle(QCoreApplication.translate("MasterControl", u"Power", None))
        self.MotorPowerCheckBox.setText(QCoreApplication.translate("MasterControl", u"Motor Power", None))
        self.UsbPowerCheckBox.setText(QCoreApplication.translate("MasterControl", u"USB Power", None))
        self.groupBox_2.setTitle(QCoreApplication.translate("MasterControl", u"Collectors", None))
        self.OffPushButton.setText(QCoreApplication.translate("MasterControl", u"Off", None))
        self.HomePushButton.setText(QCoreApplication.translate("MasterControl", u"Home", None))
        self.TrackPushButton.setText(QCoreApplication.translate("MasterControl", u"Track", None))
        self.StowPushButton.setText(QCoreApplication.translate("MasterControl", u"Stow", None))
        self.SetTimePushButton.setText(QCoreApplication.translate("MasterControl", u"Set Time", None))
        self.label.setText(QCoreApplication.translate("MasterControl", u"Windsor Master Control Panel", None))
        self.SystemTimeLabel.setText(QCoreApplication.translate("MasterControl", u"HH:MM:SS", None))
        self.menuWindsorOps.setTitle(QCoreApplication.translate("MasterControl", u"WindsorOps", None))
    # retranslateUi

