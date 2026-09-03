// ClaudeDesk v6.0 - OMNI-INTERFACE EDITION
// Built with Rust for maximum performance, safety, and cosmic intelligence
// Author: Created by Claude
// License: MIT

mod cosmic;
mod security;
mod web;

use colored::*;
use std::fs;
use std::io::{self, Write};
use std::path::{Path, PathBuf};
use std::sync::{Arc, RwLock};
use std::time::Duration;
use tokio::runtime::Runtime;

use cosmic::{CosmicFileExplorer, PredictiveAI, QuantumEntanglement};
use security::{AuditLogger, EmailAlertSystem, EmailConfig, SecurityConfig, SecurityManager};

// ═══════════════════════════════════════════════════════════════
// CONFIGURATION SYSTEM
// ═══════════════════════════════════════════════════════════════

#[derive(Debug, Clone)]
pub struct NeuralConfig {
    api_key: String,
    model: String,
    workspace_path: PathBuf,
    security: SecurityConfig,
    email: EmailConfig,
}

impl Default for NeuralConfig {
    fn default() -> Self {
        Self {
            api_key: String::new(),
            model: "claude-sonnet-2026".to_string(),
            workspace_path: PathBuf::from("./workspace"),
            security: SecurityConfig::default(),
            email: EmailConfig::default(),
        }
    }
}

// ═══════════════════════════════════════════════════════════════
// SHARED APPLICATION STATE
// ═══════════════════════════════════════════════════════════════

pub struct AppState {
    pub config: NeuralConfig,
    pub security_manager: SecurityManager,
    pub email_system: EmailAlertSystem,
    pub audit_logger: AuditLogger,
    pub cosmic_explorer: CosmicFileExplorer,
    pub predictive_ai: PredictiveAI,
    pub quantum_link: QuantumEntanglement,
    pub running: bool,
}

impl AppState {
    fn new() -> Self {
        let config = NeuralConfig::default();

        Self {
            config: config.clone(),
            security_manager: SecurityManager::new(config.security.clone()),
            email_system: EmailAlertSystem::new(config.email.clone()),
            audit_logger: AuditLogger::new(PathBuf::from("audit_log.json")),
            cosmic_explorer: CosmicFileExplorer::new(),
            predictive_ai: PredictiveAI::new(),
            quantum_link: QuantumEntanglement::new(),
            running: true,
        }
    }

    fn init(&mut self) {
        if !self.config.workspace_path.exists() {
            fs::create_dir_all(&self.config.workspace_path).unwrap_or_default();
        }
        self.cosmic_explorer
            .map_files_to_galaxy(&self.config.workspace_path);
    }
}

// ═══════════════════════════════════════════════════════════════
// HELPER FOR HEADLESS COMMANDS (WEB API)
// ═══════════════════════════════════════════════════════════════

pub fn process_command_headless(state: &mut AppState, input: &str) -> String {
    let parts: Vec<&str> = input.split_whitespace().collect();
    if parts.is_empty() {
        return String::new();
    }

    let command = parts[0].to_lowercase();

    // Simple output capture (for demo purposes, we reconstruct messages)
    // In a real app, we'd refactor to return Result<String, String> across the board.

    match command.as_str() {
        "help" => "Available: explore, scan, link, create, delete, audit".to_string(),
        "scan" => {
            state
                .cosmic_explorer
                .map_files_to_galaxy(&state.config.workspace_path);
            format!(
                "Scan complete. {} files found.",
                state.cosmic_explorer.files.len()
            )
        }
        "explore" | "galaxy" => {
            // Web view handles this via /api/galaxy, but return ASCII for terminal log
            "Launch Galaxy View to see visualization.".to_string()
        }
        "link" => {
            if parts.len() < 3 {
                "Usage: link <file1> <file2>".to_string()
            } else {
                let f1 = state.config.workspace_path.join(parts[1]);
                let f2 = state.config.workspace_path.join(parts[2]);
                if f1.exists() && f2.exists() {
                    state.quantum_link.entangle(f1, f2, true);
                    state.audit_logger.log_operation(
                        "LINK",
                        parts[1],
                        true,
                        "Quantum link established",
                        None,
                        None,
                    );
                    "✨ Quantum link established!".to_string()
                } else {
                    "❌ One or both files not found".to_string()
                }
            }
        }
        "audit" => {
            // Web handles this via /api/logs
            format!(
                "Audit logs contain {} entries. View in Security Log tab.",
                state.audit_logger.entries.len()
            )
        }
        "create" => {
            if parts.len() < 2 {
                return "Usage: create <filename>".to_string();
            }
            let filename = parts[1];
            let path = state.config.workspace_path.join(filename);
            if let Ok(_) = fs::write(&path, "New file content") {
                state.audit_logger.log_operation(
                    "CREATE",
                    filename,
                    true,
                    "File created",
                    None,
                    None,
                );
                state
                    .cosmic_explorer
                    .map_files_to_galaxy(&state.config.workspace_path);
                format!("✅ Created {}", filename)
            } else {
                "❌ Failed to create file".to_string()
            }
        }
        "delete" => {
            if parts.len() < 2 {
                return "Usage: delete <filename>".to_string();
            }
            let filename = parts[1];
            let path = state.config.workspace_path.join(filename);
            if path.exists() {
                match fs::remove_file(&path) {
                    Ok(_) => {
                        state.audit_logger.log_operation(
                            "DELETE",
                            filename,
                            true,
                            "File deleted",
                            None,
                            None,
                        );
                        state
                            .cosmic_explorer
                            .map_files_to_galaxy(&state.config.workspace_path);
                        format!("🗑️ Deleted {}", filename)
                    }
                    Err(e) => format!("❌ Failed: {}", e),
                }
            } else {
                "❌ File not found".to_string()
            }
        }
        _ => "❌ Unknown command".to_string(),
    }
}

