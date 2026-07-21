# U12 parent invitation deployment contract

U12 uses Firebase Authentication's email-link sign-in as the real email
verification step. No OTP, password hash, parent link, verifier, or recipient
email is stored or handled by a Flutter client.

## Required one-time configuration

1. Enable **Email link (passwordless sign-in)** and **Email/password** in
   Firebase Authentication. Add `logic-oasis-fyp.web.app` to the authorized
   domains list.
2. Create the two Secret Manager values outside Git. The first is a long random
   HMAC key; the second is the approved SMTP/provider credential.

   ```powershell
   firebase functions:secrets:set PARENT_INVITATION_EMAIL_HMAC_KEY
   firebase functions:secrets:set PARENT_INVITATION_SMTP_PASSWORD
   ```

3. Set the non-secret Functions configuration for the approved mail provider:
   `PARENT_INVITATION_CONTINUE_URL=https://logic-oasis-fyp.web.app/parent-invitation`,
   `PARENT_INVITATION_LINK_DOMAIN=logic-oasis-fyp.web.app`,
   `PARENT_INVITATION_ANDROID_PACKAGE=com.example.logic_oasis`,
   `PARENT_INVITATION_SMTP_HOST`, `PARENT_INVITATION_SMTP_PORT`,
   `PARENT_INVITATION_SMTP_USERNAME`, and `PARENT_INVITATION_SMTP_FROM`.
   Values must be supplied through the deployment environment, never a tracked
   `.env` file.
4. Deploy the individual-secret IAM bindings before Functions:

   ```powershell
   python tools/deploy_parent_invitation_iam.py --deployer-member user:YOUR_DEPLOYER_EMAIL --apply
   firebase deploy --only functions,firestore:rules
   ```

5. Publish `https://logic-oasis-fyp.web.app/.well-known/assetlinks.json` with
   the production Android signing certificate SHA-256 and package name
   `com.example.logic_oasis`. Its relation must be
   `delegate_permission/common.handle_all_urls`. Then deploy Hosting. Until this
file is live, Android can still open the browser link but cannot complete
automatic verified-app routing.

> The current Android release build is explicitly signed with the debug key.
> The checked-in asset link therefore supports the present build only. Replace
> its fingerprint before any real release signing key is introduced.

## Production validation

Use disposable student and parent Firebase accounts. A student sends an invite;
the parent opens the email on their own device, signs in with that same inbox,
accepts, sets a confirmed password, and sees only linked safe projections.
Repeat with the wrong inbox, expired/replayed link, revoked parent account, and
unlinked parent account: each must be denied. Confirm Firestore has no raw
email, email link, or verifier (only HMAC/hash values) in
`parentLinkInvitations`, and verify direct client reads/writes remain denied.
