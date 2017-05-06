backend "consul" {
  address = "consul_agent_1:8500"
}

listener "tcp" {
  address     = "0.0.0.0:8200"
  tls_disable = 1
}
