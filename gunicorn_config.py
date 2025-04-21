# gunicorn_config.py

import multiprocessing
import os


proc_name = "boards"


bind = [
    '0.0.0.0:8088'
]
# bind = 'unix:/tmp/gunicorn.sock'
workers = 1
worker_class = "eventlet"
threads = 2  # Number of threads per worker
timeout = 120  # Kill workers if unresponsive for 120 sec
loglevel = "info"  # Log level (debug, info, warning, error, critical)
keepalive = 10


# SSL Certificates
# certfile = "cert/cert.pem"
# keyfile = "cert/acme.com.key"
# dhparam = "cert/dhparam4096.pem"

# # Logging: Send to both terminal & file
accesslog = "-"  # Send access logs to stdout (terminal)
errorlog = "-"   # Send error logs to stderr (terminal)


accesslog = "../../log/gunicorn_access.log"
errorlog = "../../log/gunicorn_error.log"
# # loglevel = "debug"
# capture_output = True  # Ensures all logs are written
# enable_stdio_inheritance = True  # Captures worker output


# Also log to files
# access_logfile = "../../log/gunicorn_access.log"
# error_logfile = "../../log/gunicorn_error.log"


# anti-spam
limit_request_line = 4094  # Max request line length
limit_request_fields = 100  # Max number of header