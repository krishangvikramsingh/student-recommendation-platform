# Security policy

Please report vulnerabilities privately through GitHub's "Report a vulnerability" button
(Security tab) rather than a public issue. You will get a reply within a few days.

What the app does today: scrypt password hashing, single-use hashed email tokens, `HttpOnly` +
`SameSite=Strict` session cookies, CSRF checks, rate limiting, security headers, and parameterised SQL.
Known limits (sessions and rate-limit counters live in memory; mail is console-only unless SMTP is
configured) are listed in the README.
