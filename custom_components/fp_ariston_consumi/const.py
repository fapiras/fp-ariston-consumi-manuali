"""Manual-only Ariston report reader constants."""
DOMAIN = "fp_ariston_consumi"
UPSTREAM_DOMAIN = "ariston_net"
LEGACY_REPORT_PATH = "/velis/reports/{gateway}?usages=Dhw&appId=com.remotethermo.velis"
PERIOD_KEYS = ("day_kwh", "week_kwh", "month_kwh", "year_kwh")
