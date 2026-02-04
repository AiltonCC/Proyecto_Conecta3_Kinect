from PyQt6 import QtCore, QtGui
from Ui_VentanaPrincipal import *
from Ui_Jugar import *
from Ui_ConectarServidor import *
from PyQt6.QtWidgets import QMainWindow, QMessageBox, QWidget, QDialog
from PyQt6.uic import loadUi
import sys
from PyQt6.QtCore import QThread, pyqtSignal
import socket
from PyQt6.QtWidgets import QFileDialog
from PyQt6.QtGui import QPixmap
from PyQt6.QtCore import Qt, QCoreApplication
from pykinect import nui
import numpy 
import cv2
import time
from Leds import *  

#Variables globales
head = lhand = rhand = (0,0)
rhdist = lhdist = 0
kinect = nui.Runtime()
kinect.skeleton_engine.enabled = True
online = 0

class ThreadSocket(QThread):
    signal_message = pyqtSignal(str)

    def __init__(self, host, port):
        super().__init__()
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.connect((host, port))
        self.connected = True

    def run(self):
        try:
            while self.connected:
                message = self.server.recv(BUFFER_SIZE)
                if message:
                    self.signal_message.emit(message.decode("utf-8"))
                else:
                    self.signal_message.emit("<!!disconnected!!>")
                    break
        except Exception as e:
            print(f"Error: {e}")
            self.signal_message.emit("<!!error!!>")
        finally:
            self.server.close()
            self.connected = False

    def enviar_mensaje(self, mensaje):
        if self.connected:
            self.server.send(bytes(mensaje, 'utf-8'))
        
        
        
class MainWindow(QMainWindow, Ui_MainWindow):
    def __init__(self, *parent, **flags) -> None:
        super().__init__(*parent, **flags)
        self.setupUi(self)
        self.jugar.clicked.connect(self.conectargame)
        self.sesion.clicked.connect(self.cambiar_foto)
        self.Accionconectar.triggered.connect(self.conectarservidor)
        self.term.triggered.connect(self.terminos)
        self.instrucciones.triggered.connect(self.viewinstruccion)
        self.setWindowTitle("Connect3 - Bienvenido")
        
    def cambiar_foto(self):
        ruta_foto, _ = QFileDialog.getOpenFileName(self, "Seleccionar Foto", "", "Archivos de Imagen (*.png *.jpg *.bmp);;Todos los archivos (*)")

        if ruta_foto:
            pixmap = QPixmap(ruta_foto)
            
            self.label_5.setPixmap(pixmap)
            self.label_5.setScaledContents(True)

    def conectargame(self):
        MainWindow.close(self)
        ventana = Ventana()
        ventana.set_foto_jugador(self.label_5.pixmap().toImage()) 
        if online == 1:     #Visualizacion para el modo Online
            ventana.nombre_usuario = nombre
            ventana.msg.setText('Coneccion Online establecida\nPresione el boton Iniciar kinect')
            ventana.label_2.setText(f'{ventana.nombre_usuario}')
            ventana.setWindowTitle("Connect3 - Online")
        ventana.exec()

    def conectarservidor(self):
        serv = ConnectServidor()
        serv.exec()
        
    def terminos(self):
        QMessageBox.warning(self,'Terminos y Condiciones','Los alumnos no se hacen responsables si el proyecto falla al ultimo momento')
        
    def viewinstruccion(self):
        QMessageBox.information(self,'Indicaciones','Para jugar Online:\n1. Conectese al servidor\n2. Presione el boton Jugar\nPara jugar local:\n1. Presione Jugar')


    
