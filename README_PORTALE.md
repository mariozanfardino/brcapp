# BrCapp 2.0 — Autenticazione OAuth, Portale Paziente, Notifiche

## Cosa c'è di nuovo

| Area | Implementazione |
|---|---|
| **Autenticazione** | OAuth 2.0 / OpenID Connect (Authlib): Authorization Code + **PKCE S256**, `state` e `nonce`, validazione dell'`id_token`. Provider: Google, Microsoft Entra ID, qualsiasi IdP OIDC (Keycloak aziendale, gateway SPID/CIE). Login locale con password come alternativa. |
| **Sessioni** | Cookie Flask firmato, `HttpOnly`, `SameSite=Lax`, `Secure` in HTTPS, scadenza 8 h, rotazione al login. L'identità non è più affidata a `dcc.Store` nel browser. |
| **Portale paziente** | `/patient/portal` con tre sezioni: **Anagrafica**, **Cartella clinica** (referti e valori di laboratorio, solo quelli rilasciati dal medico), **Appuntamenti** (prossimi/storico, download `.ics`). |
| **Registrazione** | Codice paziente + **codice di attivazione monouso** rilasciato dalla struttura (pagina *PIN Pazienti*), consenso privacy obbligatorio, consenso email opt-in, verifica email con link firmato (48 h). Anche via OAuth. |
| **Notifiche** | Email alla prenotazione e il **giorno prima** (dalle 8:00), con allegato calendario `.ics`; email di annullamento. Idempotenti, registrate in `email_log`. |
| **Staff** | Nuova pagina **Agenda & Referti**: prenotazione/annullamento appuntamenti, pubblicazione referti nel portale, registro email e audit trail. |
| **Audit** | Tabella `audit_log`: login, accessi al portale, consultazione referti, prenotazioni, pubblicazioni, invii email. |

## Account di test (creati automaticamente)

| Chi | Accesso | Note |
|---|---|---|
| Staff | `admin / admin123` · `dott_rossi / clinico123` | Agenda & Referti nel menu |
| **PT-TEST1** Maria Rossi | `maria.rossi.test@example.com` / `Portale!2026` | 7 referti (+1 non rilasciato, invisibile), appuntamento **domani** per testare il promemoria |
| **PT-TEST2** Anna Esposito | registrazione da `/patient/register` con codice attivazione **482913** | per provare il flusso di primo accesso |

Per ricevere davvero le email di test imposta `BRCAPP_TEST_PATIENT_EMAIL=tua@email` **prima** del primo avvio (DB vuoto).
Senza SMTP le email sono salvate come `.eml` in `outbox/` accanto al database: si aprono con qualsiasi client di posta.

## Configurazione

Copia `.env.example` e valorizza le variabili (su Render: *Environment*). Minimo indispensabile in produzione:
`BRCAPP_SECRET_KEY`, `BRCAPP_BASE_URL`, `SMTP_*`, `MAIL_FROM`.

### OAuth — Google
1. Google Cloud Console → *APIs & Services* → *Credentials* → *OAuth client ID* (Web application).
2. Authorized redirect URI: `https://<tuo-dominio>/auth/callback/google`
3. Imposta `GOOGLE_CLIENT_ID` e `GOOGLE_CLIENT_SECRET`. Il pulsante compare da solo nelle pagine di login.

Microsoft: redirect `…/auth/callback/microsoft`, per lo staff usa il `MICROSOFT_TENANT_ID` aziendale.
OIDC generico (Keycloak, SPID/CIE tramite gateway): `OIDC_ISSUER` + client → redirect `…/auth/callback/oidc`.

