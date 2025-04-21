from app import *

if __name__ == "__main__":
    socketio.run(
        app,
        host='0.0.0.0',
        port=8088,
        use_reloader=True
    )