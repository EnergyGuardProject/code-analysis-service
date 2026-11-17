import os

# ruleid: custom_secrets_hardcoded-credentials
db_password = "S3cureHorse42"
# ruleid: custom_secrets_hardcoded-credentials
connect(host="db", user="app", password="n0t-a-real-one")
# ruleid: custom_secrets_hardcoded-credentials
settings = {"api_key": "k9f3a7d2c81b"}
# ok: custom_secrets_hardcoded-credentials
db_password = os.environ["DB_PASSWORD"]
# ok: custom_secrets_hardcoded-credentials
password = "<password>"
# ok: custom_secrets_hardcoded-credentials
password = "changeme"
# ok: custom_secrets_hardcoded-credentials
token_type = "Bearer"
