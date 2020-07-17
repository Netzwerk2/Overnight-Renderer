FROM debian:buster

RUN apt-get update && \
    apt-get install -y python3 #python-gobject libgtk-3-0

RUN apt-get install -y gtk+3.0
RUN apt-get install -y git
RUN apt-get install -y python3-gi
RUN apt-get install -y gir1.2-notify
#RUN apt-get install -y gobject-introspection
#RUN apt-get install -y gir1.2-gtk-3.0

RUN git clone https://github.com/Netzwerk2/Overnight-Render-Manager.git /var/tmp/orm

CMD ["python3", "/var/tmp/orm/pygtk/overnight_renderer.py"]
