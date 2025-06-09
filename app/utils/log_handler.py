import logging
# Import send_log_to_frontend carefully or pass emitter
# For this version, send_log_to_frontend will be modified to accept sio_instance

class SocketIOHandler(logging.Handler):
    def __init__(self, level=logging.NOTSET):
        super().__init__(level)
        self.formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        self.sio_emitter = None # To be set from app

    def set_emitter(self, emitter_func):
        """Sets the function to be used for emitting logs."""
        self.sio_emitter = emitter_func

    def emit(self, record):
        # Avoid logging socketio internal messages or our own handler's attempts to log
        if record.name.startswith('socketio') or \
           record.name.startswith('engineio') or \
           record.name == 'app.utils.log_handler': # Avoid self-logging
            return

        if not self.sio_emitter:
            # print("SocketIO emitter not set for SocketIOHandler.") # Debug only
            return

        try:
            log_entry = self.format(record)
            self.sio_emitter(log_entry)
        except RecursionError:
            # print("RecursionError in SocketIOHandler. Logging to console instead.") # Debug only
            pass
        except Exception as e:
            # print(f"Error in SocketIOHandler: {e}") # Debug only
            self.handleError(record)
