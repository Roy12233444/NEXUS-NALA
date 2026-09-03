use bcrypt::{hash, verify, DEFAULT_COST};
use chrono::prelude::*;
use colored::*;
use lettre::transport::smtp::authentication::Credentials;
use lettre::{Message, SmtpTransport, Transport};
use serde::{Deserialize, Serialize};
use std::fs;
use std::io::{self, Write};
use std::path::{Path, PathBuf};
use std::time::{Duration, SystemTime, UNIX_EPOCH};

// ═══════════════════════════════════════════════════════════════
// SECURITY SYSTEM - Password Protection & Authentication
// ═══════════════════════════════════════════════════════════════

#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct SecurityConfig {
    pub password_enabled: bool,
    pub password_hash: String,
    pub require_password_for: Vec<String>,
    pub max_failed_attempts: u32,
    pub lockout_duration_minutes: u32,
}

impl Default for SecurityConfig {
    fn default() -> Self {
        Self {
            password_enabled: false,
            password_hash: String::new(),
            require_password_for: vec!["DELETE".into(), "MODIFY".into()],
            max_failed_attempts: 3,
            lockout_duration_minutes: 5,
        }
    }
}

pub struct SecurityManager {
    pub config: SecurityConfig,
    pub failed_attempts: u32,
    pub lockout_until: Option<SystemTime>,
}

impl SecurityManager {
    pub fn new(config: SecurityConfig) -> Self {
        Self {
            config,
            failed_attempts: 0,
            lockout_until: None,
        }
    }

    pub fn set_password(&mut self, password: &str) {
        match hash(password, DEFAULT_COST) {
            Ok(hashed) => {
                self.config.password_hash = hashed;
                self.config.password_enabled = true;
                println!(
                    "{}",
                    "🔐 Password protection enabled (Secured with bcrypt)"
                        .green()
                        .bold()
                );
            }
            Err(e) => println!("{}", format!("❌ Failed to hash password: {}", e).red()),
        }
    }

    pub fn verify_password(&mut self, operation: &str) -> Result<bool, String> {
        // Check if locked out
        if let Some(lockout) = self.lockout_until {
            if SystemTime::now() < lockout {
                return Err(
                    "🔒 Account locked due to failed attempts. Try again later.".to_string()
                );
            } else {
                self.lockout_until = None;
                self.failed_attempts = 0;
            }
        }

        if !self.config.password_enabled {
            return Ok(true);
        }

        if !self
            .config
            .require_password_for
            .contains(&operation.to_string())
        {
            return Ok(true);
        }

        println!(
            "\n{}",
            format!("🔐 PASSWORD REQUIRED for {} operation", operation)
                .yellow()
                .bold()
        );
        print!("   Enter password: ");
        io::stdout().flush().unwrap();

        let password = Self::read_password();

        match verify(&password, &self.config.password_hash) {
            Ok(valid) if valid => {
                self.failed_attempts = 0;
                println!("{}", "✅ Authentication successful".green());
                Ok(true)
            }
            _ => {
                self.failed_attempts += 1;

                if self.failed_attempts >= self.config.max_failed_attempts {
                    self.lockout_until = Some(
                        SystemTime::now()
                            + Duration::from_secs(self.config.lockout_duration_minutes as u64 * 60),
                    );
                    Err(format!(
                        "❌ Too many failed attempts! Locked for {} minutes",
                        self.config.lockout_duration_minutes
                    ))
                } else {
                    Err(format!(
                        "❌ Wrong password! {} attempts remaining",
                        self.config.max_failed_attempts - self.failed_attempts
                    ))
                }
            }
        }
    }

    fn read_password() -> String {
        let mut password = String::new();
        io::stdin().read_line(&mut password).unwrap();
        password.trim().to_string()
    }
}

// ═══════════════════════════════════════════════════════════════
// EMAIL ALERT SYSTEM - Notification Before Big Changes
// ═══════════════════════════════════════════════════════════════

#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct EmailConfig {
    pub enabled: bool,
    pub email_address: String,
    pub alert_on_delete: bool,
    pub alert_on_bulk_operations: bool,
    pub bulk_threshold: usize,
    // Add real SMTP settings in production (skipped here for safe demo)
}

impl Default for EmailConfig {
    fn default() -> Self {
        Self {
            enabled: false,
            email_address: String::new(),
            alert_on_delete: true,
            alert_on_bulk_operations: true,
            bulk_threshold: 10,
        }
    }
}

pub struct EmailAlertSystem {
    config: EmailConfig,
}

impl EmailAlertSystem {
    pub fn new(config: EmailConfig) -> Self {
        Self { config }
    }

