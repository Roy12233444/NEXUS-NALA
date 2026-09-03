use colored::*;
use rand::Rng;
use serde::{Deserialize, Serialize};
use std::collections::{HashMap, VecDeque};
use std::fs;
use std::path::{Path, PathBuf};
use std::time::{SystemTime, UNIX_EPOCH};

// ═══════════════════════════════════════════════════════════════
// FEATURE 1: 🌌 3D COSMIC FILE EXPLORER
// ═══════════════════════════════════════════════════════════════

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CosmicCoordinates {
    pub x: f64,
    pub y: f64,
    pub z: f64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CosmicFile {
    pub path: PathBuf,
    pub position: CosmicCoordinates,
    pub size_radius: f64,
    pub color: String,
    pub gravity: f64,
}

pub struct CosmicFileExplorer {
    pub files: Vec<CosmicFile>,
    pub camera_position: CosmicCoordinates,
    pub zoom_level: f64,
}

impl CosmicFileExplorer {
    pub fn new() -> Self {
        Self {
            files: Vec::new(),
            camera_position: CosmicCoordinates {
                x: 0.0,
                y: 0.0,
                z: 100.0,
            },
            zoom_level: 1.0,
        }
    }

    pub fn map_files_to_galaxy(&mut self, workspace: &Path) {
        println!("\n{}", "🌌 COSMIC MAPPING INITIATED...".magenta().bold());
        println!(
            "{}",
            "⚡ Transforming files into celestial objects...".cyan()
        );

        self.files.clear();

        if let Ok(entries) = fs::read_dir(workspace) {
            let mut angle = 0.0;
            let radius_base = 50.0;

            for (i, entry) in entries.flatten().enumerate() {
                let path = entry.path();
                if !path.is_file() {
                    continue;
                }

                let size = fs::metadata(&path).map(|m| m.len()).unwrap_or(0);
                let size_radius = (size as f64).log10().max(1.0) * 2.0;

                // Create spiral galaxy distribution
                let spiral_arm = (i % 3) as f64;
                let radius = radius_base + (i as f64 * 5.0);

                let x = radius * (angle + spiral_arm * 2.0).cos();
                let y = radius * (angle + spiral_arm * 2.0).sin();
                let z = ((i as f64 / 10.0).sin() * 20.0);

                angle += 0.5;

                let color = Self::determine_star_color(&path);
                let gravity = size as f64 / 1_000_000.0;

                self.files.push(CosmicFile {
                    path: path.clone(),
                    position: CosmicCoordinates { x, y, z },
                    size_radius,
                    color,
                    gravity,
                });
            }
        }

        println!("✨ {} celestial objects mapped!", self.files.len());
    }

    fn determine_star_color(path: &Path) -> String {
        let ext = path
            .extension()
            .and_then(|s| s.to_str())
            .unwrap_or("")
            .to_lowercase();

        match ext.as_str() {
            "txt" | "md" => "blue",
            "pdf" | "doc" => "white",
            "jpg" | "png" => "yellow",
            "mp4" | "avi" => "red",
            "py" | "rs" | "js" => "green",
            _ => "magenta",
        }
        .to_string()
    }

    pub fn render_galaxy(&self, quantum: &QuantumEntanglement) {
        println!("\n{}", "🌌 COSMIC VIEW - FILE GALAXY".bold().underline());
        println!(
            "{}",
            format!(
                "   Camera: X={:.1} Y={:.1} Z={:.1} | Zoom: {:.1}x",
                self.camera_position.x,
                self.camera_position.y,
                self.camera_position.z,
                self.zoom_level
            )
            .cyan()
        );

        // Create 2D projection of 3D space
        let width = 60;
        let height = 20;
        let mut screen = vec![vec![" ".to_string(); width]; height];

        // Helper to project 3D to 2D
        let project = |pos: &CosmicCoordinates| -> Option<(usize, usize)> {
            let dist = ((pos.z - self.camera_position.z).abs() + 1.0) / self.zoom_level;
            if dist <= 0.0 {
                return None;
            }
            let raw_x = (pos.x - self.camera_position.x) / dist;
            let raw_y = (pos.y - self.camera_position.y) / dist;
            let proj_x = (raw_x + 30.0) as isize;
            let proj_y = (raw_y + 10.0) as isize;

            if proj_x >= 0 && proj_x < width as isize && proj_y >= 0 && proj_y < height as isize {
                Some((proj_x as usize, proj_y as usize))
            } else {
                None
            }
        };

        // Draw Quantum Links (Lines)
        for link in &quantum.links {
            // Find positions of both files
            let p1 = self
                .files
                .iter()
                .find(|f| f.path == link.file1)
                .map(|f| &f.position);
            let p2 = self
                .files
                .iter()
                .find(|f| f.path == link.file2)
                .map(|f| &f.position);

            if let (Some(pos1), Some(pos2)) = (p1, p2) {
                if let (Some((x1, y1)), Some((x2, y2))) = (project(pos1), project(pos2)) {
                    // Bresenham's Line Algorithm (Simplified)
                    let mut x = x1 as isize;
                    let mut y = y1 as isize;
                    let x2_i = x2 as isize;
                    let y2_i = y2 as isize;

                    let dx = (x2_i - x).abs();
                    let dy = -(y2_i - y).abs();
                    let sx = if x < x2_i { 1 } else { -1 };
                    let sy = if y < y2_i { 1 } else { -1 };
                    let mut err = dx + dy;

                    while x != x2_i || y != y2_i {
                        if x >= 0 && x < width as isize && y >= 0 && y < height as isize {
                            let cell = &mut screen[y as usize][x as usize];
                            if cell == " " {
                                *cell = ".".blue().dimmed().to_string();
                            }
                        }
                        let e2 = 2 * err;
                        if e2 >= dy {
                            err += dy;
                            x += sx;
                        }
                        if e2 <= dx {
                            err += dx;
                            y += sy;
                        }
                    }
                }
            }
        }

        // Draw Stars
        for file in &self.files {
            if let Some((proj_x, proj_y)) = project(&file.position) {
                let symbol = if file.size_radius > 5.0 {
                    "●"
                } else if file.size_radius > 3.0 {
                    "◉"
                } else {
                    "○"
                };

                let colored_symbol = match file.color.as_str() {
                    "blue" => symbol.blue(),
                    "white" => symbol.white(),
                    "yellow" => symbol.yellow(),
                    "red" => symbol.red(),
                    "green" => symbol.green(),
                    _ => symbol.magenta(),
                };

                screen[proj_y][proj_x] = colored_symbol.to_string();
            }
        }

        // Render screen
        print!("   ┌");
        print!("{}", "─".repeat(width));
        println!("┐");

        for row in screen {
            print!("   │");
            for cell in row {
                print!("{}", cell);
            }
            println!("│");
        }

        print!("   └");
        print!("{}", "─".repeat(width));
        println!("┘");

        println!(
            "\n   Legend: {} Large  {} Medium  {} Small  {} Link",
            "●".white(),
            "◉".white(),
            "○".white(),
            ".".blue()
        );
    }
}

// ═══════════════════════════════════════════════════════════════
// FEATURE 2: 🧠 PREDICTIVE AI ASSISTANT
// ═══════════════════════════════════════════════════════════════

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct UserAction {
    pub command: String,
    pub timestamp: u64,
}

pub struct PredictiveAI {
    pub action_history: VecDeque<UserAction>,
    // Maps current command -> likely next commands
    pub patterns: HashMap<String, Vec<String>>,
}

impl PredictiveAI {
    pub fn new() -> Self {
        Self {
            action_history: VecDeque::with_capacity(100),
            patterns: HashMap::new(),
        }
    }

    pub fn learn_action(&mut self, command: &str) {
        let action = UserAction {
            command: command.to_string(),
            timestamp: SystemTime::now()
                .duration_since(UNIX_EPOCH)
                .unwrap()
                .as_secs(),
        };

        self.action_history.push_back(action);
        if self.action_history.len() > 100 {
            self.action_history.pop_front();
        }

        // Simple Markov Chain learning
        let recent: Vec<_> = self.action_history.iter().rev().take(10).collect();
        if recent.len() >= 2 {
            let curr = &recent[1].command; // Previous
            let next = &recent[0].command; // Current (just added)

            self.patterns
                .entry(curr.clone())
                .or_insert_with(Vec::new)
                .push(next.clone());
        }
    }

    pub fn predict_next(&self, current_command: &str) -> Option<String> {
        if let Some(candidates) = self.patterns.get(current_command) {
            // Find most frequent next command
            let mut counts = HashMap::new();
            for cmd in candidates {
                *counts.entry(cmd).or_insert(0) += 1;
            }

            counts
                .into_iter()
                .max_by_key(|&(_, count)| count)
                .map(|(cmd, _)| cmd.clone())
        } else {
            None
        }
    }
}

// ═══════════════════════════════════════════════════════════════
// FEATURE 3: ⚛️ QUANTUM FILE LINKING
// ═══════════════════════════════════════════════════════════════

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct QuantumLink {
    pub file1: PathBuf,
    pub file2: PathBuf,
    pub bidirectional: bool,
}

pub struct QuantumEntanglement {
    pub links: Vec<QuantumLink>,
}

impl QuantumEntanglement {
    pub fn new() -> Self {
        Self { links: Vec::new() }
    }

    pub fn entangle(&mut self, f1: PathBuf, f2: PathBuf, bi: bool) {
        self.links.push(QuantumLink {
            file1: f1,
            file2: f2,
            bidirectional: bi,
        });
        println!("{}", "✨ Quantum link established!".cyan());
    }

    pub fn get_entangled_files(&self, source: &Path) -> Vec<PathBuf> {
        let mut targets = Vec::new();
        for link in &self.links {
            if link.file1 == source {
                targets.push(link.file2.clone());
            } else if link.bidirectional && link.file2 == source {
                targets.push(link.file1.clone());
            }
        }
        targets
    }
}
