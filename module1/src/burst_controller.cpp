#include "burst_controller.h"
#include <iostream>
#include <thread>
#include <chrono>
#include <cstring>
#include <uhd/exception.hpp>

BurstController::BurstController(UsrpController&          usrp,
                                 std::vector<BandConfig>& bands,
                                 std::vector<TcpServer*>& servers)
    : usrp_(usrp), bands_(bands), servers_(servers)
{
    sample_buf_.reserve(SAMPLES_PER_CHUNK);
}

void BurstController::run()
{
    running_ = true;
    int cycle = 0;

    std::cout << "\n[BURST] ════════════════════════════════════════════\n";
    std::cout << "[BURST]  Burst cycle starting\n";
    for (const auto& band : bands_)
        std::cout << "[BURST]  Dwell : " << band.name << " = " << band.dwell_sec << "s\n";
    std::cout << "[BURST]  Gap   : " << GAP_SEC   << "s between bands\n";
    std::cout << "[BURST] ════════════════════════════════════════════\n\n";

    while (running_) {
        ++cycle;
        std::cout << "[BURST] ── Cycle #" << cycle << " ──────────────────────────\n";

        for (int i = 0; i < static_cast<int>(bands_.size()) && running_; ++i) {
            // A USB hiccup (uhd::io_error / LIBUSB_TRANSFER_ERROR) used to escape
            // here and std::terminate() the whole process, killing the radio
            // mid-dwell. Recover by dropping the stream and moving on; give up
            // (cleanly, with a clear message) only if it keeps failing.
            try {
                do_dwell(i);
                if (!running_) break;
                do_gap(i);
                usb_errors_ = 0;
            } catch (const uhd::exception& e) {
                ++usb_errors_;
                std::cerr << "[BURST] USB/UHD error (" << usb_errors_ << "/5): "
                          << e.what() << "\n";
                try { usrp_.stop_stream(); } catch (...) {}
                if (usb_errors_ >= 5) {
                    std::cerr << "[BURST] FATAL: radio keeps failing — check that the B210 "
                                 "is on a USB 3 port with a short USB 3 cable (no hub)\n";
                    running_ = false;
                    break;
                }
                std::this_thread::sleep_for(std::chrono::milliseconds(500));
            }
        }
    }

    usrp_.stop_stream();
    std::cout << "[BURST] Loop exited cleanly.\n";
}

void BurstController::stop()
{
    running_ = false;
}

// ─────────────────────────────────────────────────────────────────────────────
//  DWELL — tune USRP to band[i], stream IQ to TCP server for DWELL_SEC
// ─────────────────────────────────────────────────────────────────────────────
void BurstController::do_dwell(int idx)
{
    const BandConfig& band = bands_[idx];
    current_band_          = idx;

    std::cout << "[BURST] ▶ DWELL  band=" << band.name
              << "  freq=" << band.freq_hz / 1e6 << " MHz"
              << "  port=" << band.tcp_port << "\n";

    // ── Retune ───────────────────────────────────────────────────────────────
    usrp_.stop_stream();
    bool locked = usrp_.tune(band.freq_hz);
    if (!locked) {
        std::cerr << "[BURST]   WARNING: LO not locked for " << band.name << "\n";
    }
    usrp_.start_stream();

    // ── Stream for band.dwell_sec ────────────────────────────────────────────
    auto deadline = std::chrono::steady_clock::now()
                  + std::chrono::milliseconds(static_cast<int>(band.dwell_sec * 1000));

    size_t total_samples = 0;

    // Keep the OTHER bands' sockets fed with zero-fill for the full duration
    // of this dwell too (not just during do_gap()) — previously they received
    // nothing at all while a different band was active, which starved
    // whichever band wasn't currently tuned for up to the combined dwell time
    // of the other bands every cycle.
    static const std::vector<uint8_t> zero_chunk(
        SAMPLES_PER_CHUNK * sizeof(std::complex<float>), 0);

    while (running_ && std::chrono::steady_clock::now() < deadline) {
        int got = usrp_.stream(sample_buf_, SAMPLES_PER_CHUNK);
        if (got <= 0) {
            std::cerr << "[BURST]   RX error, skipping chunk\n";
            std::this_thread::sleep_for(std::chrono::milliseconds(1));
            continue;
        }

        // Send raw bytes to the matching TCP server
        const uint8_t* raw = reinterpret_cast<const uint8_t*>(sample_buf_.data());
        size_t         len = static_cast<size_t>(got) * sizeof(std::complex<float>);
        servers_[idx]->broadcast(raw, len);
        total_samples += static_cast<size_t>(got);

        for (int j = 0; j < static_cast<int>(bands_.size()); ++j)
            if (j != idx) servers_[j]->broadcast(zero_chunk.data(), zero_chunk.size());
    }

    double kb = (total_samples * sizeof(std::complex<float>)) / 1024.0;
    std::cout << "[BURST]   Dwell done — sent " << total_samples
              << " samples (" << static_cast<int>(kb) << " KB) to port "
              << band.tcp_port << "\n";
}

// ─────────────────────────────────────────────────────────────────────────────
//  GAP — USRP silent, send zero-fill to keep Module 2 TCP clients alive
// ─────────────────────────────────────────────────────────────────────────────
void BurstController::do_gap(int idx)
{
    current_band_ = -1;
    usrp_.stop_stream();

    std::cout << "[BURST] ■ GAP    " << GAP_SEC << "s after "
              << bands_[idx].name << "\n";

    // Zero-fill buffer — keeps GNU Radio TCP source blocks happy (no disconnect)
    static const std::vector<uint8_t> zero_chunk(
        SAMPLES_PER_CHUNK * sizeof(std::complex<float>), 0);

    auto deadline = std::chrono::steady_clock::now()
                  + std::chrono::milliseconds(static_cast<int>(GAP_SEC * 1000));

    // Send zeros at ~10 ms intervals to keep sockets alive
    while (running_ && std::chrono::steady_clock::now() < deadline) {
        for (int i = 0; i < static_cast<int>(bands_.size()); ++i)
            servers_[i]->broadcast(zero_chunk.data(), zero_chunk.size());
        std::this_thread::sleep_for(std::chrono::milliseconds(10));
    }
}
