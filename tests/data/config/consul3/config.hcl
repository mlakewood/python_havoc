{
  "log_level": "INFO",
  "node_name": "consul3",
  "server": true,
  "disable_update_check": true,
  "start_join": ["consul1", "consul2", "consul3", "consul4", "consul5"],
  "bootstrap-expect": 2,
}
