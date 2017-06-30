FROM vault:0.7.3

RUN apk upgrade --update && \
    apk add openssl iproute2 iptables bash && \
    ln -s /usr/lib/tc/ /lib

COPY ./tls/ca/root_vault.crt /usr/local/share/ca-certificates/root_vault.crt
RUN update-ca-certificates
RUN awk -v cmd='openssl x509 -noout -subject' '/BEGIN/{close(cmd)};{print | cmd}' < /etc/ssl/certs/ca-certificates.crt | grep vault
COPY docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
RUN chmod +x /usr/local/bin/docker-entrypoint.sh
ENTRYPOINT ["docker-entrypoint.sh"]

CMD ["server"]
