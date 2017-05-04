backend "consul" {
  address = "consul_agent_1:8500"
}

listener "tcp" {
  address     = "0.0.0.0:1235"
  tls_disable = 1
}
