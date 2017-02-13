# Run Larva

 gunicorn --reload --preload -k gevent -b 0.0.0.0:8080 -w 8 main:server.app
