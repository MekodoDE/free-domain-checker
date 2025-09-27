#!/usr/bin/env python3
"""
Free Domain Checker
Checks a list of domains for availability and sends email notifications for free domains.
Domains and SMTP configuration are provided via environment variables.
"""

import os
import sys
import smtplib
import socket
import time
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List, Optional
from datetime import datetime

# No whois library used — DNS resolution only


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DomainChecker:
    def __init__(self):
        self.domains = self._get_domains_from_env()
        self.smtp_config = self._get_smtp_config()
        
    def _get_domains_from_env(self) -> List[str]:
        """Get domains from a mounted file specified by DOMAINS_FILE (recommended for large lists)."""
        # default path changed to a conventional config mount path
        domains_file = os.getenv('DOMAINS_FILE', '/domains')

        if not os.path.exists(domains_file):
            logger.error(f"Domains file not found: {domains_file}. Mount a ConfigMap/Secret at this path and set DOMAINS_FILE if needed.")
            sys.exit(1)

        try:
            with open(domains_file, 'r', encoding='utf-8') as fh:
                raw = fh.read()
        except Exception as e:
            logger.error(f"Failed to read domains file {domains_file}: {e}")
            sys.exit(1)

        # Accept newline-separated, comma-separated, semicolon-separated, or whitespace-separated lists
        # Normalize separators to newlines then split
        for part in [',', ';', '\r', '\t']:
            raw = raw.replace(part, '\n')

        # Parse lines, ignore empty lines and lines starting with '#'
        domains = []
        for line in raw.splitlines():
            ln = line.strip()
            if not ln:
                continue
            if ln.startswith('#'):
                # skip comment lines
                continue
            domains.append(ln)

        if not domains:
            logger.error(f"No valid domains found in domains file: {domains_file}")
            sys.exit(1)

        logger.info(f"Loaded {len(domains)} domains to check: {', '.join(domains)}")
        return domains
    
    def _get_smtp_config(self) -> dict:
        """Get SMTP configuration from environment variables."""
        config = {
            'host': os.getenv('SMTP_HOST'),
            'port': int(os.getenv('SMTP_PORT', '587')),
            'username': os.getenv('SMTP_USERNAME'),
            'password': os.getenv('SMTP_PASSWORD'),
            'from_email': os.getenv('SMTP_FROM_EMAIL'),
            'to_email': os.getenv('SMTP_TO_EMAIL'),
            'use_tls': os.getenv('SMTP_USE_TLS', 'true').lower() == 'true'
        }
        
        required_fields = ['host', 'username', 'password', 'from_email', 'to_email']
        missing_fields = [field for field in required_fields if not config.get(field)]
        
        if missing_fields:
            logger.error(f"Missing required SMTP configuration: {', '.join(missing_fields)}")
            sys.exit(1)
            
        logger.info(f"SMTP configured: {config['host']}:{config['port']}")
        return config
    
    def check_domain_availability(self, domain: str) -> Optional[bool]:
        """
        Check if a domain is available.
        Returns True if available, False if taken, None if unable to determine.
        """
        try:
            logger.info(f"Checking domain: {domain}")

            # Try to resolve the domain: if it resolves, it's likely taken
            try:
                socket.gethostbyname(domain)
                logger.info(f"Domain {domain} resolves to an IP address (likely taken)")
                return False
            except socket.gaierror:
                # Domain doesn't resolve -> probably available
                logger.info(f"Domain {domain} appears to be available (no DNS record)")
                return True

        except Exception as e:
            logger.error(f"Error checking domain {domain}: {e}")
            return None

    def send_email_notification(self, available_domains: List[str]) -> bool:
        """Send email notification for available domains."""
        try:
            logger.info(f"Sending email notification for {len(available_domains)} available domains")

            msg = MIMEMultipart()
            msg['From'] = self.smtp_config['from_email']
            msg['To'] = self.smtp_config['to_email']
            msg['Subject'] = f"Free Domains Found - {datetime.now().strftime('%Y-%m-%d %H:%M')}"

            body = f"""
Hello!

The domain checker has found {len(available_domains)} available domain(s):

"""
            for d in available_domains:
                body += f"• {d}\n"

            body += f"""

Check performed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

Please verify availability manually before attempting to register.

Best regards,
Domain Checker Bot
"""

            msg.attach(MIMEText(body, 'plain'))

            server = smtplib.SMTP(self.smtp_config['host'], self.smtp_config['port'])
            if self.smtp_config['use_tls']:
                server.starttls()
            server.login(self.smtp_config['username'], self.smtp_config['password'])
            server.send_message(msg)
            server.quit()

            logger.info("Email notification sent successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to send email notification: {e}")
            return False
    
    def run_check(self) -> None:
        """Run domain availability check for all domains."""
        logger.info("Starting domain availability check")
        available_domains = []
        
        for domain in self.domains:
            try:
                is_available = self.check_domain_availability(domain)
                
                if is_available is True:
                    available_domains.append(domain)
                elif is_available is False:
                    logger.info(f"Domain {domain} is not available")
                else:
                    logger.warning(f"Could not determine availability for {domain}")
                
                # Small delay between checks to be respectful to whois servers
                time.sleep(0.1)
                
            except Exception as e:
                logger.error(f"Error processing domain {domain}: {e}")
        
        # Send notification if any domains are available
        if available_domains:
            logger.info(f"Found {len(available_domains)} available domains: {', '.join(available_domains)}")
            self.send_email_notification(available_domains)
        else:
            logger.info("No available domains found")
    
    def run(self) -> None:
        """Main run loop."""
        # Designed for single-run execution (e.g. Kubernetes CronJob).
        logger.info("Domain Checker started (single run)")
        logger.info(f"Checking {len(self.domains)} domains")

        try:
            self.run_check()
            logger.info("Single run completed, exiting")
        except KeyboardInterrupt:
            logger.info("Received interrupt signal, shutting down...")
        except Exception as e:
            logger.error(f"Unexpected error during run: {e}")


if __name__ == "__main__":
    try:
        checker = DomainChecker()
        checker.run()
    except Exception as e:
        logger.error(f"Failed to start domain checker: {e}")
        sys.exit(1)