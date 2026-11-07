# Signed update feed

The app never installs updates automatically. The manual **Check for updates on GitHub** action reads a
small static feed from GitHub Pages and verifies its ECDSA P-256 signature before looking at the version.

## Public endpoints

- Feed: <https://vvg-web.github.io/cornetta-en/update/feed.json>
- Signature: <https://vvg-web.github.io/cornetta-en/update/feed.json.sig>
- Public key: the `updateFeedPublicKey` / `UpdateFeedPublicKey` constants in the Mac and Windows app
- Private key: `~/.config/cornetta/update-feed-key.pem` (outside the repository, mode `600`)

The private key must be backed up in a password manager. If it is lost, existing apps cannot trust a new
feed. A future release must then embed a new public key.

## Feed format

The signature covers the exact bytes of `feed.json`. Any whitespace change requires a new signature.

```json
{"schema":1,"version":"0.7.0","release_url":"https://github.com/VVG-web/cornetta-en/releases/tag/v0.7.0","published":"2026-11-07","mac":{"filename":"Cornetta-0.7.0.dmg","sha256":"..."},"windows":{"filename":"CornettaSetup.exe","sha256":"..."}}
```

Both apps verify the signature and require `schema == 1`. The release URL must point to a release in
`VVG-web/cornetta-en`. A bad signature or an unknown release URL never produces an update notice.

## Signing and checking

```bash
scripts/sign-feed.py --check-key
scripts/sign-feed.py --sign site/update/feed.json
scripts/sign-feed.py --verify site/update/feed.json site/update/feed.json.sig \
  --public-key-base64 "$(scripts/sign-feed.py --public-key)"
python3 -m unittest discover -s scripts/tests -p 'test_sign_feed.py'
```

`scripts/sign-feed.py` refuses a private key inside the repository, a key readable by other users, and a
signature that does not verify immediately after signing.

## Release procedure

1. Build the DMG and Windows installer.
2. Compute SHA-256 for both assets.
3. Update `site/update/feed.json` with the new version, release URL, and hashes.
4. Run `scripts/sign-feed.py --sign site/update/feed.json`.
5. Run the Python tests and `./scripts/check.sh`.
6. Commit and push. The Pages workflow publishes the feed.
7. Create the GitHub Release with the assets.
8. Verify the public feed, signature, release URL, and hashes.

The release must be published after the feed is signed. A brief window where the feed mentions a release
that is not yet public is acceptable; a release without a matching signed feed is not.

## Key rotation

Rotating the key requires a release that embeds the new public key. Sign the new feed with both keys
during the transition only if the app has an explicit dual-key verification path. The current app has a
single key, so rotation is a breaking release.
