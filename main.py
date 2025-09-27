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

try:
    import whois
except ImportError:
    print("ERROR: python-whois library not found. Please install it with: pip install python-whois")
    sys.exit(1)


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
        """Get domains from environment variables."""
        domains_str = os.getenv('DOMAINS', '')
        if not domains_str:
            logger.error("No domains specified. Set DOMAINS environment variable.")
            sys.exit(1)
            
        # Split by comma and clean up
        domains = [domain.strip() for domain in domains_str.split(',') if domain.strip()]
        
        if not domains:
            logger.error("No valid domains found in DOMAINS environment variable.")
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
            
            # First, try to resolve the domain
            try:
                socket.gethostbyname(domain)
                logger.info(f"Domain {domain} resolves to an IP address (likely taken)")
                return False
            except socket.gaierror:
                # Domain doesn't resolve, continue with whois check
                pass
            
            # Check whois information
            domain_info = whois.whois(domain)
            
            # If we get a result, the domain is likely registered
            if domain_info and domain_info.domain_name:
                logger.info(f"Domain {domain} is registered")
                return False
            else:
                logger.info(f"Domain {domain} appears to be available")
                return True
                
        except whois.parser.PywhoisError as e:
            if "No match" in str(e) or "No entries found" in str(e):
                logger.info(f"Domain {domain} appears to be available (whois: no match)")
                return True
            else:
                logger.warning(f"Whois error for {domain}: {e}")
                return None
        except Exception as e:
            logger.error(f"Error checking domain {domain}: {e}")
            return None
    
    def send_email_notification(self, available_domains: List[str]) -> bool:
        """Send email notification for available domains."""
        try:
            logger.info(f"Sending email notification for {len(available_domains)} available domains")
            
            # Create message
            msg = MIMEMultipart()
            msg['From'] = self.smtp_config['from_email']
            msg['To'] = self.smtp_config['to_email']
            msg['Subject'] = f"Free Domains Found - {datetime.now().strftime('%Y-%m-%d %H:%M')}"
            
            # Create email body
            body = f"""
Hello!

The domain checker has found {len(available_domains)} available domain(s):

"""
            for domain in available_domains:
                body += f"• {domain}\n"
            
            body += f"""

Check performed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

Please verify availability manually before attempting to register.

Best regards,
Domain Checker Bot
"""
            
            msg.attach(MIMEText(body, 'plain'))
            
            # Send email
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
                time.sleep(2)
                
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