class Ventana(QDialog, Ui_Dialog1):    
    def __init__(self):
        QDialog.__init__(self)
        loadUi("Jugar.ui", self)
        self.onkin.clicked.connect(self.iniciarkinect)
        self.instrucciones.clicked.connect(self.como_jugar)
        self.board = [[''] * 3 for _ in range(3)]  # Inicializar el tablero de 3x3
        self.celdas_marcadas = set()
        self.jugador_actual = 'X'  # Inicializar el jugador actual
        self.last_marked_time = 0  # Inicializar el tiempo de la última casilla marcada
        self.nombre_usuario = None
        self.setWindowTitle("Connect3 - Local")

    def como_jugar(self):
        QMessageBox.information(self,'Indicaciones','1. Presione el boton Iniciar Kinect\n2. El juego es el Gato pero con otro nombre')
    
    def iniciarkinect(self):
        global loop_flag
        loop_flag = True
        kinect.video_frame_ready += self.getColorImage
        kinect.video_stream.open(nui.ImageStreamType.Video, 2, nui.ImageResolution.Resolution640x480, nui.ImageType.Color)
        kinect.skeleton_frame_ready += self.frame_ready
         
        while loop_flag:
            QCoreApplication.processEvents()  # Procesar eventos
            continue
         
    def getColorImage(self, frame):
        global head, lhand, rhand, lhdist, rhdist,imgkinect
        height, width = frame.image.height, frame.image.width   #Obtiene el largo y ancho de la imagen
        imgkinect = numpy.empty((height, width, 4), numpy.uint8)
        frame.image.copy_bits(imgkinect.ctypes.data)    #Copia los bits de la imagen en el arreglo
                             
        for i in range(1, 3):   #Crea las columnas y filas del juego
            x = i * width // 3
            imgkinect = cv2.line(imgkinect, (x, 0), (x, height), (255, 255, 255), 4)
            y = i * height // 3
            imgkinect = cv2.line(imgkinect, (0, y), (width, y), (255, 255, 255), 4)
        
        imgkinect = cv2.circle(imgkinect, tuple(map(int, head)), 15, (255, 255, 0), 5) 
        imgkinect = cv2.circle(imgkinect, tuple(map(int, rhand)), 10, (0, 0, 255), 5)  
        
        # Dibujar las marcas (X u O) en el tablero
        for row, col in self.celdas_marcadas:
            player = self.board[row][col]
            if player == 'X':
                self.dibujar_figuras(row, col, 'X')
            elif player == 'O':
                self.dibujar_figuras(row, col, 'O')
                                
        if abs(rhdist) > 0.4:
            imgkinect = cv2.circle(imgkinect, tuple(map(int, rhand)), 10, (0, 255, 255), 5) 
            # Cambiar la marca en la posición correspondiente del tablero
            col = int(rhand[0] // (width / 3))
            row = int(rhand[1] // (height / 3))

            if 0 <= row < 3 and 0 <= col < 3 and self.board[row][col] == ''and self.tiempo_de_marcar():
                self.board[row][col] = self.jugador_actual
                self.celdas_marcadas.add((row, col))
                self.dibujar_figuras(row, col, self.jugador_actual)
                self.last_marked_time = time.time()  # Actualizar el tiempo de la última casilla marcada
                
                encender_led(row, col)
                
                if self.checar_ganador():
                    parpadear()
                    ganador_msg = f"¡El jugador {self.jugador_actual} ha ganado!"
                    self.msg.setText(ganador_msg)
                    self.close_kinect()
                else:
                    self.turno_jugador()
                    self.msg.setText(f"Turno actual: {self.jugador_actual}")
 
        cv2.imshow('KINECT', imgkinect) 
    
        if cv2.waitKey(1) == 27:  # Tecla esc
            self.close_kinect()
        
    def tiempo_de_marcar(self):
        # Verificar si ha pasado el tiempo suficiente desde la última casilla marcada
        return time.time() - self.last_marked_time >= 3  # 3 segundos de tiempo de retención
    
    def dibujar_figuras(self, row, col, player):
        x1 = int(col * imgkinect.shape[1] / 3)
        y1 = int(row * imgkinect.shape[0] / 3)
        x2 = int((col + 1) * imgkinect.shape[1] / 3)
        y2 = int((row + 1) * imgkinect.shape[0] / 3)

        # Dibujar una X o O según el jugador actual
        if player == 'X':
            cv2.line(imgkinect, (x1, y1), (x2, y2), (0, 255, 0), 5)
            cv2.line(imgkinect, (x1, y2), (x2, y1), (0, 255, 0), 5)

        elif player == 'O':
            cv2.circle(imgkinect, ((x1 + x2) // 2, (y1 + y2) // 2), (y2 - y1) // 2, (255, 0, 0), 5)
            
    def turno_jugador(self):
        # Pasar el turno al siguiente jugador
        if self.jugador_actual == 'X':
            self.jugador_actual = 'O'
        else:
            self.jugador_actual = 'X'
        
    def checar_ganador(self):
        # Verificar filas y columnas
        for i in range(3):
            if self.board[i][0] == self.board[i][1] == self.board[i][2] != '':
                return True  # Hay un ganador en una fila
            if self.board[0][i] == self.board[1][i] == self.board[2][i] != '':
                return True  # Hay un ganador en una columna

        # Verificar diagonales
        if self.board[0][0] == self.board[1][1] == self.board[2][2] != '':
            return True  # Hay un ganador en la diagonal principal
        if self.board[0][2] == self.board[1][1] == self.board[2][0] != '':
            return True  # Hay un ganador en la diagonal secundaria

        return False                    
    
    def frame_ready(self, frame):
        global head, lhand, rhand, lhdist, rhdist
        if frame.SkeletonData is not None:
            for index, skeleton in enumerate(frame.SkeletonData):
                if skeleton.eTrackingState == nui.SkeletonTrackingState.TRACKED:
                    head = nui.SkeletonEngine.skeleton_to_depth_image(skeleton.SkeletonPositions[nui.JointId.Head], 640, 480)
                    lhand = nui.SkeletonEngine.skeleton_to_depth_image(skeleton.SkeletonPositions[nui.JointId.HandLeft], 640, 480)
                    rhand = nui.SkeletonEngine.skeleton_to_depth_image(skeleton.SkeletonPositions[nui.JointId.HandRight], 640, 480)
                    lhdist = skeleton.SkeletonPositions[nui.JointId.Head].z - skeleton.SkeletonPositions[nui.JointId.HandLeft].z
                    rhdist = skeleton.SkeletonPositions[nui.JointId.Head].z - skeleton.SkeletonPositions[nui.JointId.HandRight].z
    
    def close_kinect(self):
        global loop_flag
        loop_flag = False
        close_arduino()
        kinect.close()
        cv2.destroyAllWindows()
    
    def set_foto_jugador(self, ruta_foto_perfil):
        if ruta_foto_perfil:
            pixmap = QPixmap(ruta_foto_perfil)

            pixmap = pixmap.scaled(self.img.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            self.img.setPixmap(pixmap)
            self.img.setScaledContents(True)  # Mantener el aspecto de la imagen



class ConnectServidor(QDialog, Ui_Dialog):
    def __init__(self):
        QDialog.__init__(self)
        loadUi("ConectarServidor.ui", self)
        self.conectar.clicked.connect(self.connected)
        self.coneccion = None
        self.nombre_usuario = None
        self.online = int
    
    def connected(self):
        server = self.servidor.text()
        self.nombre_usuario = self.nombre.text()
        port = self.puerto.text()
        if server and not server.isspace() and port and port.isnumeric():
            self.coneccion = ThreadSocket(server, int(port))
            self.coneccion.start()
            global online, nombre
            online = 1
            nombre = self.nombre_usuario
            QMessageBox.information(self,'Conectado','Conexion establecida')
            ConnectServidor.close(self) 
        
        
        
if __name__ == "__main__":    
    #Servidor
    BUFFER_SIZE = 1024  # Usamos un número pequeño para tener una respuesta rápida
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    connected = False
    #GUI
    app = QtWidgets.QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
    