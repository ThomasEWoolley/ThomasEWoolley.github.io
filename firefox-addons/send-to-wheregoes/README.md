# Send to WhereGoes: Firefox extension hosting

This directory is dedicated to the **Send to WhereGoes** Firefox extension. It is isolated from the rest of the website. The extension is independent of and not endorsed by WhereGoes.

## Current version

- Version: 1.2.0
- Add-on ID: `send-to-wheregoes@thomasewoolley.github.io`
- Distribution: Mozilla Add-on Developer Hub, unlisted/self-distribution
- Update manifest: https://thomaswoolley.co.uk/firefox-addons/send-to-wheregoes/updates.json
- Privacy notice: https://thomaswoolley.co.uk/firefox-addons/send-to-wheregoes/privacy.html

The initial update manifest deliberately contains an empty `updates` array. **This directory does not contain a signed or installable extension.** Mozilla signing is required for permanent Firefox installation.

## Mozilla signing

Upload the source ZIP for v1.2.0 to https://addons.mozilla.org/developers/ and select unlisted/self-distribution. Download the signed `.xpi` and install it through Firefox's Add-ons Manager. The source ZIP is not a signed add-on.

## How to release an automatic update

1. Increment the add-on's `manifest.json` version, retaining its ID and `browser_specific_settings.gecko.update_url`.
2. Submit the newer source ZIP to Mozilla as a **new version of the same unlisted add-on**.
3. Download the new Mozilla-signed `.xpi`.
4. Add that signed `.xpi` to this directory under a versioned filename.
5. Update `updates.json` **only after** the signed file is publicly accessible, using the format below.
6. Check the manifest and signed XPI URLs over HTTPS.

Example `updates.json` for an eventual v1.2.1:

```json
{
  "addons": {
    "send-to-wheregoes@thomasewoolley.github.io": {
      "updates": [
        {
          "version": "1.2.1",
          "update_link": "https://thomaswoolley.co.uk/firefox-addons/send-to-wheregoes/send-to-wheregoes-1.2.1.xpi"
        }
      ]
    }
  }
}
```

Never link an unsigned `.xpi`. Keep the update manifest HTTPS URL stable. The GitHub Pages repository uses a custom domain (`thomaswoolley.co.uk`); check any redirects and availability before relying on automatic updates.

## Permissions and privacy

The add-on performs a user-triggered hand-off to WhereGoes. It does not intercept browsing or contact the target URLs itself. Its declared personal-data transmission categories are `browsingActivity` and `websiteContent`, as selected URLs can contain sensitive information. The external service's privacy policies apply.

## Maintenance caution

This folder lives within the existing GitHub Pages site because the linked GitHub integration supports writing to an existing repository but not creating a new repository. Do not modify the website root files, `CNAME`, publishing configuration or unrelated pages to maintain this add-on.

## Pre-submission verification

The Mozilla submission package must contain `manifest.json` at the ZIP root and must point `browser_specific_settings.gecko.update_url` to the custom domain URL above. The add-on ID remains `send-to-wheregoes@thomasewoolley.github.io` and must match the sole key in `updates.json`.

Opening a GitHub repository link confirms the files exist in GitHub, **not** that GitHub Pages is serving their public HTTPS URLs. Before submitting, open the two URLs above in Firefox and check that `updates.json` displays JSON and `privacy.html` displays the notice. If either fails, the update mechanism is not yet verified.

The initial Firefox package requires Mozilla signing. No signed `.xpi` or live-update release has been published in this folder.
