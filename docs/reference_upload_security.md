# Reference upload security (H2.6A-R)

- MIME sniffing (PNG/JPEG/WebP); extension ignored.
- Safe filename sanitization.
- Decode validation via Pillow; animated frames rejected.
- EXIF stripped via re-encode / `exif_transpose`.
- Checksum (sha256); duplicates rejected per owner.
- Owner-scoped storage under `REFERENCE_IMAGE_STORAGE_DIR`.
- Authenticated content endpoint only; no public URLs.
- Consent required for person subject types.
