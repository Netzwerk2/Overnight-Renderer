FROM debian:buster

RUN apt-get update && \
    apt-get install -y python3 

RUN apt-get update && \
    apt-get install -y git

RUN apt-get update && \
    apt-get install -y libgtk-3-0 python3-gi gir1.2-notify gir1.2-gtk-3.0 libcanberra-gtk3-module

RUN git clone https://github.com/Netzwerk2/Overnight-Render-Manager.git /var/tmp/orm

CMD ["python3", "/var/tmp/orm/pygtk/overnight_renderer.py"]
