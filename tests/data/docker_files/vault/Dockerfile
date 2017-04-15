FROM vault:0.7.0

RUN apk upgrade --update && \
    apk add iproute2 iptables bash && \
    ln -s /usr/lib/tc/ /lib

COPY docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
RUN chmod +x /usr/local/bin/docker-entrypoint.sh
ENTRYPOINT ["docker-entrypoint.sh"]

CMD ["server"]