**Staff:** nessun auto-provisioning. Un operatore entra via OAuth solo se esiste già un utente con la stessa email (creato dall'admin); al primo accesso l'identità (`sub`) viene collegata.
**Pazienti:** se l'identità OAuth non è collegata, il paziente viene portato alla registrazione e deve inserire codice paziente + codice di attivazione.

### Email
Qualsiasi SMTP con STARTTLS (587) o SSL (465): Brevo, Mailgun, SendGrid, Amazon SES, server aziendale.
Configura SPF/DKIM sul dominio del mittente per evitare lo spam.

### Promemoria
- Lo scheduler interno controlla ogni 30 minuti gli appuntamenti di domani.
- **Render free sospende il processo dopo 15 minuti di inattività**: in quel caso lo scheduler non gira. Aggiungi un cron esterno (Render Cron Job o cron-job.org) ogni ora:
  ```
  curl -X POST https://<tuo-dominio>/tasks/reminders -H "X-Cron-Token: $BRCAPP_CRON_TOKEN"
  ```
  L'invio è idempotente: più esecuzioni non producono duplicati.
- Con più worker (gunicorn) disattiva lo scheduler interno (`BRCAPP_SCHEDULER=0`) e usa solo il cron.

## Scelte di conformità (GDPR / sanità)
- **Minimizzazione**: le email non contengono dati clinici (né prestazione, né referti): solo data, ora e sede. I dettagli si leggono nel portale dopo l'autenticazione.
- **Pseudonimizzazione**: nelle viste staff il paziente compare col solo codice; nome e codice fiscale sono visibili al paziente stesso.
- **Rilascio referti**: un referto è visibile al paziente solo dopo la pubblicazione esplicita da parte del medico.
- **Consensi** con data (`consent_privacy_at`) e revocabili (consenso email modificabile dal portale).
- **Anti-enumerazione**: messaggi identici per email/codici inesistenti, 404 sui file di altri pazienti.
- **Brute force**: blocco account dopo 5 tentativi per 15 minuti; password ≥ 10 caratteri (NIST SP 800-63B), hash scrypt.
- **Header**: HSTS (in HTTPS), `X-Frame-Options: DENY`, `nosniff`, `Cache-Control: no-store` sulle pagine con dati sanitari.

## Limiti noti e prossimi passi
- **Persistenza**: su Render free `/tmp/breastcare.db` si azzera a ogni riavvio (account, appuntamenti e referti compresi). Per un uso reale serve un database persistente (PostgreSQL gestito).
- **MFA**: non implementata per il login con password; con OAuth/SPID si eredita quella del provider. Per lo staff è consigliato usare solo SSO aziendale.
- **Firma digitale e conservazione** dei referti (CAD/AgID) e integrazione con FSE non sono incluse: qui i referti sono testi strutturati inseriti dallo staff.
- La revisione DPO/DPIA è necessaria prima di trattare dati reali di pazienti.

## Test
```
python tests/e2e_portal.py
```
Esegue ~110 verifiche end-to-end su DB temporaneo: controllo accessi, login staff/paziente, lockout, registrazione e verifica email, reset password, OAuth simulato, prenotazione con email, promemoria idempotente, isolamento dei dati tra pazienti, scheda paziente, XAI.

## Modello di classificazione (v22)

- `models_weka/Adaboost.model` contiene **AdaBoostM1 (10 decision stump) + l'header del dataset**.
- `models_weka/brcam_adaboost.json` è lo stesso modello esportato a piena precisione: l'app lo esegue
  in Python puro, quindi il **modello originale gira anche su Render** (senza Java).
  Equivalenza con WEKA verificata su 3000 casi casuali (differenza ≤ 1e-16): `python tests/test_model_equivalence.py`.
- Se aggiorni `Adaboost.model`, rigenera il JSON: `python scripts/export_weka_model.py` (serve JDK + python-weka-wrapper3).
- La codifica dei valori segue l'header del modello: BI-RADS `E0–E5`, citologia `C0–C5`, focalità `si/no/Bil:…`.
  `ricostruzione` nel training vale solo `si`: un `no` è trattato come dato mancante (comportamento WEKA standard).
- La pagina XAI mostra le 10 regole e un'importanza calcolata dai pesi reali: il modello usa 7 feature su 15.