// ═══════════════════════════════════════════════════════════════
// HOLOGRAPHIC UI
// ═══════════════════════════════════════════════════════════════

struct HolographicDisplay;

impl HolographicDisplay {
    fn render_banner() {
        println!(
            "{}",
            "\n═══════════════════════════════════════════════════════════════════".bright_blue()
        );
        println!(
            "{}",
            r#"
     ██████╗██╗      █████╗ ██╗   ██╗██████╗ ███████╗
    ██╔════╝██║     ██╔══██╗██║   ██║██╔══██╗██╔════╝
    ██║     ██║     ███████║██║   ██║██║  ██║█████╗  
    ██║     ██║     ██╔══██║██║   ██║██║  ██║██╔══╝  
    ╚██████╗███████╗██║  ██║╚██████╔╝██████╔╝███████╗
     ╚═════╝╚══════╝╚═╝  ╚═╝ ╚═════╝ ╚═════╝ ╚══════╝
    
            OMNI-INTERFACE EDITION (v6.0)
        "#
            .cyan()
            .bold()
        );
        println!(
            "{}",
            "═══════════════════════════════════════════════════════════════════".bright_blue()
        );
        println!(
            "   {} Web Dashboard Active: http://localhost:3000",
            "🌐".green().blink()
        );
        println!("   {} 3D Cosmic Explorer (Visual Links)", "🌌".magenta());
        println!("   {} Quantum File Entanglement", "⚛️".blue());
        println!("   {} Industry-Grade Security", "🛡️".green());
        println!(
            "{}",
            "═══════════════════════════════════════════════════════════════════\n".bright_blue()
        );
    }
}

// ═══════════════════════════════════════════════════════════════
// MAIN ENTRY POINT
// ═══════════════════════════════════════════════════════════════

fn main() {
    // 1. Initialize State
    let mut state = AppState::new();
    state.init(); // Initial scan

    // 2. Wrap in Arc/RwLock for sharing
    let shared_state = Arc::new(RwLock::new(state));

    // 3. Spawn Web Server in Background thread (using Tokio)
    let rt = Runtime::new().unwrap();
    let web_state = shared_state.clone();

    rt.spawn(async move {
        let app = web::create_router(web_state);
        let listener = tokio::net::TcpListener::bind("0.0.0.0:3000").await.unwrap();
        axum::serve(listener, app).await.unwrap();
    });

    // 4. Run CLI Interface in Main Thread
    HolographicDisplay::render_banner();

    let mut running = true;
    while running {
        print!("\n{} {} ", "ClaudeDesk".blue().bold(), ">".white());
        io::stdout().flush().unwrap();

        let mut input = String::new();
        io::stdin().read_line(&mut input).unwrap();
        let input = input.trim();

        if input.is_empty() {
            continue;
        }

        // Lock state for CLI operation
        {
            let mut state = shared_state.write().unwrap();

            // Check exit
            if input.eq_ignore_ascii_case("exit") || input.eq_ignore_ascii_case("quit") {
                running = false;
                println!("{}", "👋 Shutting down Omni-Interface...".yellow());
                continue;
            }

            // Learn & Predict
            state.predictive_ai.learn_action(input);
            if let Some(prediction) = state.predictive_ai.predict_next(input) {
                println!(
                    "{}",
                    format!(
                        "🤖 AI Extract: Based on patterns, you might want to run '{}' next.",
                        prediction
                    )
                    .cyan()
                    .italic()
                );
            }

            // Command Processing (CLI-specific mostly mirrored from headless/v5)
            let parts: Vec<&str> = input.split_whitespace().collect();
            let command = parts[0].to_lowercase();

            // Security verify (CLI ONLY)
            if let Err(e) = state
                .security_manager
                .verify_password(&command.to_uppercase())
            {
                println!("{}", e.red());
                continue;
            }

            match command.as_str() {
                "help" => {
                    println!("\n{}", "📖 AVAILABLE COMMANDS".bold().underline());
                    println!("  {} - Show 3D galaxy with visual links", "explore".green());
                    println!("  {} - Create quantum link", "link <f1> <f2>".green());
                    println!("  {} - Create/Delete files", "create/delete <name>".green());
                    println!("  {} - View audit logs", "audit".yellow());
                    println!("  {} - Exit", "exit".red());
                }
                "explore" | "galaxy" => {
                    state.cosmic_explorer.render_galaxy(&state.quantum_link);
                }
                "password" => {
                    if parts.len() > 1 && parts[1] == "set" {
                        print!("Enter new password: ");
                        io::stdout().flush().unwrap();
                        let mut pw = String::new();
                        io::stdin().read_line(&mut pw).unwrap();
                        state.security_manager.set_password(pw.trim());
                    }
                }
                _ => {
                    // Use headless logic for common ops
                    let output = process_command_headless(&mut state, input);
                    println!("{}", output);
                }
            }
        } // state unlock
    }
}
