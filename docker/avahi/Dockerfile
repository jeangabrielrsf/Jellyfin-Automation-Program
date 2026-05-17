FROM debian:bookworm-slim

RUN apt-get update && \
    apt-get install -y --no-install-recommends avahi-daemon avahi-utils && \
    rm -rf /var/lib/apt/lists/* && \
    mkdir -p /etc/avahi/services

COPY avahi-daemon.conf /etc/avahi/avahi-daemon.conf
COPY jellyfin.service /etc/avahi/services/jellyfin.service

EXPOSE 5353/udp

CMD ["avahi-daemon", "--no-chroot", "--no-drop-root"]
