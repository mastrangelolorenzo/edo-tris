"""EDO-Y - braccio robotico dell'agente IA.

Esegue com.tris.moveY(num) e poi chiama com.tris.movedY(num); esulta per
WINNER-Y, si deprime per WINNER-X, saluta per FLAP. Logica in ../edo-common/edo.py.
"""
from edo import run

if __name__ == "__main__":
    run("Y")
