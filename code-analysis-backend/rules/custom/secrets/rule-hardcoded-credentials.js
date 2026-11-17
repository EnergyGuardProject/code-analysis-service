// ruleid: custom_secrets_hardcoded-credentials-js
const dbPassword = "S3cureHorse42";
// ruleid: custom_secrets_hardcoded-credentials-js
const config = { apiKey: "k9f3a7d2c81b" };
// ruleid: custom_secrets_hardcoded-credentials-js
const headers = { "client_secret": "z8q1w2e3r4t5" };
// ok: custom_secrets_hardcoded-credentials-js
const fromEnv = process.env.DB_PASSWORD;
// ok: custom_secrets_hardcoded-credentials-js
const placeholder = { password: "<password>" };
// ok: custom_secrets_hardcoded-credentials-js
const tokenType = "Bearer";
