# Free Domain Checker

A Docker-based domain availability checker that monitors a list of domains and sends email notifications when domains become available. Particularly optimized for German (.de) domains but works with any domain extension.

## Features

- 🔍 **Domain Availability Checking**: Uses whois and DNS resolution to check domain availability
- 📧 **Email Notifications**: Sends email alerts when domains become available
- 🐳 **Docker Ready**: Fully containerized for easy deployment
- ⚙️ **Environment Configuration**: All settings via environment variables
- 🔄 **Scheduled Checks**: Configurable check intervals or one-time runs
- 📝 **Comprehensive Logging**: Detailed logs for monitoring and debugging
- 🔒 **Security**: Runs as non-root user in container

## Quick Start

1. **Clone or copy the files to your server**

2. **Copy and configure environment variables:**
   ```bash
   cp .env.example .env
   # Edit .env with your domains and SMTP settings
   ```

3. **Run with Docker Compose:**
   ```bash
   docker-compose up -d
   ```

## Configuration

### Environment Variables

Copy `.env.example` to `.env` and configure the following variables:

#### Domain Configuration
- `DOMAINS`: Comma-separated list of domains to check (e.g., `example.de,test.de,mydomain.de`)

#### SMTP Configuration
- `SMTP_HOST`: SMTP server hostname (e.g., `smtp.gmail.com`)
- `SMTP_PORT`: SMTP server port (default: `587`)
- `SMTP_USERNAME`: SMTP username/email
- `SMTP_PASSWORD`: SMTP password (use app passwords for Gmail)
- `SMTP_FROM_EMAIL`: Email address to send from
- `SMTP_TO_EMAIL`: Email address to send notifications to
- `SMTP_USE_TLS`: Use TLS encryption (default: `true`)

#### Check Configuration
- `CHECK_INTERVAL_HOURS`: Hours between checks (default: `24`)
- `RUN_ONCE`: Set to `true` for single run, `false` for continuous monitoring (default: `false`)

### Example Configuration for Gmail

```env
DOMAINS=mydomain.de,anotherdomain.de
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-16-character-app-password
SMTP_FROM_EMAIL=your-email@gmail.com
SMTP_TO_EMAIL=notifications@yourdomain.com
SMTP_USE_TLS=true
CHECK_INTERVAL_HOURS=6
RUN_ONCE=false
```

## Deployment Options

### Option 1: Docker Compose (Recommended)

```bash
# Build and run
docker-compose up -d

# View logs
docker-compose logs -f

# Stop
docker-compose down
```

### Option 2: Docker Run

```bash
# Build the image
docker build -t free-domain-checker .

# Run with environment file
docker run -d --name domain-checker --env-file .env free-domain-checker

# Run with inline environment variables
docker run -d --name domain-checker \
  -e DOMAINS="example.de,test.de" \
  -e SMTP_HOST="smtp.gmail.com" \
  -e SMTP_USERNAME="your-email@gmail.com" \
  -e SMTP_PASSWORD="your-password" \
  -e SMTP_FROM_EMAIL="your-email@gmail.com" \
  -e SMTP_TO_EMAIL="notifications@yourdomain.com" \
  free-domain-checker
```

docker run --rm --env-file .env -e RUN_ONCE=true free-domain-checker
### Option 3: One-time Check (Cron / Kubernetes CronJob)

This container is designed to perform a single run and exit. Schedule it externally using system cron, a CI job, or a Kubernetes CronJob (see the Kubernetes example below).

Example for system cron (daily at 09:00):

```bash
# Run once and exit using environment file
docker run --rm --env-file .env free-domain-checker
```
### Kubernetes CronJob (recommended for k8s)

Use a Kubernetes CronJob to run the container on a schedule. The container runs once and exits, so the CronJob controller handles scheduling and retries.

Example CronJob manifest (edit image, schedule and env as needed):