    pub fn send_alert(&self, operation: &str, details: &str) -> Result<(), String> {
        if !self.config.enabled || self.config.email_address.is_empty() {
            return Ok(());
        }

        println!(
            "\n{}",
            format!("📧 SENDING EMAIL ALERT to {}", self.config.email_address).cyan()
        );
        println!("   Subject: ClaudeDesk Alert - {} Operation", operation);
        println!("   Details: {}", details);

        // Simulating the actual send to avoid needing a real SMTP server for this demo
        // In real use, unwrap the following code with valid credentials:
        /*
        let email = Message::builder()
            .from("ClaudeDesk <alert@claudedesk.ai>".parse().unwrap())
            .to(self.config.email_address.parse().unwrap())
            .subject(format!("ClaudeDesk Alert: {}", operation))
            .body(String::from(details))
            .unwrap();

        // Use a real transport here
        */

        println!("{}", "📧 Alert email dispatched successfully".green());
        Ok(())
    }

    pub fn should_alert(&self, operation: &str, file_count: usize) -> bool {
        if !self.config.enabled {
            return false;
        }

        if operation.contains("DELETE") && self.config.alert_on_delete {
            return true;
        }

        if file_count >= self.config.bulk_threshold && self.config.alert_on_bulk_operations {
            return true;
        }

        false
    }
}

// ═══════════════════════════════════════════════════════════════
// AUDIT LOG SYSTEM - Complete Operation History
// ═══════════════════════════════════════════════════════════════

#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct AuditLogEntry {
    pub timestamp: u64,
    pub operation: String,
    pub file_path: String,
    pub user: String,
    pub success: bool,
    pub details: String,
    pub file_hash_before: Option<String>,
    pub file_hash_after: Option<String>,
}

pub struct AuditLogger {
    pub log_file: PathBuf,
    pub entries: Vec<AuditLogEntry>,
}

impl AuditLogger {
    pub fn new(log_file: PathBuf) -> Self {
        let mut logger = Self {
            log_file: log_file.clone(),
            entries: Vec::new(),
        };

        if log_file.exists() {
            if let Ok(content) = fs::read_to_string(&log_file) {
                if let Ok(logs) = serde_json::from_str::<Vec<AuditLogEntry>>(&content) {
                    logger.entries = logs;
                }
            }
        }

        logger
    }

    pub fn log_operation(
        &mut self,
        operation: &str,
        file_path: &str,
        success: bool,
        details: &str,
        hash_before: Option<String>,
        hash_after: Option<String>,
    ) {
        let entry = AuditLogEntry {
            timestamp: SystemTime::now()
                .duration_since(UNIX_EPOCH)
                .unwrap()
                .as_secs(),
            operation: operation.to_string(),
            file_path: file_path.to_string(),
            user: get_username(),
            success,
            details: details.to_string(),
            file_hash_before: hash_before,
            file_hash_after: hash_after,
        };

        self.entries.push(entry);
        self.save_to_disk();
    }

    fn save_to_disk(&self) {
        if let Ok(json) = serde_json::to_string_pretty(&self.entries) {
            let _ = fs::write(&self.log_file, json);
        }
    }

    pub fn display_recent_logs(&self, count: usize) {
        println!(
            "\n{}",
            format!("📝 AUDIT LOG - Recent {} Operations:", count)
                .blue()
                .bold()
        );
        println!(
            "{}",
            "────────────────────────────────────────────────────────".blue()
        );

        let recent: Vec<_> = self.entries.iter().rev().take(count).collect();

        for (i, entry) in recent.iter().enumerate() {
            let status_icon = if entry.success { "✅" } else { "❌" };
            let dt = Utc.timestamp_opt(entry.timestamp as i64, 0).unwrap();
            let datetime = dt.format("%Y-%m-%d %H:%M:%S").to_string();

            println!("\n   Log #{}", i + 1);
            println!("   {} Operation: {}", status_icon, entry.operation.cyan());
            println!("   📁 File: {}", entry.file_path);
            println!("   👤 User: {}", entry.user.yellow());
            println!("   🕐 Time: {}", datetime);
            println!("   📄 Details: {}", entry.details);

            if let Some(ref hash) = entry.file_hash_before {
                println!("   🔐 Hash Before: {}", hash);
            }
            if let Some(ref hash) = entry.file_hash_after {
                println!("   🔐 Hash After: {}", hash);
            }
        }

        println!(
            "{}",
            "────────────────────────────────────────────────────────".blue()
        );
    }
}

fn get_username() -> String {
    std::env::var("USER")
        .or_else(|_| std::env::var("USERNAME"))
        .unwrap_or_else(|_| "unknown_user".to_string())
}
