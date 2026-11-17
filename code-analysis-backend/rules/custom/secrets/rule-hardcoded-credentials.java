class Config {
    // ruleid: custom_secrets_hardcoded-credentials-java
    private static final String DB_PASSWORD = "S3cureHorse42";
    // ok: custom_secrets_hardcoded-credentials-java
    private static final String PASSWORD_ENV = "DB_PASSWORD_VAR_NAME_X";
    // ok: custom_secrets_hardcoded-credentials-java
    String password = "changeme";
}
