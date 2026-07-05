
# [CFT Whitelisting Requirements](https://docs.developer.tech.gov.sg/docs/cft-additional-docs/whitelisting?id=cft-whitelisting-requirements)

To ensure connectivity between CFT and agency systems, IP whitelisting is required in two places:

* **On CFT side:** For agencies connecting to our servers. Refer to [Whitelisting requirements](https://docs.developer.tech.gov.sg/docs/cft-additional-docs/whitelisting?id=whitelisting-requirements).
* **On agency side:** For agencies to [configure their firewalls](https://docs.developer.tech.gov.sg/docs/cft-additional-docs/firewall-clearance) to allow traffic from CFT IPs.

This diagram illustrates the various connections between CFT and Tenant systems and zones.

![firewall-clearances](https://docs.developer.tech.gov.sg/docs/cft-additional-docs/assets/firewall-clearances.png)

## [Whitelisting requirements](https://docs.developer.tech.gov.sg/docs/cft-additional-docs/whitelisting?id=whitelisting-requirements)

Refer to the whitelisting requirements for the CFT systems you are connecting to.

### [CFT HTTPS Server](https://docs.developer.tech.gov.sg/docs/cft-additional-docs/whitelisting?id=cft-https-server)

> If your system is an HTTPS Client connecting to CFT HTTPS Server.

* **Internet** : No whitelisting required.
* **Intranet** : No whitelisting required. However, if you are on GCC2.0 on AWS, [configure static routes via GCCI Common Services Transit Gateway](https://docs.developer.tech.gov.sg/docs/cft-additional-docs/tgw/configure-routes).

### [CFT SFTP Server](https://docs.developer.tech.gov.sg/docs/cft-additional-docs/whitelisting?id=cft-sftp-server)

> If your system is an SFTP Client connecting to CFT SFTP Server.

* **Internet** : Submit SR via [CFT-SM](https://go.gov.sg/cft-sm) to whitelist your agency’s SFTP client.
* **Intranet** : No whitelisting required. However, if you are on GCC2.0 on AWS, [configure static routes via GCCI Common Services Transit Gateway](https://docs.developer.tech.gov.sg/docs/cft-additional-docs/tgw/configure-routes).

### [CFT SFTP Client](https://docs.developer.tech.gov.sg/docs/cft-additional-docs/whitelisting?id=cft-sftp-client)

> If your system is an SFTP Server that the CFT SFTP Client connects to.

* **Internet** : Submit SR via [CFT-SM](https://go.gov.sg/cft-sm) to whitelist your agency’s SFTP server.
* **Intranet** : No whitelisting required. However, if you are on GCC2.0 on AWS, [configure static routes via GCCI Common Services Transit Gateway](https://docs.developer.tech.gov.sg/docs/cft-additional-docs/tgw/configure-routes).

### [CFT Notification (Webhooks) Server](https://docs.developer.tech.gov.sg/docs/cft-additional-docs/whitelisting?id=cft-notification-webhooks-server)

* **Internet** : No whitelisting required.
* **Intranet** : No whitelisting required.

## [What’s next](https://docs.developer.tech.gov.sg/docs/cft-additional-docs/whitelisting?id=whats-next)

* You may need to allow or [whitelist CFT endpoints on your Tenant/Agency Firewalls](https://docs.developer.tech.gov.sg/docs/cft-additional-docs/firewall-clearance).
* To validate the firewall rules  **from tenant system to CFT intranet** , refer to:
  * [HTTPS Firewall Rules Testing (Intranet)](https://docs.developer.tech.gov.sg/docs/cft-additional-docs/https-firewall)
  * [SFTP Client Firewall Rules Testing (Intranet)](https://docs.developer.tech.gov.sg/docs/cft-additional-docs/sftp-firewall)
