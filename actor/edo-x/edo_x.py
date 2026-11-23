"""EDO-X - braccio robotico dell'umano.

Esegue com.tris.moveX(num) e poi chiama com.tris.movedX(num); esulta per
WINNER-X, si deprime per WINNER-Y, saluta per FLAP. Logica in ../edo-common/edo.py.
"""
from edo import run

if __name__ == "__main__":
    run("X")
