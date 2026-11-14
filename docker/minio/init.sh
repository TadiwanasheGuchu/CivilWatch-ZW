#!/bin/sh
# One-off setup for local MinIO: a private media bucket and a least-privilege
# account for the API (read/write objects in that bucket only).
set -eu

: "${MINIO_ROOT_USER:?}" "${MINIO_ROOT_PASSWORD:?}" "${STORAGE_ACCESS_KEY_ID:?}" "${STORAGE_SECRET_ACCESS_KEY:?}"
BUCKET="${STORAGE_BUCKET:-civicwatch-media}"

mc alias set local http://minio:9000 "$MINIO_ROOT_USER" "$MINIO_ROOT_PASSWORD"
mc mb --ignore-existing "local/$BUCKET"
# Never public: photos are only served through short-lived signed URLs.
mc anonymous set none "local/$BUCKET"

cat > /tmp/api-policy.json <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["s3:GetObject", "s3:PutObject", "s3:DeleteObject"],
      "Resource": ["arn:aws:s3:::${BUCKET}/*"]
    },
    {
      "Effect": "Allow",
      "Action": ["s3:ListBucket", "s3:GetBucketLocation"],
      "Resource": ["arn:aws:s3:::${BUCKET}"]
    }
  ]
}
EOF
mc admin policy create local civicwatch-api /tmp/api-policy.json 2>/dev/null || true
mc admin user add local "$STORAGE_ACCESS_KEY_ID" "$STORAGE_SECRET_ACCESS_KEY"
mc admin policy attach local civicwatch-api --user "$STORAGE_ACCESS_KEY_ID" 2>/dev/null || true
echo "MinIO ready: bucket $BUCKET is private"
