#include "usrp_controller.h"
#include "burst_controller.h"
#include "tcp_server.h"

#include <iostream>
#include <vector>
#include <memory>
#include <thread>
#include <csignal>
#include <atomic>
#include <chrono>
#include <iomanip>
#include <cstdlib>

// ─────────────────────────────────────────────────────────────────────────────
//  Global stop flag — set by SIGINT / SIGTERM
// ─────────────────────────────────────────────────────────────────────────────
static std::atomic<bool> g_stop{false};
static BurstController*  g_burst_ptr{nullptr};

static void signal_handler(int /*sig*/)
{
    std::cout << "\n[MAIN] Signal caught — shutting down...\n";
    g_stop = true;
    if (g_burst_ptr) g_burst_ptr->stop();
}

// Reads an env var as a double, falling back to `def` if unset/invalid.
static double env_or(const char* name, double def)
{
    if (const char* v = std::getenv(name)) {
        try { return std::stod(v); } catch (...) {}
    }
    return def;
}

// ─────────────────────────────────────────────────────────────────────────────
//  Band definitions  (must match Module 2 TCP client config)
//
//  dwell_sec is per-band, not a shared constant: any band can be given a
//  different window via env var without touching the others' share of the
//  cycle. DMR is under active live-radio test, so it gets the long window;
//  NXDN/P25/TETRA get a short one just to keep their chains alive/exercised.
//  SECURECOM_{DMR,NXDN,P25,TETRA}_DWELL_SEC override individually without a
//  rebuild. TETRA center freq (420.0 MHz) matches the SecureCOM config sheet's
//  Terrestrial Radio Decoder row — see module2 for why it can't reuse the
//  DMR/NXDN/P25 decode chain as-is.
// ─────────────────────────────────────────────────────────────────────────────
static const std::vector<BandConfig> BANDS = {
    // Retuned from the nominal 446.09375 MHz. A real IQ capture of the actual
    // test radio (Sep 2026 bench session) put the transmission's power centroid
    // at +24778 Hz, i.e. 446.118528 MHz, with 8.3 kHz occupied bandwidth --
    // measured, not assumed. Tuning here centres that signal in channelizer
    // channel 0 instead of leaving it ~2 channels off near a filter edge.
    { "DMR446",  446.118528e6, 7001, env_or("SECURECOM_DMR_DWELL_SEC",   1.0) },
    { "NXDN96",  451.09375e6,  7002, env_or("SECURECOM_NXDN_DWELL_SEC",  1.0) },
    { "P25-Ph1", 450.09375e6,  7003, env_or("SECURECOM_P25_DWELL_SEC",   1.0) },
    { "TETRA",   420.00000e6,  7004, env_or("SECURECOM_TETRA_DWELL_SEC", 1.0) },
};

// ─────────────────────────────────────────────────────────────────────────────
//  Status printer — prints a table every 10 seconds
// ─────────────────────────────────────────────────────────────────────────────
static void status_loop(const std::vector<std::unique_ptr<TcpServer>>& servers,
                        const BurstController&                          burst)
{
    while (!g_stop) {
        std::this_thread::sleep_for(std::chrono::seconds(10));
        if (g_stop) break;

        int active = burst.current_band();

        std::cout << "\n┌──────────────────────────────────────────────────────┐\n";
        std::cout << "│  MODULE 1 — Status                                   │\n";
        std::cout << "├──────┬──────────────┬──────────┬────────┬────────────┤\n";
        std::cout << "│ Port │ Band         │ Freq     │ Active │ Clients    │\n";
        std::cout << "├──────┼──────────────┼──────────┼────────┼────────────┤\n";

        for (int i = 0; i < static_cast<int>(servers.size()); ++i) {
            const auto& s = servers[i];
            const auto& b = BANDS[i];
            bool is_active = (active == i);
            std::cout << "│ " << std::setw(4) << b.tcp_port
                      << " │ " << std::setw(12) << std::left  << b.name
                      << " │ " << std::setw(8) << std::right
                               << std::fixed << std::setprecision(5)
                               << b.freq_hz / 1e6 << " │ "
                      << std::setw(6) << (is_active ? "  ▶ ON" : "     —")
                      << " │ " << std::setw(10)
                               << s->client_count() << " │\n";
        }
        std::cout << "└──────┴──────────────┴──────────┴────────┴────────────┘\n\n";
    }
}

