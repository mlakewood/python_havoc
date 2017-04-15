FROM consul:0.8.0

RUN apk upgrade --update && \
    apk add iproute2 iptables bash && \
    ln -s /usr/lib/tc/ /lib