```yaml
apiVersion: batch/v1
kind: CronJob
metadata:
   name: free-domain-checker
spec:
   schedule: "0 9 * * *" # daily at 09:00
   jobTemplate:
      spec:
         template:
            spec:
               containers:
               - name: domain-checker
                  image: your-registry/free-domain-checker:latest
                  env:
                           # Recommended: mount domains as a file via ConfigMap and reference it via DOMAINS_FILE
                           - name: DOMAINS_FILE
                              value: "/domains"
                     - name: SMTP_HOST
                        value: "smtp.gmail.com"
                     - name: SMTP_PORT
                        value: "587"
                     - name: SMTP_USERNAME
                        valueFrom:
                           secretKeyRef:
                              name: smtp-credentials
                              key: username
                              - name: SMTP_PASSWORD
                        valueFrom:
                           secretKeyRef:
                              name: smtp-credentials
                              key: password
                     - name: SMTP_FROM_EMAIL
                        value: "your-email@gmail.com"
                     - name: SMTP_TO_EMAIL
                        value: "notify@yourdomain.com"
                     - name: SMTP_USE_TLS
                        value: "true"
               restartPolicy: OnFailure
               # Use serviceAccountName, nodeSelector, tolerations, etc. as required

      Example ConfigMap (mount as a file):

      ```yaml
      apiVersion: v1
      kind: ConfigMap
      metadata:
         name: free-domain-checker-config
      data:
         domains: |-
            # One domain per line. Lines starting with '#' are ignored by the checker.
            freimuth.de
            tokio.de
            tokyo.de
            kyoto.de
            koriyama.de
      ```

      Mount the ConfigMap as a file in the CronJob pod and set `DOMAINS_FILE` to the mount path (example):

      ```yaml
      volumes:
         - name: domains
            configMap:
               name: free-domain-checker-config
               items:
                  - key: domains
                     path: domains

      volumeMounts:
         - name: domains
            mountPath: /domains
            readOnly: true

      env:
         - name: DOMAINS_FILE
            value: /domains
      ```
```

Notes:
- Store sensitive values (SMTP credentials) in Kubernetes Secrets and reference them via `valueFrom.secretKeyRef` as shown above.
- Adjust `schedule` to your preferred cron timing. For timezone-sensitive schedules, run a timezone-aware CronJob controller or convert to UTC.
- The container is built to run once and exit; do not expect it to run continuously inside a pod.

## Email Notification Format

When available domains are found, you'll receive an email like this:

```
Subject: Free Domains Found - 2025-09-27 14:30

Hello!

The domain checker has found 2 available domain(s):

• example.de
• test.de

Check performed at: 2025-09-27 14:30:15

Please verify availability manually before attempting to register.

Best regards,
Domain Checker Bot
```

## SMTP Provider Setup

### Gmail
1. Enable 2-factor authentication
2. Generate an app password: [Google Account Settings](https://myaccount.google.com/apppasswords)
3. Use the 16-character app password as `SMTP_PASSWORD`

### Outlook/Hotmail
```env
SMTP_HOST=smtp-mail.outlook.com
SMTP_PORT=587
```

### Custom SMTP
Configure according to your provider's documentation.

## Monitoring and Logs

View real-time logs:
```bash
docker-compose logs -f domain-checker
```

The application provides detailed logging including:
- Domain check results
- Email sending status
- Error messages and warnings
- Configuration validation

## Troubleshooting

### Common Issues

**"No domains specified" error:**
- Ensure `DOMAINS` environment variable is set with comma-separated domain names

**Email sending fails:**
- Verify SMTP credentials and settings
- For Gmail, use app passwords instead of regular passwords
- Check firewall/network connectivity to SMTP server

**Domain checks return unclear results:**
- Some domains might have complex whois configurations
- The tool logs warnings for uncertain cases
- Manual verification is always recommended

**Container exits immediately:**
- Check logs with `docker-compose logs domain-checker`
- Verify all required environment variables are set
- Ensure proper `.env` file format

### Debug Mode

For detailed debugging, check the container logs:
```bash
docker-compose logs -f
```

## Security Considerations

- The container runs as a non-root user
- Store sensitive credentials (SMTP passwords) securely
- Consider using Docker secrets for production deployments
- Regularly update the base image for security patches

## Development

To modify or extend the checker:

1. Edit `main.py` for functionality changes
2. Update `requirements.txt` for new dependencies
3. Rebuild the container: `docker-compose build`

## License

This project is provided as-is for educational and personal use.

## Disclaimer

This tool provides automated domain availability checking but results should always be verified manually before attempting domain registration. Domain availability can change rapidly, and whois data may not always be completely accurate or up-to-date.