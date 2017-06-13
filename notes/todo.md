
# TO DO

- [x] fix restclient
- [ ] fix tests inside container
- [ ] FIXME: get it back / if False
- [ ] review TODO / FIXME
- [ ] fix restclient bash open
- [ ] and generalize with other 'run' services like sqladmin or swaggerui

- [ ] Bug in authentication:

```bash

(psycopg2.ProgrammingError) column external_accounts.irodsuser does not exist\nLINE 1: ...al_accounts.user_id AS external_accounts_user_id, external_a...\n ^\n [SQL: 'SELECT external_accounts.username AS external_accounts_username, external_accounts.token AS external_accounts_token, external_accounts.token_expiration AS external_accounts_token_expiration, external_accounts.email AS external_accounts_email, external_accounts.certificate_cn AS external_accounts_certificate_cn, external_accounts.certificate_dn AS external_accounts_certificate_dn, external_accounts.proxyfile AS external_accounts_proxyfile, external_accounts.description AS external_accounts_description, external_accounts.user_id AS external_accounts_user_id, external_accounts.irodsuser AS external_accounts_irodsuser, external_accounts.unity AS external_accounts_unity \\nFROM external_accounts \\nWHERE EXISTS (SELECT 1 \\nFROM \"user\" \\nWHERE \"user\".id = external_accounts.user_id AND \"user\".id = %(id_1)s) \\n LIMIT %(param_1)s'] [parameters: {'id_1': 1, 'param_1': 1}]

```