// ─────────────────────────────────────────────────────────────────────────────
//  main
// ─────────────────────────────────────────────────────────────────────────────
int main(int argc, char* argv[])
{
    std::signal(SIGINT,  signal_handler);
    std::signal(SIGTERM, signal_handler);

    // stdout is a PIPE to the bridge, where C++ streams default to full
    // buffering: the console's dwell/gap/active-band status then arrived in
    // ~20 s bursts. unitbuf flushes every insertion.
    std::cout << std::unitbuf;
    std::cerr << std::unitbuf;

    std::cout << "\n";
    std::cout << "╔══════════════════════════════════════════════════════╗\n";
    std::cout << "║   SecureCOM  —  Module 1                             ║\n";
    std::cout << "║   USRP Burst Receiver & 200 kSps TCP Server          ║\n";
    std::cout << "║   AVGARDE SYSTEMS                                    ║\n";
    std::cout << "╚══════════════════════════════════════════════════════╝\n\n";

    // ── Parse optional device args ────────────────────────────────────────────
    std::string device_args = (argc > 1) ? argv[1] : "";

    // ── 1. Start TCP servers ──────────────────────────────────────────────────
    std::vector<std::unique_ptr<TcpServer>> servers;
    std::vector<TcpServer*>                 server_ptrs;

    std::cout << "[MAIN] Starting TCP servers...\n";
    for (const auto& band : BANDS) {
        auto s = std::make_unique<TcpServer>(band.tcp_port, band.name);
        if (!s->start()) {
            std::cerr << "[MAIN] FATAL: Could not start TCP server on port "
                      << band.tcp_port << "\n";
            return 1;
        }
        server_ptrs.push_back(s.get());
        servers.push_back(std::move(s));
    }

    // ── CONNECTION VERIFICATION SUMMARY ──────────────────────────────────────
    std::cout << "\n[MAIN] ╔══ TCP SERVERS READY ════════════════════════════\n";
    for (const auto& band : BANDS) {
        std::cout << "[MAIN] ║  127.0.0.1:" << band.tcp_port
                  << "  →  " << band.name
                  << "  (" << band.freq_hz / 1e6 << " MHz)\n";
    }
    std::cout << "[MAIN] ╚  Waiting for Module 2 to connect...\n\n";

    // Wait until all 3 Module-2 clients have connected before starting USRP
    std::cout << "[MAIN] Waiting for all 3 TCP clients (Module 2) to connect...\n";
    while (!g_stop) {
        int connected = 0;
        for (auto& s : servers)
            if (s->client_count() > 0) ++connected;

        if (connected == static_cast<int>(BANDS.size())) break;

        std::cout << "[MAIN]   " << connected << "/" << BANDS.size()
                  << " clients connected — waiting...\r" << std::flush;
        std::this_thread::sleep_for(std::chrono::milliseconds(500));
    }

    if (g_stop) {
        std::cout << "\n[MAIN] Stopped before USRP init.\n";
        return 0;
    }

    std::cout << "\n[MAIN] ✔  All " << BANDS.size()
              << " clients connected — starting USRP\n\n";

    // ── 2. Open USRP ──────────────────────────────────────────────────────────
    std::unique_ptr<UsrpController> usrp;
    try {
        usrp = std::make_unique<UsrpController>(device_args);
    } catch (const std::exception& e) {
        std::cerr << "[MAIN] FATAL: USRP init failed — " << e.what() << "\n";
        return 2;
    }

    // ── 3. Start burst controller ─────────────────────────────────────────────
    std::vector<BandConfig> bands(BANDS.begin(), BANDS.end());
    BurstController burst(*usrp, bands, server_ptrs);
    g_burst_ptr = &burst;

    // Status printer in background
    std::thread status_thread(status_loop,
                              std::cref(servers),
                              std::cref(burst));
    status_thread.detach();

    // Run burst loop (blocks until stop())
    burst.run();

    // ── 4. Cleanup ────────────────────────────────────────────────────────────
    std::cout << "[MAIN] Stopping TCP servers...\n";
    for (auto& s : servers) s->stop();

    if (burst.failed()) {
        // non-zero so the bridge knows this was the radio failing, not a Stop
        std::cout << "[MAIN] Module 1 exited: radio failed (USB).\n";
        return 3;
    }
    std::cout << "[MAIN] Module 1 exited cleanly.\n";
    return 0;
}
