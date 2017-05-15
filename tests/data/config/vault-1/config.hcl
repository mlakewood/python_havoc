storage "consul" {
  address = "consul_agent_1:8500"
  path = "vault"
  redirect_addr = "http://127.0.0.1:1234"
}

listener "tcp" {
  address     = "0.0.0.0:1234"
  tls_disable = 1
}
