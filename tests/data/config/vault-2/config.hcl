storage "consul" {
  address = "consul_agent_2:8500"
  cluster_addr = "https://vault_vault_2_1:8200"
  path = "vault"
}

listener "tcp" {
  address     = "vault_vault_2_1:8200"
  tls_cert_file =  "/vault/tls/vault.crt"
  tls_key_file = "/vault/tls/vault.key"
}
