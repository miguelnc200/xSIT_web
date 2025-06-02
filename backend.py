from flask import Flask, request, jsonify, render_template
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Polygon, Circle
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
from matplotlib.path import Path
import math
from flask_cors import CORS


app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

def calcular_tiempo_llegada(pos_balon, velocidad_balon, pos_jugador):
    """Calcula el tiempo que tarda el balón en llegar a la posición del jugador"""
    distancia = math.sqrt((pos_balon[0] - pos_jugador[0])**2 + (pos_balon[1] - pos_jugador[1])**2)
    tiempo = distancia / (velocidad_balon * 1000 / 3600)  # Convertir km/h a m/s
    return tiempo

def calcular_radio_efectivo(tiempo_llegada, radio_base, tiempo_reaccion):
    """Ajusta el radio en función del tiempo de llegada vs tiempo de reacción"""
    factor = tiempo_llegada / tiempo_reaccion
    return radio_base * factor

def calcular_xsit(pos_balon, portero, jugadores, velocidad_balon):
    fig, ax = plt.subplots(figsize=(10, 6), dpi=100)
    ax.set_xlim(0, 120)
    ax.set_ylim(0, 75)
    ax.set_xticks([])  
    ax.set_yticks([])  
    ax.set_frame_on(False)
    ax.set_facecolor('white')

    # Goal
    porteria = [(120, 32), (120, 43)] if pos_balon[0] >= 60 else [(0, 32), (0, 43)]
    
    # Triangle
    vertices_triangulo = np.array([pos_balon, porteria[0], porteria[1]])
    triangulo = Polygon(vertices_triangulo, closed=True, edgecolor='red', facecolor=(1, 0, 0), linewidth=2)
    ax.add_patch(triangulo)

    # Ball
    ax.scatter(*pos_balon, color='red', s=100, label="Ball")

    # Players with circle that change with speed of the ball
    for jugador in jugadores:
        tiempo = calcular_tiempo_llegada(pos_balon, velocidad_balon, jugador)
        radio = calcular_radio_efectivo(tiempo, radio_base=1.5, tiempo_reaccion = 0.25 )
        circulo = Circle(jugador, radius=radio, color='blue', alpha=0.5)
        ax.add_patch(circulo)

    # GK with the circle
    tiempo_portero = calcular_tiempo_llegada(pos_balon, velocidad_balon, portero)
    radio_portero = calcular_radio_efectivo(tiempo_portero, radio_base=2.0, tiempo_reaccion= 0.23)
    por = Circle(portero, radius=radio_portero, color='green', alpha=0.5, label="Goalkeeper")
    ax.add_patch(por)

    plt.legend()

    # Procesing the white area
    canvas = FigureCanvas(fig)
    canvas.draw()

    w, h = canvas.get_width_height()
    image = np.frombuffer(canvas.buffer_rgba(), dtype='uint8').reshape((h, w, 4))
    plt.close(fig)

    transform = ax.transData
    pix_vertices = transform.transform(vertices_triangulo)
    pix_vertices[:, 1] = h - pix_vertices[:, 1]

    path = Path(pix_vertices)
    Y, X = np.mgrid[0:h, 0:w]
    coords = np.vstack((X.ravel(), Y.ravel())).T
    mask = path.contains_points(coords).reshape((h, w))

    colores_dentro = image[mask]
    colores_redondeados = (colores_dentro[:,3] // 10) * 10
    colores_unicos, counts = np.unique(colores_redondeados, axis=0, return_counts=True)

    for color, count in zip(colores_unicos, counts):
        if np.all(np.abs(color - [250, 0, 0]) <= 5):
            porcentaje = count / np.sum(counts)
            return porcentaje
    return 0.0

@app.route('/calculate_xsit', methods=['POST'])
def calculate_xsit_route():
    data = request.json
    print("Datos recibidos:", data) 
    pos_balon = data.get("pos_balon")  # [x, y]
    velocidad_balon = data.get("velocidad_balon")  # en km/h
    portero = data.get("portero")  # [x, y]
    jugadores = data.get("jugadores")  # lista de [x, y]

    if not pos_balon or not velocidad_balon or not portero or not jugadores:
        return jsonify({"error": "Faltan datos"}), 400

    xsit_value = calcular_xsit(pos_balon, portero, jugadores, velocidad_balon)
    return jsonify({"xsit": xsit_value})

@app.route("/")
def index():
    return render_template("xSIT.html") 

if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
