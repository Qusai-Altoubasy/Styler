# infrastructure

Infrastructure as code (database, storage, hosting). AWS CDK (TypeScript). Not started yet.

## Phase 5 requirements

### The server's IAM key on the images bucket

Lightsail has no IAM roles, so the API uses an IAM user's key from the server's env file (`S3_ACCESS_KEY_ID`, `S3_SECRET_ACCESS_KEY`). On the images bucket it needs exactly:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["s3:ListBucket"],
      "Resource": "arn:aws:s3:::<images bucket>"
    },
    {
      "Effect": "Allow",
      "Action": ["s3:GetObject", "s3:PutObject", "s3:DeleteObject"],
      "Resource": [
        "arn:aws:s3:::<images bucket>/tmp/*",
        "arn:aws:s3:::<images bucket>/media/*"
      ]
    }
  ]
}
```

- **`s3:ListBucket` is required.** Without it, S3 answers `403` instead of `404` for an object that does not exist. The API then fails every save of an expired upload with `500 storage_misconfigured` (and logs the missing permission) instead of telling the manager to upload again (`422 image_not_uploaded`).
- Nothing outside `tmp/*` and `media/*`: the key cannot read or delete anything else in the bucket.
- The backups folder gets its own statement when the nightly backup is added.
- After deploying, check it: save a product with an upload older than a day (or a made-up `tmp/` key). The answer must be `422 image_not_uploaded`, not `500`.

