FROM alpine:3.21

RUN apk add --no-cache avahi

COPY avahi-daemon.conf /etc/avahi/avahi-daemon.conf
COPY jellyfin.service /etc/avahi/services/jellyfin.service

EXPOSE 5353/udp

CMD ["avahi-daemon", "--no-chroot", "--no-drop-root"]
