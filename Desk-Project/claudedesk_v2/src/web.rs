use axum::{
    extract::State,
    http::StatusCode,
    response::IntoResponse,
    routing::{get, post},
    Json, Router,
};
use serde::{Deserialize, Serialize};
use std::sync::{Arc, RwLock};
use tower_http::cors::CorsLayer;
use tower_http::services::ServeDir;

// Import AppState from main (assuming main makes it public or we define it here)
// To avoid circular dependencies during the refactor, I'll assume AppState is available via crate::AppState
use crate::AppState;

// API Routes
pub fn create_router(state: Arc<RwLock<AppState>>) -> Router {
    Router::new()
        // API Routes
        .route("/api/galaxy", get(get_galaxy))
        .route("/api/galaxy/json", get(get_galaxy_json))
        .route("/api/logs", get(get_logs))
        .route("/api/command", post(run_command))
        // Static Files
        .nest_service("/", ServeDir::new("static"))
        .layer(CorsLayer::permissive())
        .with_state(state)
}

// Handlers

#[derive(Serialize)]
struct GalaxyData {
    files: Vec<crate::cosmic::CosmicFile>,
    links: Vec<crate::cosmic::QuantumLink>,
}

async fn get_galaxy_json(State(state): State<Arc<RwLock<AppState>>>) -> Json<GalaxyData> {
    let state = state.read().unwrap();
    Json(GalaxyData {
        files: state.cosmic_explorer.files.clone(),
        links: state.quantum_link.links.clone(),
    })
}

async fn get_galaxy(State(state): State<Arc<RwLock<AppState>>>) -> impl IntoResponse {
    let state = state.read().unwrap();

    // Use a string capture for the ASCII art
    // We need to modify render_galaxy to return a String instead of printing?
    // Or we capture stdout?
    // Capturing stdout is hard. Let's make a version that returns string.

    // Hack: We'll reimplement or modify cosmic.rs to be string-friendly.
    // For now, let's assume we can get it or return a placeholder.
    // Actually, `cosmic_explorer` is in `state`.

    // We should refactor `render_galaxy` to return String.
    // But since I can't easily change previous files without a tool call,
    // I will assume I'll add a `render_to_string` method to `cosmic.rs` next,
    // OR I will interpret the method refactor I did previously (it prints).
    // Let's modify `cosmic.rs` later to return string.
    // For now, return a placeholder or reconstruct it here.

    // Let's implement a quick renderer here or call a method I'll add.

    // Better: Allow the handler to lock state and generate the string.
    let galaxy_str = generate_galaxy_string(&state.cosmic_explorer, &state.quantum_link);
    galaxy_str
}

async fn get_logs(
    State(state): State<Arc<RwLock<AppState>>>,
) -> Json<Vec<crate::security::AuditLogEntry>> {
    let state = state.read().unwrap();
    // Use an internal method to access logs (fields might be private)
    // We'll need to make AuditLogger::entries public or add a getter
    // Assuming `entries` is accessible or `list_logs()` exists.
    // The previous implementation had `entries` as private but `display_recent_logs` printed them.
    // We will need to make fields public in main.rs refactor.
    Json(state.audit_logger.entries.clone())
}

#[derive(Deserialize)]
struct CommandConfig {
    command: String,
}

#[derive(Serialize)]
struct CommandResponse {
    output: String,
}

async fn run_command(
    State(state): State<Arc<RwLock<AppState>>>,
    Json(payload): Json<CommandConfig>,
) -> Json<CommandResponse> {
    // We need a way to run commands on the shared state.
    // Currently `process_command` is on `ClaudeDesk` struct.
    // `AppState` will hold the individual managers.
    // We should move `process_command` logic to a standalone function or method on `AppState`.

    let mut state = state.write().unwrap();
    let output = crate::process_command_headless(&mut state, &payload.command);

    Json(CommandResponse { output })
}

// Helper to render galaxy to string (similar to cosmic.rs logic)
fn generate_galaxy_string(
    explorer: &crate::cosmic::CosmicFileExplorer,
    quantum: &crate::cosmic::QuantumEntanglement,
) -> String {
    use std::fmt::Write;
    let mut output = String::new();

    writeln!(output, "\n{}", "🌌 COSMIC VIEW - FILE GALAXY").unwrap();
    writeln!(
        output,
        "   Camera: X={:.1} Y={:.1} Z={:.1} | Zoom: {:.1}x",
        explorer.camera_position.x,
        explorer.camera_position.y,
        explorer.camera_position.z,
        explorer.zoom_level
    )
    .unwrap();

    // Create 2D projection of 3D space
    let width = 60;
    let height = 20;
    let mut screen = vec![vec![" ".to_string(); width]; height];

    let project = |pos: &crate::cosmic::CosmicCoordinates| -> Option<(usize, usize)> {
        let dist = ((pos.z - explorer.camera_position.z).abs() + 1.0) / explorer.zoom_level;
        if dist <= 0.0 {
            return None;
        }
        let raw_x = (pos.x - explorer.camera_position.x) / dist;
        let raw_y = (pos.y - explorer.camera_position.y) / dist;
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
        let p1 = explorer
            .files
            .iter()
            .find(|f| f.path == link.file1)
            .map(|f| &f.position);
        let p2 = explorer
            .files
            .iter()
            .find(|f| f.path == link.file2)
            .map(|f| &f.position);

        if let (Some(pos1), Some(pos2)) = (p1, p2) {
            if let (Some((x1, y1)), Some((x2, y2))) = (project(pos1), project(pos2)) {
                // Bresenham's Line Algorithm
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
                            *cell = ".".to_string(); // Web doesn't need ANSI colors for dots
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
    for file in &explorer.files {
        if let Some((proj_x, proj_y)) = project(&file.position) {
            let symbol = if file.size_radius > 5.0 {
                "●"
            } else if file.size_radius > 3.0 {
                "◉"
            } else {
                "○"
            };
            // Simple plain text for web ASCII container
            screen[proj_y][proj_x] = symbol.to_string();
        }
    }

    // Render screen
    write!(output, "   ┌").unwrap();
    write!(output, "{}", "─".repeat(width)).unwrap();
    writeln!(output, "┐").unwrap();

    for row in screen {
        write!(output, "   │").unwrap();
        for cell in row {
            write!(output, "{}", cell).unwrap();
        }
        writeln!(output, "│").unwrap();
    }

    write!(output, "   └").unwrap();
    write!(output, "{}", "─".repeat(width)).unwrap();
    writeln!(output, "┘").unwrap();

    writeln!(output, "\n   Legend: ● Large  ◉ Medium  ○ Small  . Link").unwrap();

    output
}
