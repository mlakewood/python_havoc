storage "consul" {
  address = "consul_agent_1:8500"
  redirect_addr = "http://127.0.0.1:1235"
  path = "vault"
}

listener "tcp" {
  address     = "0.0.0.0:1235"
  tls_disable = 1
}
