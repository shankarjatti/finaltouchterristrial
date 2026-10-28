#include <algorithm>
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
//  ── Centre frequencies ──
//  Every band's centre is env-overridable via SECURECOM_<BAND>_FREQ_HZ, with
//  the value below as the default, so the console can retune a protocol without
//  a rebuild. This matters in practice: the DMR default had to be corrected by
//  ~25 kHz after measuring the real transmission.
//
//  ── Gap defaults ──
//  With 4 bands a 1.0 s gap cost half the cycle. With 8 it would cost 8 s of
//  every 16 s. The gap only exists to push zero-fill keep-alive to the TCP
//  clients, which does not need a whole second, so the default is 0.2 s and it
//  is per-band and env-overridable like dwell. This is also what makes the
//  console's Gap column actually do something -- it used to be inert because
//  gap was a compile-time constant.
// Every band uses the same 1.0 s / 1.0 s dwell/gap by default (explicit
// choice, not a duty-cycle optimisation) -- both constants are kept as
// separate names only so a future band can diverge without touching every
// call site; each is still env-overridable per band exactly like dwell.
static const double GAP_LEGACY  = 1.0;
static const double GAP_DEFAULT = 1.0;

static const std::vector<BandConfig> BANDS = {
    // AIR + MARITIME subsystem: AIS and ADS-B only. This Module 1 is the
    // standalone air/maritime backend -- the 8 terrestrial bands live in the
    // separate COUPLING/version1 tree and are NOT built here (one B210, one
    // Module 1 at a time). AIS 161.975/162.025 and ADS-B 1090 MHz are the fixed
    // international channels; AIS verified over a cable (HackRF -> B210).
    //
    // Each band gets its OWN hardware sample rate (not the shared 200 kSps):
    //  * AIS  250 kSps  -- airmaritime_decoder_live.py decimates by 5 to 50 kSps
    //    and its GMSK demod uses AIS_SPS = 250000/5/9600 (5.208 samp/sym).
    //    Centre is 162.000 MHz, NOT 162.025: airmaritime_decoder_live.py
    //    demodulates two channels at -/+25 kHz from the tuned centre
    //    (freq_xlating +-25000), i.e. AIS 161.975 (87B) and 162.025 (88B).
    //    Tuned to 162.025 (the reference's old value) its two channels land
    //    on 162.000 / 162.050 -- neither is an AIS channel, so nothing decodes.
    //  * ADS-B 6 MSps  -- Mode-S pulses are 0.5 us. On a real 1090 MHz recording
    //    the decoder (modes_demod.py) got 12 CRC-valid frames / 10 s at 2 MSps,
    //    116 at 4 MSps and 155 at 6 MSps; airmaritime_decoder_live.py expects
    //    exactly this rate (ADSB_SOURCE_RATE_HZ).
    { "AIS",  env_or("SECURECOM_AIS_FREQ_HZ",  162.000e6), 7009, env_or("SECURECOM_AIS_DWELL_SEC",  1.0),
              env_or("SECURECOM_AIS_GAP_SEC",  GAP_DEFAULT), env_or("SECURECOM_AIS_SAMPRATE_HZ",  250e3) },
    { "ADSB", env_or("SECURECOM_ADSB_FREQ_HZ", 1090.00e6), 7010, env_or("SECURECOM_ADSB_DWELL_SEC", 1.0),
              env_or("SECURECOM_ADSB_GAP_SEC", GAP_DEFAULT), env_or("SECURECOM_ADSB_SAMPRATE_HZ", 6e6)  },
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
    // Flush stdout after every insertion.
    //
    // When stdout is a pipe rather than a terminal, libstdc++ block-buffers it
    // (~4-8 kB). The bridge therefore did not see a "DWELL band=..." line until
    // enough later output had accumulated to force a flush, so the console's
    // dwell indicator moved in bursts: measured 13.6 s of silence followed by a
    // whole cycle of band changes arriving inside 0.2 s. Unit-buffering costs
    // nothing here (a few short lines per dwell) and makes the schedule
    // readable in real time.
    std::cout.setf(std::ios::unitbuf);
    std::cerr.setf(std::ios::unitbuf);

    std::signal(SIGINT,  signal_handler);
    std::signal(SIGTERM, signal_handler);

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
        // ~0.16 s of complex64 IQ at this band's rate (AIS 320 kB, ADS-B 7.7 MB)
        s->set_send_buffer_bytes(std::max(256 * 1024, static_cast<int>(band.samp_rate_hz * 8 * 0.16)));
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

    // Wait for Module-2 clients before starting the USRP, but not forever.
    //
    // The terrestrial stack (bridge_server.py) and the air/maritime stack
    // (airmaritime_bridge.py) are deliberately independent processes with
    // independent lifecycles -- neither knows the other exists. Gating on
    // ALL BANDS.size() clients connecting would mean running one stack alone
    // hangs here forever waiting for clients the other stack was supposed to
    // provide. A band with nobody connected just dwells with no listener --
    // TcpServer already tolerates that; nothing downstream in the dwell loop
    // depends on every port being consumed.
    const double wait_timeout_sec = env_or("SECURECOM_CLIENT_WAIT_TIMEOUT_SEC", 15.0);
    std::cout << "[MAIN] Waiting up to " << wait_timeout_sec << "s for Module 2 clients "
              << "(" << BANDS.size() << " bands total; proceeding with whatever's "
              << "connected after that)...\n";
    const auto wait_deadline = std::chrono::steady_clock::now()
                              + std::chrono::milliseconds(static_cast<int>(wait_timeout_sec * 1000));
    int connected = 0;
    while (!g_stop) {
        connected = 0;
        for (auto& s : servers)
            if (s->client_count() > 0) ++connected;

        if (connected == static_cast<int>(BANDS.size())) break;
        if (std::chrono::steady_clock::now() >= wait_deadline) break;

        std::cout << "[MAIN]   " << connected << "/" << BANDS.size()
                  << " clients connected — waiting...\r" << std::flush;
        std::this_thread::sleep_for(std::chrono::milliseconds(500));
    }

    if (g_stop) {
        std::cout << "\n[MAIN] Stopped before USRP init.\n";
        return 0;
    }

    if (connected < static_cast<int>(BANDS.size())) {
        std::cout << "\n[MAIN] Proceeding with " << connected << "/" << BANDS.size()
                  << " Module 2 clients connected. Bands with no client:\n";
        for (int i = 0; i < static_cast<int>(BANDS.size()); ++i)
            if (servers[i]->client_count() == 0)
                std::cout << "[MAIN]   " << BANDS[i].name << " (port " << BANDS[i].tcp_port
                          << ") — will dwell with no listener\n";
    } else {
        std::cout << "\n[MAIN] ✔  All " << connected << " clients connected.\n";
    }
    std::cout << "[MAIN] Starting USRP...\n\n";

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
        // non-zero so a supervisor can tell the radio failing from a normal Stop
        std::cout << "[MAIN] Module 1 exited: radio failed (USB).\n";
        return 3;
    }
    std::cout << "[MAIN] Module 1 exited cleanly.\n";
    return 0;
}
