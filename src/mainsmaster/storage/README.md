# Artifact storage

`base.py` defines the artifact-store contract. `local.py` supports development and tests. `s3.py` uses the standard S3 API for Cloudflare R2, MinIO, AWS S3, or another compatible service. Production settings reject local-only artifact storage.

The pipeline keeps PDF rendering on ephemeral local disk, removes rendered page images before publishing to S3, uploads durable inputs/results, and records the artifact prefix in private `_system` report metadata.
